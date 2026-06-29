import sys
from pathlib import Path

import h5py
import numpy as np


sys.path.insert(
    0, str(Path(__file__).parents[2] / 'tools' / 'validation' /
           'reaction_event_output'))

from check_reaction_events import check_reaction_events


VECTOR_DTYPE = np.dtype([('x', 'f8'), ('y', 'f8'), ('z', 'f8')])

EVENT_DTYPE = np.dtype([
    ('event_id', 'i8'),
    ('n_products', 'i4'),
    ('first_product_index', 'i8'),
    ('history_id', 'i8'),
    ('particle_id', 'i8'),
    ('parent_id', 'i8'),
    ('cell_id', 'i4'),
    ('cell_instance', 'i4'),
    ('material_id', 'i4'),
    ('universe_id', 'i4'),
    ('target_za', 'i4'),
    ('reaction_mt', 'i4'),
    ('incident_particle', 'i4'),
    ('incident_energy', 'f8'),
    ('incident_direction', VECTOR_DTYPE),
    ('outgoing_neutron_energy', 'f8'),
    ('outgoing_neutron_direction', VECTOR_DTYPE),
    ('recoil_za', 'i4'),
    ('recoil_energy', 'f8'),
    ('recoil_direction', VECTOR_DTYPE),
    ('event_weight', 'f8'),
    ('time', 'f8'),
    ('provenance', 'i4'),
])

PRODUCT_DTYPE = np.dtype([
    ('event_id', 'i8'),
    ('product_index', 'i4'),
    ('product_particle', 'i4'),
    ('product_za_or_pdg', 'i4'),
    ('product_energy', 'f8'),
    ('product_direction', VECTOR_DTYPE),
    ('product_weight', 'f8'),
    ('product_source', 'i4'),
    ('product_provenance', 'i4'),
])


def _unit_vector():
    return (0.0, 0.0, 1.0)


def _event(event_id=10, n_products=0, first_product_index=-1,
           target_za=26056, reaction_mt=None,
           incident_energy=14.1e6, recoil_energy=1.0, provenance=None,
           recoil_direction=None):
    row = np.zeros((), dtype=EVENT_DTYPE)
    row['event_id'] = event_id
    row['n_products'] = n_products
    row['first_product_index'] = first_product_index
    row['history_id'] = event_id
    row['particle_id'] = event_id
    row['parent_id'] = event_id
    row['cell_id'] = 1
    row['cell_instance'] = 0
    row['material_id'] = 1
    row['universe_id'] = 0
    row['target_za'] = target_za
    row['reaction_mt'] = reaction_mt or (16 if n_products else 2)
    row['incident_particle'] = 2112
    row['incident_energy'] = incident_energy
    row['incident_direction'] = _unit_vector()
    row['outgoing_neutron_energy'] = 1.0e6
    row['outgoing_neutron_direction'] = _unit_vector()
    row['recoil_za'] = target_za
    row['recoil_energy'] = recoil_energy
    row['recoil_direction'] = recoil_direction or _unit_vector()
    row['event_weight'] = 1.0
    row['provenance'] = provenance or (2 if n_products else 1)
    return row


def _product(event_id, product_index):
    row = np.zeros((), dtype=PRODUCT_DTYPE)
    row['event_id'] = event_id
    row['product_index'] = product_index
    row['product_particle'] = 2112
    row['product_za_or_pdg'] = 2112
    row['product_energy'] = 1.0e6
    row['product_direction'] = _unit_vector()
    row['product_weight'] = 1.0
    row['product_source'] = 1
    row['product_provenance'] = 2
    return row


def _write_file(path, events, products=None):
    with h5py.File(path, 'w') as h5file:
        h5file.attrs['filetype'] = 'reaction_events'
        h5file.attrs['version'] = (1, 1)
        group = h5file.create_group('reaction_events')
        group.create_dataset('events', data=np.array(events, dtype=EVENT_DTYPE))
        if products is not None:
            group.create_dataset(
                'products', data=np.array(products, dtype=PRODUCT_DTYPE))
        metadata = group.create_group('metadata')
        metadata.attrs['schema_version'] = (1, 1)
        metadata.attrs['max_events'] = 100
        metadata.attrs['filename'] = 'reaction_events.h5'
        metadata.attrs['write_products'] = products is not None
        metadata.attrs['write_unsupported'] = False
        metadata.attrs['balance_diagnostics'] = False
        metadata.attrs['n_material_filters'] = 0
        metadata.attrs['n_cell_filters'] = 0
        metadata.attrs['n_nuclide_filters'] = 0
        metadata.attrs['n_reaction_filters'] = 0
        metadata.attrs['provenance_1'] = 'elastic_exact'
        metadata.attrs['provenance_2'] = 'product_distribution_sampled'
        metadata.attrs['provenance_3'] = 'residual_momentum_balance'
        metadata.attrs['provenance_4'] = 'capture_gamma_approx'
        metadata.attrs['provenance_5'] = 'energy_balance_only'
        metadata.attrs['provenance_6'] = 'unsupported'


