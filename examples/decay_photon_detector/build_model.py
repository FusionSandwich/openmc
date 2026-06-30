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
DETECTOR_RESPONSE_MANIFEST = 'detector_response_manifest.json'
DETECTOR_RESPONSE_SCHEMA_VERSION = 1
TALLY_SCORES = {
    'detector photon flux': 'flux',
    'detector pulse height': 'pulse-height',
    'detector heating': 'heating',
}


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


def build_detector_response_manifest(metadata, export_files=None):
    """Build a JSON-serializable detector response manifest."""
    timing = metadata.get('timing', {})
    source = metadata.get('source', {})
    tallies = metadata.get('tallies', {})
    geometry = metadata.get('geometry', {})
    outputs = tallies.get('outputs', {})
    export_files = [] if export_files is None else export_files
    export_file_entries = []
    for path in export_files:
        filename = Path(path).name
        tally_name = outputs.get(filename)
        export_file_entries.append({
            'path': filename,
            'tally_name': tally_name,
            'tally_score': TALLY_SCORES.get(tally_name),
        })

    return {
        'schema_version': DETECTOR_RESPONSE_SCHEMA_VERSION,
        'openmc_version': metadata.get('openmc_version'),
        'git_sha_if_available': None,
        'source_type': source.get('type'),
        'source_normalization': source.get('strength_photons_per_s'),
        'source_units': source.get('units'),
        'source_time_metadata': timing,
        'count_start': timing.get('count_start_s'),
        'count_duration': timing.get('count_duration_s'),
        'detector_name': 'active germanium',
        'detector_cell_id': tallies.get('detector_cell_id'),
        'detector_material': 'germanium',
        'detector_active_volume_if_available': tallies.get(
            'active_volume_cm3'),
        'geometry_description': geometry.get('detector'),
        'tally_name': 'detector pulse height',
        'tally_score': 'pulse-height',
        'energy_units': 'eV',
        'tally_units': 'per source particle',
        'energy_bin_edges': tallies.get('energy_bins_eV'),
        'export_files': export_file_entries,
    }


def write_detector_response_manifest(output_dir, metadata, export_files=None):
    output_dir = Path(output_dir)
    manifest = build_detector_response_manifest(metadata, export_files)
    path = output_dir / DETECTOR_RESPONSE_MANIFEST
    with open(path, 'w') as fh:
        json.dump(manifest, fh, indent=2)
        fh.write('\n')
    return path


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
    write_detector_response_manifest(output_dir, metadata)
    return model, metadata


def export_statepoint_tables(statepoint_path, output_dir='.', metadata=None):
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
    if metadata is None:
        conditions = output_dir / 'detector_conditions.json'
        if conditions.exists():
            with open(conditions) as fh:
                metadata = json.load(fh)
    if metadata is not None:
        write_detector_response_manifest(output_dir, metadata, written)
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
            for path in export_statepoint_tables(
                    statepoint, output_dir, metadata):
                print(path)
            print(output_dir / DETECTOR_RESPONSE_MANIFEST)
        finally:
            if old_chain is None:
                os.environ.pop('OPENMC_CHAIN_FILE', None)
            else:
                os.environ['OPENMC_CHAIN_FILE'] = old_chain


if __name__ == '__main__':
    main()
