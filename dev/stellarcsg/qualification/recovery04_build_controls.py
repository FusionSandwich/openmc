#!/usr/bin/env python3
"""Serial local builds using only preflighted installed libraries and sources."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    work = a.repo.parent
    source = a.repo / 'dev/stellarcsg/qualification/recovery04_frozen_bank.cpp'
    build = a.repo / 'build'
    commands = [
        ['cmake', '-S', str(work/'stellarcsg-cont-a/dev/stellarcsg'), '-B', str(build/'recovery-04-A'), '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release', '-DSTELLARCSG_ENABLE_HDF5=ON'],
        ['cmake', '--build', str(build/'recovery-04-A'), '--target', 'stellarcsg_reference', '--parallel', '1'],
        ['cmake', '--build', str(build/'recovery-04-seed'), '--target', 'stellarcsg_recovery04_bank', '--parallel', '1'],
    ]
    bindings = [
        ('old', a.repo, build/'recovery-04-baseline/libstellarcsg_reference.a', []),
        ('previous_A', work/'stellarcsg-cont-a', build/'recovery-04-A/libstellarcsg_reference.a', []),
        ('exact_reference', work/'stellarcsg-fast-03', Path('/mnt/d/codex-verification/stellarcsg-20260913-03/kernel-off/libstellarcsg_reference.a'), ['-lgmpxx', '-lgmp']),
    ]
    for name, repo, library, extra in bindings:
        commands.append(['g++', '-std=c++17', '-O3', '-DNDEBUG', '-DSTELLARCSG_HAS_HDF5',
            '-I'+str(repo/'dev/stellarcsg/include'), '-I/usr/include/hdf5/serial', str(source), str(library),
            '-L/usr/lib/x86_64-linux-gnu/hdf5/serial', '-lhdf5_hl', '-lhdf5', *extra, '-o', str(a.output/name)])
    receipt = {'acquisition_bytes': 0, 'dependency_environment_changes': False,
        'parallel_compilers': 1, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'attempts': []}
    for i, command in enumerate(commands):
        with (a.output/f'{i}.stdout').open('w') as out, (a.output/f'{i}.stderr').open('w') as err:
            result = subprocess.run(command, stdout=out, stderr=err, timeout=180)
        receipt['attempts'].append({'command': command, 'exit_code': result.returncode})
        (a.output/'receipt.json').write_text(json.dumps(receipt, indent=2))
        print(i, result.returncode, flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
    receipt['library_hashes'] = {str(lib): hashlib.sha256(lib.read_bytes()).hexdigest() for _, _, lib, _ in bindings}
    receipt['binary_hashes'] = {name: hashlib.sha256((a.output/name).read_bytes()).hexdigest() for name, _, _, _ in bindings}
    (a.output/'receipt.json').write_text(json.dumps(receipt, indent=2))
