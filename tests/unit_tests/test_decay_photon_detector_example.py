import importlib.util
from pathlib import Path

import numpy as np
import openmc


EXAMPLE = (Path(__file__).parents[2] / 'examples' /
           'decay_photon_detector' / 'build_model.py')


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
    assert (tmp_path / 'chain_decay_photon_detector.xml').exists()

    assert model.settings.photon_transport
    source = model.settings.source[0]
    assert isinstance(source.energy, openmc.stats.DecaySpectrum)
    assert metadata['source']['strength_photons_per_s'] > 0.0
    assert metadata['source']['type'] == 'decay_photon'
    assert metadata['tallies']['detector_cell_id'] is not None
    assert metadata['transport']['particles'] == ['photon']
    assert metadata['tallies']['outputs'] == {
        'detector_photon_flux.csv': 'detector photon flux',
        'detector_pulse_height.csv': 'detector pulse height',
        'detector_heating.csv': 'detector heating',
    }

    bins = np.asarray(metadata['tallies']['energy_bins_eV'])
    assert np.all(np.isfinite(bins))
    assert np.all(np.diff(bins) > 0.0)
