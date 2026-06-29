import csv
import importlib.util
from pathlib import Path

import numpy as np
import openmc


EXAMPLE = (Path(__file__).parents[2] / 'examples' /
           'layered_media_source_terms' / 'build_model.py')


def load_example():
    spec = importlib.util.spec_from_file_location(
        'layered_media_source_terms_build_model', EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_layered_media_source_terms_example_export(tmp_path):
    example = load_example()
    model, metadata = example.export_example(
        tmp_path, particles=10, batches=1)

    assert (tmp_path / 'settings.xml').exists()
    assert (tmp_path / 'geometry.xml').exists()
    assert (tmp_path / 'materials.xml').exists()
    assert (tmp_path / 'tallies.xml').exists()
    assert (tmp_path / 'layered_media_conditions.json').exists()
    assert (tmp_path / 'layer_definitions.csv').exists()

    assert model.settings.recoil_production
    assert model.settings.reaction_event_output['enabled']
    assert model.settings.reaction_event_output['write_products']
    assert metadata['reaction_event_output']['filename'].endswith('.h5')
    assert metadata['transport']['tracking_method'] == 'surface'

    tally_names = {tally.name for tally in model.tallies}
    assert 'layer neutron flux' in tally_names
    assert 'layer reaction rates' in tally_names
    assert 'layer damage energy' in tally_names
    assert 'layer particle production' in tally_names

    with open(tmp_path / 'layer_definitions.csv') as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(metadata['geometry']['layers'])
    assert len({row['cell_id'] for row in rows}) == len(rows)
    assert all(row['cell_id'].isdigit() for row in rows)
    assert any(row['material'] == 'iron' for row in rows)
    assert any(row['material'] == 'void' for row in rows)

    bins = np.asarray(metadata['tallies']['energy_bins_eV'])
    assert np.all(np.isfinite(bins))
    assert np.all(np.diff(bins) > 0.0)

    source = model.settings.source[0]
    assert source.particle == 'neutron'
    assert isinstance(source.energy, openmc.stats.Discrete)
    assert metadata['source']['normalization'] == 'per source neutron'
    assert 'layer_particle_production.csv' in metadata['tallies']['outputs']

    readme = (Path(__file__).parents[2] / 'examples' /
              'layered_media_source_terms' / 'README.md').read_text().lower()
    assert 'downstream' in readme or 'source-term' in readme
    assert 'does not' in readme
    assert 'hts degradation' in readme
    assert 'bca/md' in readme
