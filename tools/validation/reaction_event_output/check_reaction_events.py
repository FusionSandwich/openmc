import argparse
import json
import re
import sys

import h5py
import numpy as np


EVENT_FIELDS = (
    'event_id',
    'n_products',
    'first_product_index',
    'history_id',
    'particle_id',
    'parent_id',
    'cell_id',
    'cell_instance',
    'material_id',
    'universe_id',
    'target_za',
    'reaction_mt',
    'incident_particle',
    'incident_energy',
    'incident_direction',
    'outgoing_neutron_energy',
    'outgoing_neutron_direction',
    'recoil_za',
    'recoil_energy',
    'recoil_direction',
    'event_weight',
    'time',
    'provenance',
)

PRODUCT_FIELDS = (
    'event_id',
    'product_index',
    'product_particle',
    'product_za_or_pdg',
    'product_energy',
    'product_direction',
    'product_weight',
    'product_source',
    'product_provenance',
)

DEFAULT_PROVENANCE_CODES = {1, 2, 3, 4, 5, 6}


def _decode(value):
    if isinstance(value, bytes):
        return value.decode()
    return value


def _field_names(dataset):
    if dataset.dtype.names is None:
        return set()
    return set(dataset.dtype.names)


def _missing_fields(dataset, expected):
    return sorted(set(expected) - _field_names(dataset))


def _vector_components(array):
    names = array.dtype.names
    if names is None:
        return None
    if not {'x', 'y', 'z'}.issubset(names):
        return None
    return np.column_stack((array['x'], array['y'], array['z']))


def _finite(errors, label, values):
    if values.size and not np.all(np.isfinite(values)):
        errors.append(f'{label} contains non-finite values')


def _nonnegative(errors, label, values):
    if values.size and np.any(values < 0.0):
        errors.append(f'{label} contains negative values')


def _metadata_provenance_codes(metadata):
    codes = set()
    for name in metadata.attrs:
        match = re.fullmatch(r'provenance_(\d+)', name)
        if match:
            codes.add(int(match.group(1)))
    return codes or set(DEFAULT_PROVENANCE_CODES)


def _check_file_attrs(h5file, errors):
    filetype = _decode(h5file.attrs.get('filetype'))
    if filetype != 'reaction_events':
        errors.append('file attribute "filetype" is not "reaction_events"')
    if 'version' not in h5file.attrs:
        errors.append('missing file attribute "version"')
    if 'reaction_events' not in h5file:
        errors.append('missing group "/reaction_events"')


def _check_metadata(metadata, errors):
    for attr in ('schema_version', 'max_events', 'filename', 'write_products',
                 'write_unsupported', 'balance_diagnostics',
                 'n_material_filters', 'n_cell_filters', 'n_nuclide_filters',
                 'n_reaction_filters'):
        if attr not in metadata.attrs:
            errors.append(f'missing metadata attribute "{attr}"')

    for attr in ('n_material_filters', 'n_cell_filters', 'n_nuclide_filters',
                 'n_reaction_filters'):
        if attr in metadata.attrs and int(metadata.attrs[attr]) < 0:
            errors.append(f'metadata attribute "{attr}" is negative')


def _check_events(events, allowed_provenance, required_provenance, errors):
    missing = _missing_fields(events, EVENT_FIELDS)
    if missing:
        errors.append('events dataset is missing fields: ' + ', '.join(missing))
        return {}

    data = events[()]
    _finite(errors, 'events.incident_energy', data['incident_energy'])
    _finite(errors, 'events.outgoing_neutron_energy',
            data['outgoing_neutron_energy'])
    _finite(errors, 'events.recoil_energy', data['recoil_energy'])
    _finite(errors, 'events.event_weight', data['event_weight'])
    _finite(errors, 'events.time', data['time'])
    _nonnegative(errors, 'events.incident_energy', data['incident_energy'])
    _nonnegative(errors, 'events.outgoing_neutron_energy',
                 data['outgoing_neutron_energy'])
    _nonnegative(errors, 'events.recoil_energy', data['recoil_energy'])
    _nonnegative(errors, 'events.n_products', data['n_products'])

    for field in ('incident_direction', 'outgoing_neutron_direction',
                  'recoil_direction'):
        components = _vector_components(data[field])
        if components is None:
            errors.append(f'events.{field} is not an x/y/z compound field')
        else:
            _finite(errors, f'events.{field}', components)

    provenance = set(int(x) for x in np.unique(data['provenance']))
    unknown = sorted(provenance - allowed_provenance)
    if unknown:
        errors.append('events dataset contains unknown provenance codes: ' +
                      ', '.join(str(x) for x in unknown))

    missing_provenance = sorted(set(required_provenance) - provenance)
    if missing_provenance:
        errors.append('events dataset is missing required provenance codes: ' +
                      ', '.join(str(x) for x in missing_provenance))

    return {
        'events': int(events.shape[0]),
        'event_ids': set(int(x) for x in data['event_id']),
        'product_ranges': {
            int(row['event_id']): (
                int(row['first_product_index']),
                int(row['n_products']),
            )
            for row in data
        },
        'reaction_mts': sorted(int(x) for x in np.unique(data['reaction_mt'])),
        'provenance': sorted(provenance),
    }


