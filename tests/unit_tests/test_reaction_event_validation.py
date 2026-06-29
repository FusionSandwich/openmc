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


def _event(event_id=10, n_products=0, first_product_index=-1):
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
    row['target_za'] = 26056
    row['reaction_mt'] = 16 if n_products else 2
    row['incident_particle'] = 2112
    row['incident_energy'] = 14.1e6
    row['incident_direction'] = _unit_vector()
    row['outgoing_neutron_energy'] = 1.0e6
    row['outgoing_neutron_direction'] = _unit_vector()
    row['recoil_za'] = 26056
    row['recoil_energy'] = 1.0
    row['recoil_direction'] = _unit_vector()
    row['event_weight'] = 1.0
    row['provenance'] = 2 if n_products else 1
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


def test_reaction_event_checker_accepts_product_ranges(tmp_path):
    path = tmp_path / 'reaction_events.h5'
    _write_file(path, [_event(10, 2, 0)],
                [_product(10, 0), _product(10, 1)])

    summary, errors = check_reaction_events(path, require_products=True)

    assert errors == []
    assert summary['events'] == 1
    assert summary['products'] == 2


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
