#!/usr/bin/env python3
"""Run retained 384-ray capture and compare with separately retained reference."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    capture = a.output / 'capture.jsonl'
    command = [str(a.binary), str(a.input)]
    with capture.open('w') as out, (a.output / 'stderr.txt').open('w') as err:
        run = subprocess.run(command, stdout=out, stderr=err, timeout=180)
    candidate = rows(capture)
    reference = rows(a.reference)
    cr = {(r['shape'], r['index']): r for r in candidate if r['kind'] == 'ray'}
    rr = {(r['shape'], r['index']): r for r in reference if r['kind'] == 'ray'}
    assert cr.keys() == rr.keys() and len(cr) == 384
    assert [r for r in candidate if r['kind'] == 'geometry'] == [r for r in reference if r['kind'] == 'geometry']
    mismatches, outside_domain = [], []
    for key, ref in rr.items():
        row = cr[key]
        assert (row['origin'], row['direction']) == (ref['origin'], ref['direction'])
        if ref['state'] == 'BLOCKED':
            outside_domain.append({'shape': key[0], 'index': key[1],
                'reference_state': 'BLOCKED', 'reference_reason': ref.get('error'),
                'candidate_state': row['state'], 'candidate_distance': row.get('distance')})
            continue
        errors = []
        for name in ('distance', 'scaled_distance', 'rigid_distance'):
            x, y = row.get(name), ref.get(name)
            if (x is None) != (y is None) or (x is not None and abs(x-y) > 2e-8):
                errors.append(name)
        if row.get('found') != ref.get('found') or row['state'] != 'PASS':
            errors.append('disposition')
        if errors:
            mismatches.append({'shape': key[0], 'index': key[1], 'fields': errors,
                'candidate': row, 'reference': ref})
    result = {'schema': 'stellarcsg.recovery04.retained-replay/v1',
        'command': command, 'exit_code': run.returncode,
        'hashes': {str(f): sha(f) for f in (a.binary, a.input, a.reference, capture)},
        'candidate_metamorphic_states': dict(Counter(r['state'] for r in cr.values())),
        'reference_states': dict(Counter(r['state'] for r in rr.values())),
        'admitted_reference_cases': 384-len(outside_domain),
        'admitted_wrong_root_or_metamorphism_count': len(mismatches),
        'mismatches': mismatches, 'reference_blocked_cases': outside_domain,
        'warning': 'Candidate PASS is a retained harness metamorphic result, not a root-completeness certificate. Reference BLOCKED remains BLOCKED even if the candidate returns a value.'}
    (a.output / 'comparison.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ('mismatches', 'reference_blocked_cases', 'hashes', 'command')}, indent=2))


if __name__ == '__main__':
    main()
