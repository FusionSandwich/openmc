"""Bounded local native acceptance; existing dependencies, isolated outputs only."""
import copy
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from fractions import Fraction as F
from functools import partial
import resource
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts'
LOCK = ROOT.parent / 'local-coil-wave-20260926/compute.lock'
NATIVE = Path('/var/tmp') / f'stellarcsg-axis-review-20261008-{os.getpid()}-{time.time_ns()}'
REUSED_ROOT = None
CAP = 300 * 2**20


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def size(path):
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())


def limits(building=False):
    memory = 1536 * 2**20 if building else 2**30
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def run(label, args, deadline, cap=None):
    end = min(deadline, time.monotonic() + cap) if cap else deadline
    started = time.monotonic()
    env = os.environ | {'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
    with (OUT / f'{label}.stdout').open('w') as stdout, (OUT / f'{label}.stderr').open('w') as stderr:
        child = subprocess.Popen(args, stdout=stdout, stderr=stderr, env=env,
                                 preexec_fn=partial(limits, label.startswith(('build-', 'configure-'))),
                                 start_new_session=True)
        try:
            while child.poll() is None:
                if time.monotonic() >= end:
                    raise TimeoutError(f'{label}: phase deadline')
                if size(NATIVE) + size(OUT) + (size(REUSED_ROOT) if REUSED_ROOT else 0) > CAP:
                    raise RuntimeError(f'{label}: output cap')
                time.sleep(1)
        except BaseException:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=10)
            raise
    save(f'{label}.exit.json', {'args': list(map(str, args)), 'exit': child.returncode,
                              'seconds': time.monotonic() - started})
    if child.returncode:
        raise RuntimeError(f'FIRST_FAILURE {label} exit={child.returncode}')
    return (OUT / f'{label}.stdout').read_text()


def retained():
    parent = ROOT.parent / 'stellarcsg-astra-kernel-20260926'
    pins = {'current': '9bf312f3e556b586fec44b714f179b97fa8dd5a25a249951674b01174b49432d',
            'baseline': '546be4c8af7da69196d6b4408de7bfb9af6ac0ddb424a90205cd513b60c19b9a'}
    for kind, identity in pins.items():
        path = parent / f'dev/stellarcsg/reports/p00-step1-20261001-01/{kind}/build/lib/libopenmc.so'
        assert sha(path) == identity, path


def client(label, build, folder, queries, deadline):
    output = run(label, [build / 'bin/stellarcsg_native_axis_test', folder,
                        folder / 'queries.txt'], deadline, 20)
    metadata = [json.loads(line[5:]) for line in output.splitlines() if line.startswith('META ')]
    assert len(metadata) == 1, metadata
    loaded = Path(metadata[0]['library']).resolve()
    assert loaded == (build / 'lib/libopenmc.so').resolve(), metadata
    rows = [json.loads(line[4:]) for line in output.splitlines() if line.startswith('ROW ')]
    assert len(rows) == 2 * len(queries), (label, len(rows), len(queries))
    for cycle in range(2):
        for row, query in zip(rows[cycle * len(queries):(cycle + 1) * len(queries)], queries):
            assert row['id'] == query['id'] and row['cycle'] == cycle
            assert row['fixture_restored'] and row['source_reset'], row
    return rows


