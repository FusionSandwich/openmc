#!/usr/bin/env python3
"""Durably record bounded, pinned, unique-query subprocess attempts."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--lane', action='append', required=True, help='label=/absolute/binary')
    p.add_argument('--bank', type=Path, required=True)
    p.add_argument('--coils', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repetitions', type=int, default=7)
    a = p.parse_args()
    with a.bank.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    keys = [(r['geometry'], r['category'].startswith('coincident_'),
             *(float(r[k]) for k in ('ox', 'oy', 'oz', 'dx', 'dy', 'dz'))) for r in rows]
    if len(rows) != 160 or len(set(keys)) != 160:
        raise ValueError('Primary timing requires 160 distinct query input tuples')
    a.output.mkdir(parents=True, exist_ok=False)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    lanes = dict(entry.split('=', 1) for entry in a.lane)
    hashes = {str(f): hashlib.sha256(Path(f).read_bytes()).hexdigest()
              for f in [a.bank, a.coils, *lanes.values()]}
    receipt = {'schema': 'stellarcsg.recovery04.measure/v1', 'hashes': hashes,
        'affinity': sorted(os.sched_getaffinity(0)), 'attempts': [],
        'note': 'One unique bank per fresh process; reference calls disabled. Per-call timer overhead is included; setup, classification and normal calls are outside distance timers.'}
    for repeat in range(a.repetitions):
        schedule = list(lanes.items())
        if repeat % 2:
            schedule.reverse()
        for name, binary in schedule:
            command = [binary, '--replay', str(a.bank), '--wistell-h5', str(a.coils), '--skip-reference']
            attempt = {'lane': name, 'repeat': repeat, 'command': command, 'started': time.time()}
            stdout, stderr = a.output / f'{name}-{repeat}.jsonl', a.output / f'{name}-{repeat}.stderr'
            try:
                with stdout.open('w') as out, stderr.open('w') as err:
                    run = subprocess.run(command, stdout=out, stderr=err, timeout=180)
                attempt['exit_code'] = run.returncode
            except subprocess.TimeoutExpired:
                attempt['timeout'] = True
            attempt.update(finished=time.time(), stdout=stdout.name, stderr=stderr.name)
            receipt['attempts'].append(attempt)
            (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2))
            print(name, repeat, attempt.get('exit_code', 'TIMEOUT'), flush=True)
