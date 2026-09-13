#!/usr/bin/env python3
"""Reproduce archived microbenchmarks without changing their timed ray banks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sentinel', type=Path, required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--coil-file', type=Path, required=True)
    parser.add_argument('--plasma-file', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    qualified = repo / 'dev/stellarcsg/qualified'
    args.output.mkdir(parents=True, exist_ok=False)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    commands = {
        'ztorus_before': [str(args.sentinel), '--banks', '10000'],
        'wistell_coil031_historical_bank': [str(args.build / 'stellarcsg_file_swept_benchmark'),
            str(args.coil_file), '/coils/coil_031', '1'],
        'wistell_plasma_historical_bank': [str(args.build / 'stellarcsg_file_surface_benchmark'),
            str(args.plasma_file), '/surfaces/wistell_d'],
        'ztorus_after': [str(args.sentinel), '--banks', '10000'],
    }
    report = {'schema': 'stellarcsg.recovery04.historical-reproduction/v1',
        'source_sha': args.source_sha,
        'affinity': sorted(os.sched_getaffinity(0)), 'started': time.time(),
        'note': 'Historical-bank reproduction only. Sentinel repeats 64 rays without an application cache. Coil classification repeats miss origins and is not cold unique classification. Oracle reduced to one ray OUTSIDE the timed loop. No whole-machine transport or 48-coil run.',
        'measurements': {}}
    for label, cmd in commands.items():
        records = []
        for repeat in range(8):
            attempt = {'command': cmd, 'repeat': repeat, 'warmup': repeat == 0}
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                (args.output / f'{label}-{repeat}.stdout').write_text(result.stdout)
                (args.output / f'{label}-{repeat}.stderr').write_text(result.stderr)
                attempt['exit_code'] = result.returncode
                attempt['result'] = json.loads(result.stdout)
            except Exception as exc:
                attempt['error'] = repr(exc)
            records.append(attempt)
            report['measurements'][label] = {'binary_sha256': sha(cmd[0]), 'attempts': records}
            (args.output / 'receipt.json').write_text(json.dumps(report, indent=2))
        valid = [r['result'] for r in records[1:] if r.get('exit_code') == 0 and 'error' not in r]
        stats = {}
        for key in ('ns_per_query', 'distance_ns_per_call', 'classification_ns_per_call'):
            vals = [v[key] for v in valid if key in v]
            if vals:
                stats[key] = {'median_of_bank_means': statistics.median(vals), 'min': min(vals), 'max': max(vals), 'repetitions': len(vals)}
        report['measurements'][label]['statistics'] = stats
        print(label, json.dumps(stats), flush=True)
    report['finished'] = time.time()
    report['payload_hashes'] = {str(p): sha(p) for p in (args.coil_file, args.plasma_file)}
    (args.output / 'receipt.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