def main():
    global OUT, REUSED_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-name', default='artifacts')
    parser.add_argument('--reuse-phase', type=Path)
    parser.add_argument('--phase-seconds', type=int, default=900)
    parser.add_argument('--cross-sections', type=Path, default=Path(
        '/mnt/d/openc-hts-dpa-data/openmc-data/endfb-vii.1-hdf5/cross_sections.xml'))
    options = parser.parse_args()
    assert Path(options.output_name).name == options.output_name
    assert 1 <= options.phase_seconds <= 1800
    OUT = ROOT / options.output_name
    started = time.monotonic()
    deadline = started + options.phase_seconds
    OUT.mkdir()  # No overwrite, no reclaim of another owner's lease.
    mem = {line.split(':')[0]: int(line.split()[1]) * 1024
           for line in Path('/proc/meminfo').read_text().splitlines()}
    assert mem['MemAvailable'] >= 3 * 2**30
    assert all(shutil.disk_usage(p).free >= 2 * 2**30 for p in [ROOT, '/mnt/c', '/mnt/d', NATIVE.parent])
    retained()
    assert options.cross_sections.is_file()
    xs_identity = sha(options.cross_sections)
    LOCK.mkdir()
    token = f'axis-review-{os.getpid()}-{time.time_ns()}'
    owner_file = LOCK / 'AXIS_REVIEW_OWNER.json'
    owner_file.write_text(json.dumps({'owner': token, 'workers': 1, 'phase_seconds': options.phase_seconds,
                                     'build_virtual_bytes': 1536 * 2**20,
                                     'test_virtual_bytes': 2**30, 'output_bytes': CAP}))
    try:
        save('admission.json', {'mem_available': mem['MemAvailable'], 'acquisition_bytes': 0,
             'source': str(ROOT), 'native': str(NATIVE), 'deadline_seconds': options.phase_seconds,
             'tools': {name: shutil.which(name) for name in ['g++', 'cmake', 'python3']},
             'git_pointer_diagnosis': 'Windows worktree pointer is invalid in WSL; copy has no .git',
             'configure_cap_seconds_per_build': 150,
             'cross_sections_index': str(options.cross_sections), 'index_sha256': xs_identity})
        NATIVE.mkdir()
        native_source = NATIVE / 'source'
        native_source.mkdir()
        for name in ['src', 'include', 'cmake', 'vendor']:
            shutil.copytree(ROOT / name, native_source / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        # A full repository also contains retained experiments under dev/.
        # Copy the native build/test inputs, never another agent's reports.
        development = native_source / 'dev/stellarcsg'
        development.mkdir(parents=True)
        for name in ['src', 'include', 'tests', 'openmc_adapter']:
            shutil.copytree(ROOT / 'dev/stellarcsg' / name, development / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for name in ['CMakeLists.txt', 'AXIS_REVIEW_REPAIR_20261008.md']:
            shutil.copy2(ROOT / 'dev/stellarcsg' / name, development / name)
        shutil.copy2(ROOT / 'CMakeLists.txt', native_source)
        shutil.copy2(ROOT / '.git_archival.txt', native_source)
        # CMake's existing post-build step copies only into this isolated tree.
        (native_source / 'openmc/lib').mkdir(parents=True)
        identities = {str(p.relative_to(native_source)): sha(p)
                      for p in native_source.rglob('*') if p.is_file()}
        save('source-identities.json', identities)
        spec = importlib.util.spec_from_file_location('axis_fixture', ROOT / 'dev/stellarcsg/tests/P00_NATIVE_AXIS_ACCEPTANCE_20261001.py')
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        fixtures.OUT = OUT
        fixtures.XS = options.cross_sections
        results = []
        builds = {}
        for enabled in [True, False]:
            kind = 'on' if enabled else 'off'
            build = NATIVE / kind
            if enabled and options.reuse_phase:
                prior = json.loads((options.reuse_phase / 'failure.json').read_text())
                REUSED_ROOT = Path(prior['native_outputs'])
                prior_sources = json.loads((options.reuse_phase / 'source-identities.json').read_text())
                for name, identity in prior_sources.items():
                    # Only the Python fixture/runner and explanatory prose may
                    # differ. Every compiled/configuration input must match.
                    if name.endswith(('.py', '.md')):
                        continue
                    assert sha(ROOT / name) == identity == sha(REUSED_ROOT / 'source' / name), name
                build = REUSED_ROOT / 'on'
                pinned = json.loads((options.reuse_phase / 'binary-identities-on.json').read_text())
                assert sha(build / 'lib/libopenmc.so') == pinned['library_sha256']
                assert sha(build / 'bin/stellarcsg_native_axis_test') == pinned['client_sha256']
                assert sha(build / 'compile_commands.json') == pinned['compile_commands_sha256']
                save('reused-on-build.json', {'phase': str(options.reuse_phase), 'build': str(build),
                     'compiled_inputs_match': True, 'binaries': pinned})
            builds[kind] = build
            if not (enabled and options.reuse_phase):
                run(f'configure-{kind}', ['cmake', '-S', native_source, '-B', build,
                '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CXX_FLAGS_RELEASE=-O0 -DNDEBUG',
                '-DOPENMC_USE_MPI=OFF', '-DOPENMC_USE_OPENMP=OFF', '-DOPENMC_BUILD_TESTS=OFF',
                '-DOPENMC_FORCE_VENDORED_LIBS=ON', '-DFETCHCONTENT_FULLY_DISCONNECTED=ON',
                '-DGIT_SUBMODULE=OFF', '-DOPENMC_ENABLE_STRICT_FP=ON',
                '-DSTELLARCSG_BUILD_AXIS_TEST_CLIENT=ON',
                f'-DOPENMC_ENABLE_EXPERIMENTAL_AXIS_PLANES={"ON" if enabled else "OFF"}',
                    '-DOPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=OFF'], deadline, 150)
                run(f'build-{kind}', ['cmake', '--build', build, '--target',
                                    'stellarcsg_native_axis_test', '-j', '1'], deadline)
            run(f'loader-{kind}', ['ldd', build / 'bin/stellarcsg_native_axis_test'], deadline, 10)
            save(f'binary-identities-{kind}.json', {'library_sha256': sha(build / 'lib/libopenmc.so'),
                  'client_sha256': sha(build / 'bin/stellarcsg_native_axis_test'),
                  'compile_commands_sha256': sha(build / 'compile_commands.json')})
            commands = json.loads((build / 'compile_commands.json').read_text())
            client_command = next(c['command'] for c in commands if c['file'].endswith('/test_native_axis_events.cpp'))
            assert ('-DOPENMC_EXPERIMENTAL_AXIS_PLANES' in client_command) == enabled
            if not enabled:
                continue
            for axis in range(3):
                for case, offset, duplicate in [('gap48', 1 + 2**-48, False),
                    ('adjacent', math.nextafter(1., 2.), False), ('touching', 1., False), ('duplicate', 0., True)]:
                    for reverse in [False, True]:
                        name = f'{case}-axis{axis}-tokens{int(reverse)}'
                        folder, planes, queries = fixtures.fixture(name, axis, offset, reverse, duplicate=duplicate)
                        rows = client(name, build, folder, queries, deadline)
                        for row, q in zip(rows, queries * 2):
                            fixtures.check(row, fixtures.expected(planes, axis, q))
                        results.append({'model': name, 'rows': rows})
                        save('results.json', results)
            folder, planes, queries = fixtures.fixture('rounded-times', 0, 1 + 2**-48, huge=True)
            rows = client('rounded-times', build, folder, queries, deadline)
            for row, q in zip(rows, queries * 2):
                fixtures.check(row, fixtures.expected(planes, 0, q))
            results.append({'model': 'rounded-times', 'rows': rows})
            for guard in ['oblique', 'nonunit', 'coplanar', 'nonplanar', 'time', 'filter',
                          'stale', 'collision', 'material', 'overflow', 'masked-vacuum', 'sentinel', 'unbounded-extreme', 'surface-bank']:
                folder, planes, queries = fixtures.fixture('unsupported-' + guard, 0, 1 + 2**-48, guard=guard)
                rows = client('unsupported-' + guard, build, folder, queries, deadline)
                for row, q in zip(rows, queries * 2):
                    if guard in ['stale', 'collision', 'material', 'overflow'] and q['mode'] == 0:
                        fixtures.check(row, fixtures.expected(planes, 0, q))
                    else:
                        assert row['events'] == [] and 'AXIS_PLANE_UNSUPPORTED:' in row['error'], row
                        assert all(v == 0 for tally in row['scores'] for v in tally), row
                        if guard == 'overflow':
                            assert 'NO_START_OWNER' not in row['error'], row
                if guard in ['masked-vacuum', 'unbounded-extreme']:
                    try:
                        fixtures.expected(planes, 0, queries[0])
                    except ValueError:
                        pass
                    else:
                        raise AssertionError('oracle accepted unsupported vacuum enclosure')
                if guard == 'sentinel':
                    # Finite equality, independently distinguished from overflow.
                    exact = F(planes[6][2]) - F(queries[0]['p'][0])
                    assert exact == F(float.fromhex('0x1.fffffffffffffp+1023'))
                    try:
                        fixtures.expected(planes, 0, queries[0])
                    except ValueError:
                        pass
                    else:
                        raise AssertionError('oracle accepted sentinel collision')
                if guard in ['masked-vacuum', 'sentinel', 'unbounded-extreme']:
                    assert all(r['source_position_unchanged'] for r in rows)
                results.append({'model': 'unsupported-' + guard, 'rows': rows})
                save('results.json', results)
        # Identical full legacy itineraries in the same-build runtime-off path
        # and a matching-header compile-option-off library. Retain known gaps.
        legacy = []
        for axis in range(3):
            for case, offset in [('resolved', 2.), ('gap48', 1 + 2**-48)]:
                name = f'legacy-{case}-axis{axis}'
                folder, planes, queries = fixtures.fixture(name, axis, offset, runtime=False)
                on_rows = client(name + '-on', builds['on'], folder, queries, deadline)
                off_rows = client(name + '-off', builds['off'], folder, queries, deadline)
                assert on_rows == off_rows, name
                assert all(not e['context'] for r in on_rows for e in r['events'])
                assert all(r['error'] == '' and r['events'] and r['events'][-1]['weight'] == 0 for r in on_rows)
                witness = False
                if case == 'gap48':
                    for row, q in zip(on_rows, queries * 2):
                        correct = fixtures.expected(planes, axis, q)
                        witness |= [e['length'] for e in row['events']] != [e['length'] for e in correct]
                    assert witness, 'expected legacy gap48 length/ownership witness absent'
                legacy.append({'model': name, 'rows': on_rows,
                               'legacy_negative_witness': witness})
        save('legacy-results.json', legacy)
        row = results[0]['rows'][0]
        wanted = fixtures.expected(
            fixtures.fixture('corruption-oracle', 0, 1 + 2**-48)[1], 0,
            {'p': [.25, .42, .27], 'd': [1., 0., 0.], 'steps': 5})
        rejected = []
        for corruption in ['owner', 'missing_gap', 'redistributed_flux', 'wrong_current', 'missing_contact']:
            bad = copy.deepcopy(row)
            if corruption == 'owner': bad['events'][0]['after'] = 108
            elif corruption == 'missing_gap': bad['events'].pop(1)
            elif corruption == 'redistributed_flux':
                amount = bad['events'][1]['scores'][0][0]
                assert amount > 0
                bad['events'][1]['scores'][0][1] += amount
                bad['events'][1]['scores'][0][0] = 0.
            elif corruption == 'wrong_current': bad['events'][0]['scores'][1] = [0.] * len(bad['scores'][1])
            else: bad['events'][0]['contacts'] = []
            try:
                fixtures.check(bad, wanted)
            except AssertionError:
                rejected.append(corruption)
        assert len(rejected) == 5
        retained()
        assert sha(options.cross_sections) == xs_identity
        assert all(sha(native_source / p) == h and sha(ROOT / p) == h for p, h in identities.items())
        total_bytes = size(NATIVE) + size(OUT) + (size(REUSED_ROOT) if REUSED_ROOT else 0)
        assert total_bytes < CAP
        save('receipt.json', {'status': 'PASS_PENDING_INDEPENDENT_REVIEW',
             'seconds': time.monotonic() - started, 'models': len(results),
             'rows': sum(len(x['rows']) for x in results), 'corruptions_rejected': rejected,
             'legacy_models': len(legacy), 'native_outputs': str(NATIVE),
             'output_bytes': total_bytes, 'lease': 'release after terminal children'})
    except BaseException as error:
        save('failure.json', {'status': 'FIRST_FAILURE_NO_RETRY', 'error': repr(error),
             'seconds': time.monotonic() - started, 'native_outputs': str(NATIVE)})
        raise
    finally:
        if json.loads(owner_file.read_text())['owner'] == token:
            owner_file.unlink()
            LOCK.rmdir()


if __name__ == '__main__':
    main()
