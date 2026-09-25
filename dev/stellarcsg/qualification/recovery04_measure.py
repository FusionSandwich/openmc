#!/usr/bin/env python3
"""Durably record bounded, pinned, unique-query subprocess attempts."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--lane', action='append', required=True, help='label=/absolute/binary')
    p.add_argument('--bank', type=Path, required=True)
    p.add_argument('--coils', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repetitions', type=int, default=7)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--native-ztorus', type=Path)
    p.add_argument('--native-library', type=Path)
    a = p.parse_args()
    if bool(a.native_ztorus) != bool(a.native_library):
        p.error('native ZTorus executable and OpenMC library must be supplied together')
    if a.repetitions < 1:
        p.error('repetitions must be positive')
    parsed_lanes = [entry.split('=', 1) for entry in a.lane]
    if any(len(parts) != 2 or not parts[0] or not parts[1] for parts in parsed_lanes):
        p.error('each lane must be label=/absolute/binary')
    names = [parts[0] for parts in parsed_lanes]
    if len(set(names)) != len(names):
        p.error('duplicate lane labels are forbidden')
    lanes = dict(parsed_lanes)
    if any(not Path(binary).is_file() for binary in lanes.values()):
        p.error('every lane executable must exist')
    with a.bank.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    keys = [(r['geometry'], r['category'].startswith('coincident_'),
             *(float(r[k]) for k in ('ox', 'oy', 'oz', 'dx', 'dy', 'dz'))) for r in rows]
    if len(rows) != 160 or len(set(keys)) != 160:
        raise ValueError('Primary timing requires 160 distinct query input tuples')
    if not a.coils.is_file():
        p.error('coils fixture must exist')
    if a.native_ztorus:
        if not a.native_ztorus.is_file() or not a.native_library.is_file():
            p.error('native executable/library must exist')
        loader = subprocess.run(['ldd', str(a.native_ztorus)], capture_output=True,
                                text=True, check=False)
        bindings = [line for line in loader.stdout.splitlines() if 'libopenmc.so' in line]
        if loader.returncode or len(bindings) != 1 or str(a.native_library.resolve()) not in bindings[0]:
            p.error('native ZTorus is not bound to the specified OpenMC library')
    a.output.mkdir(parents=True, exist_ok=False)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    hashes = {str(f): hashlib.sha256(Path(f).read_bytes()).hexdigest()
              for f in [a.bank, a.coils, *lanes.values(),
                        *([a.native_ztorus, a.native_library] if a.native_ztorus else [])]}
    receipt = {'schema': 'stellarcsg.recovery04.measure/v1', 'hashes': hashes,
        'source_commit': a.source_commit,
        'affinity': sorted(os.sched_getaffinity(0)), 'attempts': [],
        'native_attempts': [], 'native_openmc_loader_binding': bindings[0].strip() if a.native_ztorus else None,
        'state': 'INCOMPLETE',
        'note': 'One unique bank per fresh process; reference calls disabled. Per-call timer overhead is included; setup, classification and normal calls are outside distance timers.'}
    def run_native(repeat, position):
        command = [str(a.native_ztorus), '--banks', '10000']
        stdout = a.output / f'native-{position}-{repeat}.json'
        stderr = a.output / f'native-{position}-{repeat}.stderr'
        attempt = {'repeat': repeat, 'position': position, 'command': command}
        try:
            with stdout.open('w') as out, stderr.open('w') as err:
                completed = subprocess.run(command, stdout=out, stderr=err, timeout=30)
            attempt['exit_code'] = completed.returncode
            result = json.loads(stdout.read_text()) if completed.returncode == 0 else None
            attempt['result'] = result
            attempt['valid'] = (isinstance(result, dict) and
                                result.get('kind') == 'native_ztorus_absolute_control' and
                                result.get('queries') == 640000)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            attempt['error'] = str(error)
            attempt['valid'] = False
        attempt.update(stdout=stdout.name, stderr=stderr.name)
        receipt['native_attempts'].append(attempt)
        (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    for repeat in range(a.repetitions):
        if a.native_ztorus:
            run_native(repeat, 'before')
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
        if a.native_ztorus:
            run_native(repeat, 'after')
    exits = [attempt.get('exit_code') for attempt in receipt['attempts']]
    native_valid = all(attempt['valid'] for attempt in receipt['native_attempts'])
    receipt['state'] = 'PASS' if all(code == 0 for code in exits) and native_valid else 'BLOCKED' if None in exits or 2 in exits else 'FAIL'
    (a.output / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    sys.exit(0 if receipt['state'] == 'PASS' else 2 if receipt['state'] == 'BLOCKED' else 1)
