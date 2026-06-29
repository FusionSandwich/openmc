import argparse
import json
import os
import shutil
from math import pi
from pathlib import Path

import numpy as np
import openmc


EXAMPLE_DIR = Path(__file__).resolve().parent
CHAIN_FILE = EXAMPLE_DIR / 'chain_decay_photon_detector.xml'

SOURCE_RADIUS_CM = 0.25
SOURCE_VOLUME_CM3 = 4.0 / 3.0 * pi * SOURCE_RADIUS_CM**3
SOURCE_ATOM_DENSITY = 1.0e-9
DETECTOR_RADIUS_CM = 2.0
DETECTOR_HEIGHT_CM = 4.0
DETECTOR_CENTER_X_CM = 8.0
BOUNDARY_RADIUS_CM = 20.0
ENERGY_BINS_EV = np.linspace(0.0, 1.5e6, 151)


def _copy_chain_file(output_dir):
    chain_path = output_dir / CHAIN_FILE.name
    if CHAIN_FILE.resolve() != chain_path.resolve():
        shutil.copyfile(CHAIN_FILE, chain_path)
    return chain_path


def _source_rate(source_energy):
    with openmc.config.patch('chain_file', CHAIN_FILE):
        return source_energy.integral()


def build_model(particles=10000, batches=10):
    """Build a generic decay-photon detector transport model."""
    germanium = openmc.Material(name='active germanium')
    germanium.set_density('g/cm3', 5.323)
    germanium.add_element('Ge', 1.0)

    sample_sphere = openmc.Sphere(r=SOURCE_RADIUS_CM)
    detector_cyl = openmc.ZCylinder(
        x0=DETECTOR_CENTER_X_CM, y0=0.0, r=DETECTOR_RADIUS_CM)
    detector_zmin = openmc.ZPlane(z0=-0.5 * DETECTOR_HEIGHT_CM)
    detector_zmax = openmc.ZPlane(z0=0.5 * DETECTOR_HEIGHT_CM)
    boundary = openmc.Sphere(r=BOUNDARY_RADIUS_CM, boundary_type='vacuum')

    detector_region = -detector_cyl & +detector_zmin & -detector_zmax
    source_cell = openmc.Cell(name='activated sample', region=-sample_sphere)
    detector_cell = openmc.Cell(
        name='active germanium', fill=germanium, region=detector_region)
    void_cell = openmc.Cell(
        name='air gap', region=+sample_sphere & -boundary & ~detector_region)

    source_energy = openmc.stats.DecaySpectrum(
        {'Co60': SOURCE_ATOM_DENSITY}, volume=SOURCE_VOLUME_CM3)
    source = openmc.IndependentSource(
        particle='photon',
        space=openmc.stats.Point((0.0, 0.0, 0.0)),
        angle=openmc.stats.Isotropic(),
        energy=source_energy,
    )

    model = openmc.Model()
    model.materials = openmc.Materials([germanium])
    model.geometry = openmc.Geometry([source_cell, detector_cell, void_cell])
    model.settings.run_mode = 'fixed source'
    model.settings.batches = batches
    model.settings.particles = particles
    model.settings.photon_transport = True
    model.settings.electron_treatment = 'led'
    model.settings.cutoff = {'energy_photon': 1000.0}
    model.settings.source = source

    cell_filter = openmc.CellFilter(detector_cell)
    photon_filter = openmc.ParticleFilter('photon')
    energy_filter = openmc.EnergyFilter(ENERGY_BINS_EV)

    flux = openmc.Tally(name='detector photon flux')
    flux.filters = [cell_filter, photon_filter, energy_filter]
    flux.scores = ['flux']

    pulse_height = openmc.Tally(name='detector pulse height')
    pulse_height.filters = [cell_filter, energy_filter]
    pulse_height.scores = ['pulse-height']

    heating = openmc.Tally(name='detector heating')
    heating.filters = [cell_filter]
    heating.scores = ['heating']

    model.tallies = openmc.Tallies([flux, pulse_height, heating])
    metadata = build_metadata(detector_cell.id, source_energy)
    return model, metadata


