import argparse
import csv
import json
from pathlib import Path

import numpy as np
import openmc


ENERGY_BINS_EV = [0.0, 1.0e5, 1.0e6, 5.0e6, 20.0e6]
PRODUCTION_BINS_EV = [0.0, 1.0e5, 1.0e6, 5.0e6, 20.0e6]
REACTION_BINS = [2, 4, 102]
BOX_HALF_WIDTH_CM = 3.0

LAYER_SPECS = (
    {
        'name': 'source gap',
        'x_min_cm': -5.0,
        'x_max_cm': 0.0,
        'material': None,
        'role': 'source region',
    },
    {
        'name': 'iron sample',
        'x_min_cm': 0.0,
        'x_max_cm': 0.3,
        'material': 'iron',
        'role': 'activation or damage sample',
    },
    {
        'name': 'water gap',
        'x_min_cm': 0.3,
        'x_max_cm': 1.3,
        'material': 'water',
        'role': 'moderating or coolant layer',
    },
    {
        'name': 'copper backing',
        'x_min_cm': 1.3,
        'x_max_cm': 1.8,
        'material': 'copper',
        'role': 'backing or shielding layer',
    },
    {
        'name': 'downstream tally gap',
        'x_min_cm': 1.8,
        'x_max_cm': 5.0,
        'material': None,
        'role': 'downstream response region',
    },
)


def make_materials():
    iron = openmc.Material(name='iron')
    iron.set_density('g/cm3', 7.87)
    iron.add_nuclide('Fe56', 1.0)

    water = openmc.Material(name='water')
    water.set_density('g/cm3', 1.0)
    water.add_nuclide('H1', 2.0)
    water.add_nuclide('O16', 1.0)

    copper = openmc.Material(name='copper')
    copper.set_density('g/cm3', 8.96)
    copper.add_nuclide('Cu63', 1.0)

    return {
        'iron': iron,
        'water': water,
        'copper': copper,
    }


def build_model(particles=10000, batches=10):
    materials = make_materials()
    y_min = openmc.YPlane(y0=-BOX_HALF_WIDTH_CM, boundary_type='vacuum')
    y_max = openmc.YPlane(y0=BOX_HALF_WIDTH_CM, boundary_type='vacuum')
    z_min = openmc.ZPlane(z0=-BOX_HALF_WIDTH_CM, boundary_type='vacuum')
    z_max = openmc.ZPlane(z0=BOX_HALF_WIDTH_CM, boundary_type='vacuum')

    x_planes = {}
    for x in sorted({spec['x_min_cm'] for spec in LAYER_SPECS} |
                    {spec['x_max_cm'] for spec in LAYER_SPECS}):
        if x in (-5.0, 5.0):
            x_planes[x] = openmc.XPlane(x0=x, boundary_type='vacuum')
        else:
            x_planes[x] = openmc.XPlane(x0=x)

    layer_cells = []
    layer_rows = []
    for spec in LAYER_SPECS:
        region = (
            +x_planes[spec['x_min_cm']] & -x_planes[spec['x_max_cm']] &
            +y_min & -y_max & +z_min & -z_max
        )
        material = materials.get(spec['material'])
        cell = openmc.Cell(name=spec['name'], fill=material, region=region)
        layer_cells.append(cell)
        layer_rows.append({
            'name': spec['name'],
            'cell_id': cell.id,
            'material': spec['material'] or 'void',
            'role': spec['role'],
            'x_min_cm': spec['x_min_cm'],
            'x_max_cm': spec['x_max_cm'],
            'thickness_cm': spec['x_max_cm'] - spec['x_min_cm'],
        })

    model = openmc.Model()
    model.materials = openmc.Materials(materials.values())
    model.geometry = openmc.Geometry(layer_cells)
    model.settings.run_mode = 'fixed source'
    model.settings.particles = particles
    model.settings.batches = batches
    model.settings.recoil_production = True
    model.settings.source = openmc.IndependentSource(
        particle='neutron',
        space=openmc.stats.Point((-4.5, 0.0, 0.0)),
        angle=openmc.stats.Monodirectional(),
        energy=openmc.stats.Discrete([14.1e6], [1.0]),
    )
    model.settings.reaction_event_output = {
        'enabled': True,
        'filename': 'layer_reaction_events.h5',
        'max_events': 10000,
        'reactions': REACTION_BINS,
        'write_products': True,
        'write_unsupported': True,
        'balance_diagnostics': True,
    }

    cell_filter = openmc.CellFilter(layer_cells)
    energy_filter = openmc.EnergyFilter(ENERGY_BINS_EV)
    neutron_filter = openmc.ParticleFilter('neutron')
    reaction_filter = openmc.ReactionFilter(REACTION_BINS)
    production_filter = openmc.ParticleProductionFilter(
        ['neutron', 'photon'], PRODUCTION_BINS_EV)

    flux = openmc.Tally(name='layer neutron flux')
    flux.filters = [cell_filter, neutron_filter, energy_filter]
    flux.scores = ['flux']

    reactions = openmc.Tally(name='layer reaction rates')
    reactions.filters = [cell_filter, reaction_filter]
    reactions.scores = ['flux']

    damage = openmc.Tally(name='layer damage energy')
    damage.filters = [cell_filter, neutron_filter]
    damage.scores = ['damage-energy']

    production = openmc.Tally(name='layer particle production')
    production.filters = [cell_filter, neutron_filter, energy_filter,
                          production_filter]
    production.scores = ['events']
    production.estimator = 'analog'

    model.tallies = openmc.Tallies([flux, reactions, damage, production])
    metadata = build_metadata(layer_rows)
    return model, metadata