def _check_products(products, event_ids, allowed_provenance, errors):
    missing = _missing_fields(products, PRODUCT_FIELDS)
    if missing:
        errors.append('products dataset is missing fields: ' + ', '.join(missing))
        return {}

    data = products[()]
    _finite(errors, 'products.product_energy', data['product_energy'])
    _finite(errors, 'products.product_weight', data['product_weight'])
    _nonnegative(errors, 'products.product_energy', data['product_energy'])
    _nonnegative(errors, 'products.product_index', data['product_index'])

    components = _vector_components(data['product_direction'])
    if components is None:
        errors.append('products.product_direction is not an x/y/z compound field')
    else:
        _finite(errors, 'products.product_direction', components)

    product_event_ids = set(int(x) for x in data['event_id'])
    unknown_events = sorted(product_event_ids - event_ids)
    if unknown_events:
        shown = ', '.join(str(x) for x in unknown_events[:10])
        if len(unknown_events) > 10:
            shown += ', ...'
        errors.append('products dataset references missing event_id values: ' +
                      shown)

    provenance = set(int(x) for x in np.unique(data['product_provenance']))
    unknown = sorted(provenance - allowed_provenance)
    if unknown:
        errors.append('products dataset contains unknown provenance codes: ' +
                      ', '.join(str(x) for x in unknown))

    return {
        'products': int(products.shape[0]),
        'product_event_counts': {
            int(event_id): int(np.count_nonzero(data['event_id'] == event_id))
            for event_id in product_event_ids
        },
        'product_sources': sorted(
            int(x) for x in np.unique(data['product_source'])),
        'product_provenance': sorted(provenance),
    }


def _check_product_ranges(product_ranges, products, errors):
    if products is None:
        for event_id, (first_index, n_products) in product_ranges.items():
            if n_products != 0:
                errors.append(
                    f'event_id {event_id} declares products but products '
                    'dataset is absent')
            if first_index != -1:
                errors.append(
                    f'event_id {event_id} has no products but '
                    'first_product_index is not -1')
        return

    data = products[()]
    n_rows = int(products.shape[0])
    product_event_ids, product_event_counts = np.unique(data['event_id'],
                                                        return_counts=True)
    observed_counts = {
        int(event_id): int(count)
        for event_id, count in zip(product_event_ids, product_event_counts)
    }
    for event_id, (first_index, n_products) in product_ranges.items():
        observed_count = observed_counts.get(event_id, 0)
        if observed_count != n_products:
            errors.append(
                f'event_id {event_id} declares {n_products} products but '
                f'{observed_count} product rows reference it')
        if n_products == 0:
            if first_index != -1:
                errors.append(
                    f'event_id {event_id} has no products but '
                    'first_product_index is not -1')
            continue
        if first_index < 0:
            errors.append(
                f'event_id {event_id} declares products but '
                'first_product_index is negative')
            continue
        if first_index + n_products > n_rows:
            errors.append(
                f'event_id {event_id} product range extends past products '
                'dataset')
            continue
        event_product_ids = data['event_id'][first_index:first_index + n_products]
        if np.any(event_product_ids != event_id):
            errors.append(
                f'event_id {event_id} product range contains rows for another '
                'event')
        product_indices = data['product_index'][first_index:
                                                first_index + n_products]
        if not np.array_equal(product_indices, np.arange(n_products)):
            errors.append(
                f'event_id {event_id} product_index values are not contiguous '
                'from zero')


def check_reaction_events(path, require_products=False,
                          required_provenance=()):
    errors = []
    summary = {
        'path': str(path),
        'events': 0,
        'products': None,
        'reaction_mts': [],
        'provenance': [],
    }

    with h5py.File(path, 'r') as h5file:
        _check_file_attrs(h5file, errors)
        if 'reaction_events' not in h5file:
            return summary, errors

        group = h5file['reaction_events']
        if 'events' not in group:
            errors.append('missing dataset "/reaction_events/events"')
            return summary, errors
        if 'metadata' not in group:
            errors.append('missing group "/reaction_events/metadata"')
            return summary, errors

        metadata = group['metadata']
        _check_metadata(metadata, errors)
        allowed_provenance = _metadata_provenance_codes(metadata)
        event_summary = _check_events(
            group['events'], allowed_provenance, required_provenance, errors)
        summary.update({
            'events': event_summary.get('events', 0),
            'reaction_mts': event_summary.get('reaction_mts', []),
            'provenance': event_summary.get('provenance', []),
        })

        has_products = 'products' in group
        if require_products and not has_products:
            errors.append('missing required dataset "/reaction_events/products"')
        if has_products:
            product_summary = _check_products(
                group['products'], event_summary.get('event_ids', set()),
                allowed_provenance, errors)
            _check_product_ranges(event_summary.get('product_ranges', {}),
                                  group['products'], errors)
            summary.update({
                'products': product_summary.get('products', 0),
                'product_sources': product_summary.get('product_sources', []),
                'product_provenance': product_summary.get(
                    'product_provenance', []),
            })
        else:
            _check_product_ranges(event_summary.get('product_ranges', {}),
                                  None, errors)

    return summary, errors


def main():
    parser = argparse.ArgumentParser(
        description='Validate an OpenMC reaction_events.h5 diagnostic file.')
    parser.add_argument('path', help='Path to reaction_events.h5')
    parser.add_argument('--require-products', action='store_true',
                        help='Require /reaction_events/products to exist.')
    parser.add_argument('--require-provenance', type=int, action='append',
                        default=[],
                        help='Require at least one event with this provenance.')
    parser.add_argument('--summary-json', action='store_true',
                        help='Print the validation summary as JSON.')
    args = parser.parse_args()

    summary, errors = check_reaction_events(
        args.path, args.require_products, args.require_provenance)

    if args.summary_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f'{summary["path"]}: {summary["events"]} events')
        if summary['products'] is not None:
            print(f'{summary["path"]}: {summary["products"]} products')
        if summary['reaction_mts']:
            print('reaction_mt: ' + ', '.join(
                str(x) for x in summary['reaction_mts']))
        if summary['provenance']:
            print('provenance: ' + ', '.join(
                str(x) for x in summary['provenance']))

    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