def build_metadata(detector_cell_id, source_energy):
    detector_volume = pi * DETECTOR_RADIUS_CM**2 * DETECTOR_HEIGHT_CM
    return {
        'openmc_version': openmc.__version__,
        'geometry': {
            'sample': f'sphere, radius {SOURCE_RADIUS_CM} cm',
            'detector': (
                f'germanium cylinder, radius {DETECTOR_RADIUS_CM} cm, '
                f'height {DETECTOR_HEIGHT_CM} cm, center x '
                f'{DETECTOR_CENTER_X_CM} cm'
            ),
            'shielding': 'none',
        },
        'timing': {
            'irradiation_start_s': 0.0,
            'irradiation_end_s': 3600.0,
            'cooling_time_s': 86400.0,
            'count_start_s': 86400.0,
            'count_duration_s': 3600.0,
        },
        'source': {
            'type': 'decay_photon',
            'nuclides': {
                'Co60': {
                    'atom_density_atom_per_b_cm': SOURCE_ATOM_DENSITY,
                },
            },
            'volume_cm3': SOURCE_VOLUME_CM3,
            'normalization': 'DecaySpectrum integral from depletion chain',
            'strength_photons_per_s': _source_rate(source_energy),
            'units': 'photons/s',
            'chain_file': CHAIN_FILE.name,
        },
        'tallies': {
            'energy_bins_eV': ENERGY_BINS_EV.tolist(),
            'detector_cell_id': detector_cell_id,
            'active_volume_cm3': detector_volume,
            'outputs': {
                'detector_photon_flux.csv': 'detector photon flux',
                'detector_pulse_height.csv': 'detector pulse height',
                'detector_heating.csv': 'detector heating',
            },
        },
        'transport': {
            'particles': ['photon'],
            'electron_transport': False,
            'tracking_method': 'surface',
        },
    }


def export_example(output_dir='.', particles=10000, batches=10):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    chain_path = _copy_chain_file(output_dir)

    model, metadata = build_model(particles=particles, batches=batches)
    metadata['source']['chain_file'] = chain_path.name
    model.export_to_xml(output_dir)
    with open(output_dir / 'detector_conditions.json', 'w') as fh:
        json.dump(metadata, fh, indent=2)
        fh.write('\n')
    return model, metadata


def export_statepoint_tables(statepoint_path, output_dir='.'):
    output_dir = Path(output_dir)
    outputs = {
        'detector_photon_flux.csv': 'detector photon flux',
        'detector_pulse_height.csv': 'detector pulse height',
        'detector_heating.csv': 'detector heating',
    }
    written = []
    with openmc.StatePoint(statepoint_path) as sp:
        for filename, tally_name in outputs.items():
            tally = sp.get_tally(name=tally_name)
            path = output_dir / filename
            df = tally.get_pandas_dataframe()
            df.columns = [
                ' '.join(str(part) for part in col if str(part))
                if isinstance(col, tuple) else col
                for col in df.columns.to_flat_index()
            ]
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            df[numeric_columns] = (
                df[numeric_columns]
                .replace([np.inf, -np.inf], np.nan)
                .fillna(0.0)
            )
            df.to_csv(path, index=False)
            written.append(path)
    return written


def main():
    parser = argparse.ArgumentParser(
        description='Build a decay photon detector example model.')
    parser.add_argument('--output-dir', default='.',
                        help='Directory for XML inputs and metadata.')
    parser.add_argument('--particles', type=int, default=10000,
                        help='Particles per batch.')
    parser.add_argument('--batches', type=int, default=10,
                        help='Number of fixed-source batches.')
    parser.add_argument('--run', action='store_true',
                        help='Run OpenMC after exporting inputs.')
    parser.add_argument('--openmc-exec', default='openmc',
                        help='OpenMC executable to use with --run.')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    model, metadata = export_example(
        output_dir, particles=args.particles, batches=args.batches)
    print(output_dir / 'detector_conditions.json')

    if args.run:
        chain_path = output_dir / metadata['source']['chain_file']
        old_chain = os.environ.get('OPENMC_CHAIN_FILE')
        os.environ['OPENMC_CHAIN_FILE'] = str(chain_path.resolve())
        try:
            statepoint = model.run(cwd=output_dir, openmc_exec=args.openmc_exec,
                                   export_model_xml=False)
            for path in export_statepoint_tables(statepoint, output_dir):
                print(path)
        finally:
            if old_chain is None:
                os.environ.pop('OPENMC_CHAIN_FILE', None)
            else:
                os.environ['OPENMC_CHAIN_FILE'] = old_chain


if __name__ == '__main__':
    main()
