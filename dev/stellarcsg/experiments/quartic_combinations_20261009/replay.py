"""Replay frozen controls and counterexamples; do not rerun owner campaigns."""
from datetime import datetime, timezone
import ast
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import unittest

import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / 'snapshot'
ATTEMPT = SNAPSHOT / 'attempts/0003-direct-fourier-algebraic-20261009'
ORIGINAL = ATTEMPT / 'run-002/source'
sys.path[:0] = [str(HERE), str(ORIGINAL),
               str(HERE.parent / 'query_combinations_20261009')]
import direct_algebraic
# Retained source is relocated; bind its frozen input dependency explicitly.
direct_algebraic.INPUTS = ATTEMPT / 'inputs'
from direct_algebraic import DirectFourier, LocalQuartic, field_jet, query_candidates
from quartic_oracle import isolate


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    manifest = read(HERE / 'snapshot_manifest.json')
    hashes_ok = all(hashlib.sha256((HERE / row['snapshot']).read_bytes()).hexdigest()
                    == row['sha256'] for row in manifest['files'])
    if not hashes_ok:
        raise ValueError('Snapshot hash mismatch')
    source_receipt = read(ATTEMPT / 'run-002/receipt.json')
    mapping = {'fourier_torus.py': SNAPSHOT / 'fourier_torus.py',
               'test_fourier_torus.py': SNAPSHOT / 'test_fourier_torus.py'}
    source_binding = all(hashlib.sha256((ORIGINAL/name).read_bytes()).hexdigest() == digest
                         for name, digest in source_receipt['source_hashes'].items())
    if not source_binding:
        raise ValueError('Retained run source does not match frozen code')
    formatting_binding = {name: ast.dump(ast.parse((ORIGINAL/name).read_text(encoding='utf-8')))
                          == ast.dump(ast.parse(mapping.get(name, SNAPSHOT/'experiments'/name)
                                                .read_text(encoding='utf-8')))
                          for name in source_receipt['source_hashes']}
    output_binding = all(hashlib.sha256((ATTEMPT/'run-002'/name).read_bytes()).hexdigest()
                         == digest for name, digest in source_receipt['output_hashes'].items())
    if not all(formatting_binding.values()) or not output_binding:
        raise ValueError('Changed executable AST or retained output hash')
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_fourier_torus', 'test_patch_methods', 'test_direct_algebraic',
        'test_quartic_oracle', 'test_candidate_scheduler'])
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (HERE / 'replay_tests.txt').write_text(log.getvalue(), encoding='utf-8')
    if not tests.wasSuccessful():
        print(log.getvalue())
        raise RuntimeError('Controls failed')
    print(f'{tests.testsRun} controls passed', flush=True)

    negatives = read(ATTEMPT / 'independent_counterexamples.json')['counterexamples']
    high = negatives[0]
    target = DirectFourier()
    target.m = np.array(high['m'])
    target.n = np.array(high['stored_n'])
    target.c = np.array(high['cos_coefficients_m'])
    target.s = np.array(high['sin_coefficients_m'])
    result = query_candidates(target, high['origin_m'], high['direction'],
                              ceiling=high['ceiling_m'], samples=high['samples'])
    o, d = np.array(high['origin_m']), np.array(high['direction'])
    values = [float(field_jet(target, o + t*d)[0])
              for t in high['reference_bracket_m']]
    separation = min(abs(t - high['isolated_crossing_m'])
                     for t in result['candidates_m'])
    assert values[0] * values[1] < 0 and separation > 0.003
    assert result['disposition'] == 'UNRESOLVED'
    singular = negatives[1]
    singular_result = query_candidates(
        DirectFourier(circular=True), singular['origin_m'], singular['direction'],
        ceiling=singular['ceiling_m'], samples=singular['samples'])
    assert singular_result['disposition'] == 'UNRESOLVED'
    assert not singular_result['candidates_m'] and singular_result['unsupported']

    extra = read(ATTEMPT / 'quartic_counterexample.json')
    atlas = read(ATTEMPT / 'run-002/local_quartic_results.json')[0]
    record = atlas['patch_records'][0]
    wt, wp = 2*np.pi/atlas['theta_patches'], 2*np.pi/(3*atlas['phi_patches_one_period'])
    patch = LocalQuartic(np.array(record['center_m']), np.array(record['frame']),
                         record['scale_m'], np.array(record['coefficients']),
                         record['rank'], record['condition'], wt/2, wp/2, wt/2, wp/2)
    o, d = np.array(extra['origin_m']), np.array(extra['direction'])
    candidates = patch.trimmed_ray_candidates(o, d, ceiling=extra['ceiling_m'])
    coefficients = patch.ray_polynomial(o, d).tolist()
    isolated = isolate(coefficients, 0, extra['ceiling_m'])
    assert isolated.disposition == 'COMPLETE'
    numerical_root = candidates['candidates_m'][0]
    # Numerical roots are not exact; match to the nearby exact coefficient root.
    closest = min(isolated.roots,
                  key=lambda r: abs(float((r.lower+r.upper)/2) - numerical_root))
    exact_midpoint = float((closest.lower + closest.upper)/2)
    target_field = float(field_jet(DirectFourier(), o + exact_midpoint*d)[0])
    assert abs(exact_midpoint - numerical_root) < 1e-8 and target_field > 0.78
    assert candidates['disposition'] == 'UNRESOLVED'
    print('Three retained counterexamples reproduced', flush=True)
    receipt = dict(
        created_utc=datetime.now(timezone.utc).isoformat(), status='PASS_SCOPED_REFERENCE',
        source_commit=manifest['source_commit'], snapshot_files=len(manifest['files']),
        snapshot_hashes_valid=hashes_ok, retained_run_source_binding=source_binding,
        formatted_source_ast_equivalent=formatting_binding, retained_output_hashes_valid=output_binding,
        runtime=dict(executable=sys.executable, python=platform.python_version(),
                     numpy=np.__version__, scipy=scipy.__version__),
        tests=dict(run=tests.testsRun, failures=len(tests.failures), errors=len(tests.errors)),
        counterexamples=[dict(id=high['id'], reproduced=True,
                             bracket_field_m=values, missed_crossing_separation_m=separation,
                             candidate_count=len(result['candidates_m']), disposition='UNRESOLVED'),
                        dict(id=singular['id'], reproduced=True, **singular_result),
                        dict(id=extra['id'], reproduced=True,
                             exact_polynomial_root_count=len(isolated.roots),
                             matched_root_interval=[str(closest.lower), str(closest.upper)],
                             target_field_at_interval_midpoint_m=target_field,
                             disposition='UNRESOLVED')],
        new_source_sha256={name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                           for name in ['quartic_oracle.py', 'test_quartic_oracle.py', 'replay.py']},
        native_build=False, transport=False, real_vmec=False,
        physical_fidelity_acceptance=False, native_speed_acceptance=False)
    (HERE / 'replay_results.json').write_text(json.dumps(receipt, indent=2,
                                                        allow_nan=False)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
