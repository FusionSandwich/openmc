import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import openmc


EXAMPLE = (Path(__file__).parents[2] / 'examples' /
           'decay_photon_detector' / 'build_model.py')
CHECKER_DIR = (Path(__file__).parents[2] / 'tools' / 'validation' /
               'detector_response')
sys.path.insert(0, str(CHECKER_DIR))

from check_detector_response import check_detector_response


def load_example():
    spec = importlib.util.spec_from_file_location(
        'decay_photon_detector_build_model', EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_decay_photon_detector_example_export(tmp_path):
    example = load_example()
    model, metadata = example.export_example(
        tmp_path, particles=10, batches=1)

    assert (tmp_path / 'settings.xml').exists()
    assert (tmp_path / 'geometry.xml').exists()
    assert (tmp_path / 'materials.xml').exists()
    assert (tmp_path / 'tallies.xml').exists()
    assert (tmp_path / 'detector_conditions.json').exists()
    assert (tmp_path / 'detector_response_manifest.json').exists()
    assert (tmp_path / 'chain_decay_photon_detector.xml').exists()

    assert model.settings.photon_transport
    source = model.settings.source[0]
    assert isinstance(source.energy, openmc.stats.DecaySpectrum)
    assert metadata['source']['strength_photons_per_s'] > 0.0
    assert metadata['source']['type'] == 'decay_photon'
    assert metadata['timing']['count_duration_s'] > 0.0
    assert metadata['source']['normalization']
    assert metadata['tallies']['detector_cell_id'] is not None
    assert metadata['transport']['particles'] == ['photon']
    assert metadata['tallies']['outputs'] == {
        'detector_photon_flux.csv': 'detector photon flux',
        'detector_pulse_height.csv': 'detector pulse height',
        'detector_heating.csv': 'detector heating',
    }

    with open(tmp_path / 'detector_response_manifest.json') as fh:
        manifest = json.load(fh)
    assert manifest['schema_version'] == 1
    assert manifest['source_type'] == 'decay_photon'
    assert manifest['source_normalization'] > 0.0
    assert manifest['source_units'] == 'photons/s'
    assert manifest['detector_cell_id'] == metadata['tallies']['detector_cell_id']
    assert manifest['detector_material'] == 'germanium'
    assert manifest['tally_score'] == 'pulse-height'
    assert manifest['energy_units'] == 'eV'
    assert manifest['tally_units']

    bins = np.asarray(metadata['tallies']['energy_bins_eV'])
    assert np.all(np.isfinite(bins))
    assert np.all(np.diff(bins) > 0.0)

    readme = (Path(__file__).parents[2] / 'examples' /
              'decay_photon_detector' / 'README.md').read_text().lower()
    assert 'does not model' in readme
    assert 'detector electronics' in readme
    assert 'peak fitting' in readme


def _write_detector_csv(path, values=(1.0, 2.0)):
    path.write_text(
        'energy low [eV],energy high [eV],mean,std. dev.\n' +
        '\n'.join(
            f'{index},{index + 1},{value},0.0'
            for index, value in enumerate(values)
        ) + '\n')


def _write_manifest_with_exports(tmp_path, files):
    example = load_example()
    _, metadata = example.export_example(tmp_path, particles=10, batches=1)
    paths = []
    for filename, values in files.items():
        path = tmp_path / filename
        _write_detector_csv(path, values)
        paths.append(path)
    return example.write_detector_response_manifest(tmp_path, metadata, paths)


def test_detector_response_checker_accepts_valid_export(tmp_path):
    manifest_path = _write_manifest_with_exports(
        tmp_path, {'detector_pulse_height.csv': (1.0, 2.0)})

    summary, errors = check_detector_response(manifest_path)

    assert errors == []
    assert summary['schema_version'] == 1
    assert summary['export_files'] == 1
    assert summary['source_type'] == 'decay_photon'
    assert summary['detector_cell_id'] is not None


def test_detector_response_checker_rejects_missing_manifest(tmp_path):
    _, errors = check_detector_response(tmp_path)

    assert any('missing manifest' in error for error in errors)


def test_detector_response_checker_rejects_nonmonotonic_energy_bins(tmp_path):
    manifest_path = _write_manifest_with_exports(
        tmp_path, {'detector_pulse_height.csv': (1.0,)})
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    manifest['energy_bin_edges'] = [0.0, 2.0, 1.0]
    with open(manifest_path, 'w') as fh:
        json.dump(manifest, fh)

    _, errors = check_detector_response(manifest_path)

    assert any('energy_bin_edges are not strictly monotonic' in error
               for error in errors)


def test_detector_response_checker_rejects_nonfinite_csv_values(tmp_path):
    manifest_path = _write_manifest_with_exports(
        tmp_path, {'detector_pulse_height.csv': (1.0,)})
    csv_path = tmp_path / 'detector_pulse_height.csv'
    csv_path.write_text(
        'energy low [eV],energy high [eV],mean,std. dev.\n'
        '0.0,1.0,inf,0.0\n')

    _, errors = check_detector_response(manifest_path)

    assert any('is not finite' in error for error in errors)


def test_detector_response_checker_rejects_bad_schema_version(tmp_path):
    manifest_path = _write_manifest_with_exports(
        tmp_path, {'detector_pulse_height.csv': (1.0,)})
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    manifest['schema_version'] = 99
    with open(manifest_path, 'w') as fh:
        json.dump(manifest, fh)

    _, errors = check_detector_response(manifest_path)

    assert any('manifest schema_version is 99; expected 1' in error
               for error in errors)


def test_detector_response_checker_rejects_missing_export_file(tmp_path):
    manifest_path = _write_manifest_with_exports(
        tmp_path, {'detector_pulse_height.csv': (1.0,)})
    (tmp_path / 'detector_pulse_height.csv').unlink()

    _, errors = check_detector_response(manifest_path)

    assert any('missing export file: detector_pulse_height.csv' in error
               for error in errors)


def test_detector_response_checker_rejects_missing_detector_id(tmp_path):
    manifest_path = _write_manifest_with_exports(
        tmp_path, {'detector_pulse_height.csv': (1.0,)})
    with open(manifest_path) as fh:
        manifest = json.load(fh)
    manifest['detector_cell_id'] = None
    with open(manifest_path, 'w') as fh:
        json.dump(manifest, fh)

    _, errors = check_detector_response(manifest_path)

    assert any('manifest field "detector_cell_id" is required' in error
               for error in errors)
