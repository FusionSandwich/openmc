"""Bounded replay of unchanged rays with explicit cross-representation limits."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


BANK = Path('dev/stellarcsg/qualification/recovery04_frozen_bank.csv')
PROVENANCE_PATHS = (
    'binary', 'frozen_csv', 'wistell_h5', 'offset_engine_cpp',
    'offset_engine_hpp', 'exact_dyadic_hpp', 'frozen_bank_cpp', 'runner_script',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _object_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON object key: {key}')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f'nonstandard JSON constant: {value}')


def _load_json_line(line):
    value = json.loads(line, object_pairs_hook=_object_no_duplicates,
                       parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise ValueError('JSONL record must be an object')
    return value


def _frozen_ids(bank):
    with Path(bank).open(newline='', encoding='utf-8') as stream:
        return [row['id'] for row in csv.DictReader(stream)]


def _read_jsonl(path):
    parsed = []
    malformed = []
    for index, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines()):
        if not line.strip():
            malformed.append(index + 1)
            continue
        try:
            parsed.append(_load_json_line(line))
        except (ValueError, json.JSONDecodeError):
            malformed.append(index + 1)
    return parsed, malformed


def _valid_queries(rows, malformed, bank):
    queries = [row for row in rows if row.get('kind') == 'query']
    summaries = [row for row in rows if row.get('kind') == 'summary']
    ids = [row.get('id') for row in queries]
    expected = _frozen_ids(bank)
    valid = (not malformed and len(rows) == 161 and len(summaries) == 1 and
             len(queries) == 160 and len(expected) == 160 and
             ids == expected and all(row.get('geometry_representation') ==
                                     'exact_control_offset' for row in queries))
    return queries, valid


def _provenance_paths(args):
    return {
        'binary': args.binary,
        'frozen_csv': BANK,
        'wistell_h5': args.wistell,
        'offset_engine_cpp': Path('dev/stellarcsg/src/certified_spline_offset.cpp'),
        'offset_engine_hpp': Path('dev/stellarcsg/include/stellarcsg/certified_spline_offset.hpp'),
        'exact_dyadic_hpp': Path('dev/stellarcsg/src/exact_dyadic.hpp'),
        'frozen_bank_cpp': Path('dev/stellarcsg/qualification/recovery04_frozen_bank.cpp'),
        'runner_script': Path(__file__),
    }


def _capture_hashes(paths):
    return {name: sha(path) for name, path in paths.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--wistell', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    paths = _provenance_paths(args)
    hashes_before = _capture_hashes(paths)
    command = [str(args.binary), '--replay', str(BANK), '--wistell-h5',
               str(args.wistell), '--skip-reference', '--exact-control-offset']
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    before = time.time()
    launch = {
        'pid': None, 'started': before, 'command': command,
        'timeout_seconds': 900, 'memory_limit_inherited': True,
        'hashes_before': hashes_before,
        'build_binding_limitation': 'Hash equality observes file identity before and after execution; it does not prove which sources or headers the compiler consumed to produce the binary.'
    }
    (args.output/'launch.json').write_text(json.dumps(launch, indent=2)+'\n')
    with (args.output/'candidate.jsonl').open('w') as out, (args.output/'stderr.txt').open('w') as err:
        child = subprocess.Popen(command, stdout=out, stderr=err, env=env)
        launch['pid'] = child.pid
        (args.output/'launch.json').write_text(json.dumps(launch, indent=2)+'\n')
        print(json.dumps({'pid': child.pid, 'started': before, 'command': command}), flush=True)
        timed_out = False
        try:
            code = child.wait(timeout=900)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            code = child.wait()

    rows, malformed = _read_jsonl(args.output/'candidate.jsonl')
    queries, output_valid = _valid_queries(rows, malformed, BANK)
    exact_rows, exact_malformed = _read_jsonl(Path(
        'dev/stellarcsg/reports/local-cont-20260925/strict-old-01/exact-reference-0.jsonl'))
    exact = {row['id']: row for row in exact_rows
             if row.get('kind') == 'query' and isinstance(row.get('id'), str)}
    different = []
    if output_valid and not exact_malformed:
        for row in queries:
            if row.get('candidate_state') != 'PASS' or row['id'] not in exact:
                continue
            legacy = exact[row['id']]
            if (row.get('candidate_found') != legacy.get('candidate_found') or
                (row.get('candidate_found') and
                 abs(row['candidate_distance']-legacy['candidate_distance']) > 2e-8)):
                different.append(row['id'])

    hashes_after = _capture_hashes(paths)
    changed_paths = [paths[name].as_posix() for name in PROVENANCE_PATHS
                     if hashes_before[name] != hashes_after[name]]
    report = {
        'schema': 'stellarcsg.offset-bank-observation/v1',
        'geometry_representation': 'exact_control_offset',
        'state': 'OBSERVATION_ONLY_DIFFERENT_REPRESENTATION',
        'exit_code': code, 'timed_out': timed_out, 'seconds': time.time()-before,
        'query_count': len(queries), 'malformed_lines': malformed,
        'output_valid': output_valid,
        'dispositions': dict(Counter(q.get('candidate_disposition', 'missing') for q in queries)),
        'candidate_states': dict(Counter(q.get('candidate_state', 'missing') for q in queries)),
        'telemetry_states': dict(Counter(q.get('telemetry_state', 'missing') for q in queries)),
        'resolved_differences_from_legacy_reference': different,
        'old_wrong_ids': {q['id']: q for q in queries if q.get('id') in ('a03','a06','a08','a15')},
        'hashes_before': hashes_before,
        'hashes_after': hashes_after,
        'provenance_unchanged': not changed_paths,
        'changed_paths': changed_paths,
        'candidate_jsonl_sha256': sha(args.output/'candidate.jsonl'),
        'build_binding_limitation': 'Hash equality observes file identity before and after execution; it does not prove which sources or headers the compiler consumed to produce the binary.',
        'claim_boundary': 'Unchanged frozen input rays, explicitly changed represented surface. Legacy oracle agreement is descriptive, not qualification of the new surface. No full-bank PASS or matched performance claim.',
    }
    (args.output/'receipt.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('exit_code','timed_out','seconds','query_count',
        'output_valid','provenance_unchanged','changed_paths','dispositions','candidate_states',
        'resolved_differences_from_legacy_reference')}))
    return 0 if output_valid and not timed_out and code == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
