import argparse
import csv
import json
import math
import sys
from pathlib import Path


EXPECTED_SCHEMA_VERSION = 1
REQUIRED_FIELDS = (
    'schema_version',
    'openmc_version',
    'git_sha_if_available',
    'source_type',
    'source_normalization',
    'source_units',
    'source_time_metadata',
    'count_start',
    'count_duration',
    'detector_name',
    'detector_cell_id',
    'detector_material',
    'detector_active_volume_if_available',
    'geometry_description',
    'tally_name',
    'tally_score',
    'energy_units',
    'tally_units',
    'energy_bin_edges',
    'export_files',
)


def _is_finite_number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def _check_energy_bins(manifest, errors):
    bins = manifest.get('energy_bin_edges')
    if not isinstance(bins, list) or len(bins) < 2:
        errors.append('energy_bin_edges must contain at least two values')
        return
    if not all(_is_finite_number(value) for value in bins):
        errors.append('energy_bin_edges contains non-finite values')
        return
    if any(b <= a for a, b in zip(bins, bins[1:])):
        errors.append('energy_bin_edges are not strictly monotonic')


def _check_time_metadata(manifest, errors):
    count_start = manifest.get('count_start')
    count_duration = manifest.get('count_duration')
    if count_start is not None and not _is_finite_number(count_start):
        errors.append('count_start is not finite or null')
    if count_duration is not None:
        if not _is_finite_number(count_duration):
            errors.append('count_duration is not finite or null')
        elif count_duration < 0.0:
            errors.append('count_duration is negative')


def _iter_export_entries(export_files):
    if isinstance(export_files, dict):
        for path, metadata in export_files.items():
            entry = {'path': path}
            if isinstance(metadata, dict):
                entry.update(metadata)
            elif metadata is not None:
                entry['tally_name'] = str(metadata)
            yield entry
    elif isinstance(export_files, list):
        for entry in export_files:
            if isinstance(entry, str):
                yield {'path': entry}
            elif isinstance(entry, dict):
                yield entry
            else:
                yield {'path': None}
    else:
        yield {'path': None}


def _check_csv(path, errors):
    try:
        with open(path, newline='') as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                errors.append(f'{path.name} has no CSV header')
                return
            numeric_seen = False
            for row_index, row in enumerate(reader, start=1):
                for column, value in row.items():
                    if value is None or value == '':
                        continue
                    try:
                        number = float(value)
                    except ValueError:
                        continue
                    numeric_seen = True
                    if not math.isfinite(number):
                        errors.append(
                            f'{path.name} row {row_index} column {column} '
                            'is not finite')
            if not numeric_seen:
                errors.append(f'{path.name} has no numeric detector values')
    except OSError as exc:
        errors.append(f'could not read {path.name}: {exc}')


def check_detector_response(path):
    errors = []
    manifest_path = Path(path)
    if manifest_path.is_dir():
        manifest_path = manifest_path / 'detector_response_manifest.json'
    if not manifest_path.exists():
        return {}, [f'missing manifest: {manifest_path}']

    try:
        with open(manifest_path) as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f'could not read manifest: {exc}']

    for field in REQUIRED_FIELDS:
        if field not in manifest:
            errors.append(f'missing manifest field "{field}"')

    if manifest.get('schema_version') != EXPECTED_SCHEMA_VERSION:
        errors.append(
            f'manifest schema_version is {manifest.get("schema_version")}; '
            f'expected {EXPECTED_SCHEMA_VERSION}')

    normalization = manifest.get('source_normalization')
    if normalization is not None and not _is_finite_number(normalization):
        errors.append('source_normalization is not finite or null')

    for field in ('source_type', 'source_units', 'detector_name',
                  'detector_cell_id', 'detector_material',
                  'geometry_description', 'tally_name', 'tally_score',
                  'energy_units', 'tally_units'):
        if manifest.get(field) in (None, ''):
            errors.append(f'manifest field "{field}" is required')

    _check_energy_bins(manifest, errors)
    _check_time_metadata(manifest, errors)

    entries = list(_iter_export_entries(manifest.get('export_files')))
    if not entries:
        errors.append('export_files must list at least one file')
    export_count = 0
    for entry in entries:
        relpath = entry.get('path')
        if not relpath:
            errors.append('export file entry is missing path')
            continue
        export_count += 1
        export_path = manifest_path.parent / relpath
        if not export_path.exists():
            errors.append(f'missing export file: {relpath}')
            continue
        suffix = export_path.suffix.lower()
        if suffix == '.csv':
            _check_csv(export_path, errors)
        elif suffix in ('.h5', '.hdf5'):
            try:
                import h5py
            except ImportError:
                errors.append(f'h5py is required to read {relpath}')
            else:
                try:
                    with h5py.File(export_path, 'r'):
                        pass
                except OSError as exc:
                    errors.append(f'could not read {relpath}: {exc}')
        else:
            errors.append(f'unsupported export file extension: {relpath}')

    return {
        'path': str(manifest_path),
        'schema_version': manifest.get('schema_version'),
        'export_files': export_count,
        'source_type': manifest.get('source_type'),
        'detector_cell_id': manifest.get('detector_cell_id'),
    }, errors


def main():
    parser = argparse.ArgumentParser(
        description='Validate an OpenMC detector response export manifest.')
    parser.add_argument(
        'path', help='Path to detector_response_manifest.json or its directory.')
    parser.add_argument('--summary-json', action='store_true',
                        help='Print the validation summary as JSON.')
    args = parser.parse_args()

    summary, errors = check_detector_response(args.path)
    if args.summary_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f'{summary.get("path", args.path)}: '
              f'{summary.get("export_files", 0)} export files')

    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