def build_metadata(layer_rows):
    return {
        'openmc_version': openmc.__version__,
        'geometry': {
            'type': 'one-dimensional slab stack in a finite box',
            'box_half_width_cm': BOX_HALF_WIDTH_CM,
            'layers': layer_rows,
        },
        'source': {
            'type': 'monoenergetic neutron point source',
            'position_cm': [-4.5, 0.0, 0.0],
            'direction': '+x',
            'energy_eV': 14.1e6,
            'normalization': 'per source neutron',
        },
        'tallies': {
            'energy_bins_eV': ENERGY_BINS_EV,
            'production_energy_bins_eV': PRODUCTION_BINS_EV,
            'reaction_mts': REACTION_BINS,
            'outputs': {
                'layer_flux.csv': 'layer neutron flux',
                'layer_reaction_rates.csv': 'layer reaction rates',
                'layer_damage_energy.csv': 'layer damage energy',
                'layer_particle_production.csv': 'layer particle production',
            },
        },
        'reaction_event_output': {
            'filename': 'layer_reaction_events.h5',
            'write_products': True,
            'write_unsupported': True,
            'balance_diagnostics': True,
        },
        'transport': {
            'particles': ['neutron'],
            'electron_transport': False,
            'tracking_method': 'surface',
        },
    }


def write_layer_table(metadata, output_dir):
    path = output_dir / 'layer_definitions.csv'
    rows = metadata['geometry']['layers']
    with open(path, 'w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def export_statepoint_tables(statepoint_path, output_dir='.'):
    output_dir = Path(output_dir)
    outputs = {
        'layer_flux.csv': 'layer neutron flux',
        'layer_reaction_rates.csv': 'layer reaction rates',
        'layer_damage_energy.csv': 'layer damage energy',
        'layer_particle_production.csv': 'layer particle production',
    }
    written = []
    with openmc.StatePoint(statepoint_path) as sp:
        for filename, tally_name in outputs.items():
            tally = sp.get_tally(name=tally_name)
            path = output_dir / filename
            tally.get_pandas_dataframe().to_csv(path, index=False)
            written.append(path)
    return written


def export_example(output_dir='.', particles=10000, batches=10):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model, metadata = build_model(particles=particles, batches=batches)
    model.export_to_xml(output_dir)
    with open(output_dir / 'layered_media_conditions.json', 'w') as fh:
        json.dump(metadata, fh, indent=2)
        fh.write('\n')
    write_layer_table(metadata, output_dir)
    return model, metadata


def main():
    parser = argparse.ArgumentParser(
        description='Build a layered-media source-term example model.')
    parser.add_argument('--output-dir', default='.',
                        help='Directory for XML inputs and metadata.')
    parser.add_argument('--particles', type=int, default=10000,
                        help='Particles per batch.')
    parser.add_argument('--batches', type=int, default=10,
                        help='Number of fixed-source batches.')
    parser.add_argument('--run', action='store_true',
                        help='Run OpenMC and export source-term CSV tables.')
    parser.add_argument('--openmc-exec', default='openmc',
                        help='OpenMC executable to use with --run.')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    model, _ = export_example(
        output_dir, particles=args.particles, batches=args.batches)
    print(output_dir / 'layered_media_conditions.json')

    if args.run:
        statepoint = model.run(cwd=output_dir, openmc_exec=args.openmc_exec,
                               export_model_xml=False)
        for path in export_statepoint_tables(statepoint, output_dir):
            print(path)


if __name__ == '__main__':
    main()