def _direction_norms(direction):
    return np.sqrt(
        direction['x'] * direction['x'] +
        direction['y'] * direction['y'] +
        direction['z'] * direction['z'])


def _max_elastic_recoil_energy(incident_energy, awr):
    return 4.0 * awr / ((1.0 + awr) * (1.0 + awr)) * incident_energy


def test_elastic_pka_event_sanity_fixture(tmp_path):
    path = tmp_path / 'reaction_events.h5'
    h1_event = _event(event_id=1, target_za=1001, recoil_energy=8.0e6)
    fe56_event = _event(event_id=2, target_za=26056, recoil_energy=8.0e5)
    _write_file(path, [h1_event, fe56_event])

    assert path.exists()
    summary, errors = check_reaction_events(
        path, required_provenance=(1,))
    assert errors == []
    assert summary['events'] == 2
    assert summary['products'] is None
    assert summary['provenance'] == [1]

    with h5py.File(path, 'r') as h5file:
        metadata = h5file['reaction_events']['metadata'].attrs
        assert tuple(metadata['schema_version']) == (1, 1)
        events = h5file['reaction_events']['events'][()]

    awr_by_za = {1001: 1.0, 26056: 56.0}
    assert np.all(events['n_products'] == 0)
    assert np.all(events['first_product_index'] == -1)
    assert set(events['target_za']) == {1001, 26056}
    for row in events:
        t_max = _max_elastic_recoil_energy(
            row['incident_energy'], awr_by_za[int(row['target_za'])])
        assert 0.0 <= row['recoil_energy'] <= t_max
    assert np.all(np.isfinite(_direction_norms(events['recoil_direction'])))
    assert np.allclose(_direction_norms(events['recoil_direction']), 1.0)


def test_reaction_event_checker_accepts_product_ranges(tmp_path):
    path = tmp_path / 'reaction_events.h5'
    _write_file(path, [_event(10, 2, 0), _event(11, 1, 2)],
                [_product(10, 0), _product(10, 1), _product(11, 0)])

    summary, errors = check_reaction_events(path, require_products=True)

    assert errors == []
    assert summary['events'] == 2
    assert summary['products'] == 3


def test_reaction_event_checker_accepts_no_product_file(tmp_path):
    path = tmp_path / 'reaction_events.h5'
    _write_file(path, [_event()])

    summary, errors = check_reaction_events(path)

    assert errors == []
    assert summary['events'] == 1
    assert summary['products'] is None


def test_reaction_event_checker_rejects_declared_products_without_dataset(
        tmp_path):
    path = tmp_path / 'reaction_events.h5'
    _write_file(path, [_event(10, 1, 0)])

    _, errors = check_reaction_events(path)

    assert any('declares products but products dataset is absent' in error
               for error in errors)


def test_reaction_event_checker_rejects_bad_product_range(tmp_path):
    path = tmp_path / 'reaction_events.h5'
    _write_file(path, [_event(10, 2, 0)],
                [_product(10, 0), _product(11, 1)])

    _, errors = check_reaction_events(path, require_products=True)

    assert any('product range contains rows for another event' in error
               for error in errors)


def test_reaction_event_checker_rejects_product_count_mismatch(tmp_path):
    path = tmp_path / 'reaction_events.h5'
    _write_file(path, [_event(10, 1, 0)],
                [_product(10, 0), _product(10, 1)])

    _, errors = check_reaction_events(path, require_products=True)

    assert any('declares 1 products but 2 product rows reference it' in error
               for error in errors)


def test_unsupported_product_data_fixture_is_not_exact(tmp_path):
    path = tmp_path / 'reaction_events.h5'
    unsupported = _event(event_id=20, reaction_mt=107, provenance=6,
                         n_products=0, first_product_index=-1,
                         recoil_energy=0.0, recoil_direction=(0.0, 0.0, 0.0))
    _write_file(path, [unsupported])

    summary, errors = check_reaction_events(
        path, required_provenance=(6,))

    assert errors == []
    assert summary['provenance'] == [6]
    with h5py.File(path, 'r') as h5file:
        event = h5file['reaction_events']['events'][0]
    assert event['reaction_mt'] == 107
    assert event['provenance'] == 6
    assert event['provenance'] != 1
    assert event['n_products'] == 0
    assert event['first_product_index'] == -1
