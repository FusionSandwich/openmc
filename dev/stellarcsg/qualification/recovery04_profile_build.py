#!/usr/bin/env python3
"""Build separate instrumented controls without changing production defaults."""
import argparse
import json
from pathlib import Path
import subprocess


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    old = a.repo.parent / 'stellarcsg-recovery-bank-04'
    commands = []
    for name, repo in [('old-on', old), ('seed-on', a.repo)]:
        build = a.output / name
        commands += [
            ['cmake', '-S', str(repo/'dev/stellarcsg'), '-B', str(build), '-G', 'Ninja',
             '-DCMAKE_BUILD_TYPE=Release', '-DSTELLARCSG_ENABLE_HDF5=ON', '-DSTELLARCSG_ENABLE_PERFORMANCE_COUNTERS=ON'],
            ['cmake', '--build', str(build), '--target', 'stellarcsg_reference', '--parallel', '1'],
            ['g++', '-std=c++17', '-O3', '-DNDEBUG', '-DSTELLARCSG_HAS_HDF5', '-DSTELLARCSG_ENABLE_PERFORMANCE_COUNTERS',
             '-I'+str(repo/'dev/stellarcsg/include'), '-I/usr/include/hdf5/serial',
             str(a.repo/'dev/stellarcsg/qualification/recovery04_frozen_bank.cpp'), str(build/'libstellarcsg_reference.a'),
             '-L/usr/lib/x86_64-linux-gnu/hdf5/serial', '-lhdf5_hl', '-lhdf5', '-o', str(a.output/name.replace('-on', '_bank'))]]
    receipt = {'acquisition_bytes': 0, 'dependency_environment_changes': False, 'attempts': []}
    for index, command in enumerate(commands):
        with (a.output/f'{index}.stdout').open('w') as out, (a.output/f'{index}.stderr').open('w') as err:
            result = subprocess.run(command, stdout=out, stderr=err, timeout=180)
        receipt['attempts'].append({'command': command, 'exit_code': result.returncode})
        (a.output/'receipt.json').write_text(json.dumps(receipt, indent=2))
        print(index, result.returncode, flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
