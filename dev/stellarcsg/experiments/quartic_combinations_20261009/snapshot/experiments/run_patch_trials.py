"""Append a bounded experiment with frozen inputs/source; never overwrite a run.

Run from the prototype directory:
  python experiments/run_patch_trials.py --run-id run-001
"""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import tracemalloc
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import scipy

from patch_methods import (
    HybridRadius, SplineRadius, SharedIndex, TorusPatch, fit_fourier_patch,
    fourier_jet, polynomial_design, polynomial_vector, profile_normal,
    query_diagnostic, real_quartic_candidates, surface_frame, synthetic_boundary,
    torus_polynomial,
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')


def atlas_study(nt, np_, amplitude):
    start = time.perf_counter()
    boundary = synthetic_boundary(amplitude)
    wt, wp = 2 * np.pi / nt, (2 * np.pi / 3) / np_
    patches, unsupported, errors, angles = {}, [], [], []
    for i in range(nt):
        for j in range(np_):
            tc, pc = (i + 0.5) * wt, (j + 0.5) * wp
            try:
                patch = fit_fourier_patch(boundary, tc, pc)
            except ValueError as e:
                unsupported.append({'theta_index': i, 'phi_index': j, 'reason': str(e)})
                continue
            jets = [fourier_jet(boundary, tc + dt, pc + dp)
                    for dt in np.linspace(-wt / 2, wt / 2, 5)
                    for dp in np.linspace(-wp / 2, wp / 2, 5)]
            points = np.array([v[0] for v in jets])
            normals = np.array([surface_frame(v)[1] for v in jets])
            patch.set_sampled_trims(points)
            _, fitted_normals, error = patch.project(points)
            errors.extend(np.abs(error))
            angles.extend(np.degrees(np.arccos(np.clip(np.sum(normals * fitted_normals, axis=1), -1, 1))))
            patches[i, j] = patch
    gaps = []
    for (i, j), patch in patches.items():
        neighbor = patches.get(((i + 1) % nt, j))
        if neighbor is not None:
            for dp in (-wp / 2, 0, wp / 2):
                p = fourier_jet(boundary, (i + 1) * wt, (j + 0.5) * wp + dp)[0]
                gaps.append(float(np.linalg.norm(patch.project(p)[0] - neighbor.project(p)[0])))
        neighbor = patches.get((i, (j + 1) % np_))
        if neighbor is not None:
            if j == np_ - 1:
                angle = 2 * np.pi / 3
                c, s = np.cos(angle), np.sin(angle)
                rot = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
                neighbor = TorusPatch(rot @ neighbor.center, rot @ neighbor.frame,
                                     neighbor.major, neighbor.minor, neighbor.beta_center)
            for dt in (-wt / 2, 0, wt / 2):
                p = fourier_jet(boundary, (i + 0.5) * wt + dt, (j + 1) * wp)[0]
                gaps.append(float(np.linalg.norm(patch.project(p)[0] - neighbor.project(p)[0])))
    return {'theta_patches': nt, 'phi_patches_one_field_period': np_,
            'amplitude_m': amplitude, 'supported_patches': len(patches),
            'unsupported_patches': unsupported,
            'sample_count': len(errors), 'sampled_max_surface_error_m': max(errors) if errors else None,
            'sampled_max_normal_error_deg': max(angles) if angles else None,
            'sampled_max_neighbor_seam_gap_m': max(gaps) if gaps else None,
            'construction_and_diagnostic_seconds': time.perf_counter() - start,
            'closed_volume': amplitude == 0 and not unsupported,
            'whole_domain_fit_certified': False,
            'verdict': 'EXACT_CONTROL_DISPATCH' if amplitude == 0 else 'APPROXIMATE_PATCHES_NOT_A_CLOSED_SOLID'}


def quartic_study(count):
    start = time.perf_counter()
    scale = 6.0
    rng = np.random.default_rng(7412)
    polynomials = [torus_polynomial(np.zeros(3), (0, 0, 1), 5 / scale, 0.8 / scale)]
    for _ in range(count - 1):
        center = rng.uniform(-0.6, 0.6, 3) / scale
        axis = np.r_[rng.uniform(-0.3, 0.3, 2), 1.0]
        major, minor = rng.uniform(4.6, 5.4) / scale, rng.uniform(0.6, 1.0) / scale
        polynomials.append(torus_polynomial(center, axis, major, minor))
    basis = np.column_stack([polynomial_vector(p) for p in polynomials])
    t, p = np.meshgrid(np.linspace(0, 2*np.pi, 18, endpoint=False),
                       np.linspace(0, 2*np.pi, 24, endpoint=False), indexing='ij')
    points = synthetic_boundary().position_cm(t, p).reshape(-1, 3) / (100 * scale)
    design = polynomial_design(points)
    differences = basis[:, 1:] - basis[:, :1]
    beta = np.linalg.lstsq(design @ differences, -(design @ basis[:, 0]), rcond=1e-11)[0]
    weights = np.r_[1 - np.sum(beta), beta]
    coefficients = basis @ weights
    # Sum(weights)=1 fixes the quartic leading term and excludes the trivial F=0 fit.
    tt, pp = np.meshgrid(np.linspace(0, 2*np.pi, 21, endpoint=False) + 0.023,
                         np.linspace(0, 2*np.pi, 29, endpoint=False) + 0.017, indexing='ij')
    holdout = synthetic_boundary().position_cm(tt, pp).reshape(-1, 3) / (100 * scale)
    residual = polynomial_design(holdout) @ coefficients
    rays = []
    for phi in np.linspace(0, 2*np.pi, 12, endpoint=False):
        d = np.array([np.cos(phi), np.sin(phi), 0.0])
        roots = real_quartic_candidates(coefficients, 0.1 * d / scale, d / scale, 10.0)
        target = 5 - (0.8 + 0.12 * np.cos(3 * phi)) - 0.1
        rays.append({'phi': float(phi), 'target_first_distance_m': float(target),
                     'quartic_candidates_m': roots,
                     'first_candidate_error_m': abs(roots[0] - target) if roots else None})
    errors = [r['first_candidate_error_m'] for r in rays if r['first_candidate_error_m'] is not None]
    return {'primitive_count': count, 'monomial_count': len(coefficients),
            'basis_rank': int(np.linalg.matrix_rank(basis, tol=1e-10)),
            'weight_sum': float(np.sum(weights)), 'maximum_absolute_weight': float(np.max(np.abs(weights))),
            'holdout_algebraic_rms_dimensionless': float(np.sqrt(np.mean(residual**2))),
            'sampled_radial_first_candidate_max_error_m': max(errors) if errors else None,
            'radial_missing_candidate_count': sum(not r['quartic_candidates_m'] for r in rays),
            'ray_controls': rays, 'construction_seconds': time.perf_counter() - start,
            'verdict': 'ONE_QUARTIC_COMPILES_BUT_GENERAL_FOURIER_FIDELITY_UNPROVED'}


def ray_bank():
    rng = np.random.default_rng(99831)
    rays = []
    for i in range(32):
        origin = rng.uniform(-7, 7, 3)
        target = synthetic_boundary().position_cm(rng.uniform(0, 2*np.pi), rng.uniform(0, 2*np.pi)) / 100
        d = target - origin
        d /= np.linalg.norm(d)
        rays.append({'id': f'general-{i:02}', 'origin_m': origin.tolist(), 'direction': d.tolist()})
    for i, phi in enumerate(np.linspace(0, 2*np.pi, 16, endpoint=False)):
        d = np.array([np.cos(phi), np.sin(phi), 0.0])
        rays.append({'id': f'radial-{i:02}', 'origin_m': (0.1*d).tolist(), 'direction': d.tolist()})
    rays.extend([{'id': 'miss-z', 'origin_m': [0, 0, 3], 'direction': [0, 0, 1]},
                 {'id': 'grazing', 'origin_m': [5.92, 0, -2], 'direction': [0, 0, 1]},
                 {'id': 'thin-chord', 'origin_m': [0.1, 0, 0.92 - 1e-8], 'direction': [1, 0, 0]},
                 {'id': 'coincident-control', 'origin_m': [5.92, 0, 0], 'direction': [1, 0, 0]}])
    return rays


def profile_study(count, fraction, rays):
    tracemalloc.start()
    start = time.perf_counter()
    profile = SplineRadius(count) if fraction is None else HybridRadius(count, fraction)
    index = SharedIndex(profile.patches())
    construction = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    phi = np.linspace(0, 2*np.pi, 4096, endpoint=False)
    a, da = profile.value_derivative(phi)
    target = 0.8 + 0.12 * np.cos(3 * phi)
    position_error = float(np.max(np.abs(a - target)))
    angle_errors = []
    for theta in (0, np.pi/4, np.pi/2, np.pi):
        for p in phi[::32]:
            r, dr = profile.value_derivative(p)
            target_normal = profile_normal(theta, p, 0.8 + 0.12*np.cos(3*p), -0.36*np.sin(3*p))
            fitted_normal = profile_normal(theta, p, float(r), float(dr))
            angle_errors.append(float(np.degrees(np.arccos(np.clip(target_normal @ fitted_normal, -1, 1)))))
    start = time.perf_counter()
    rows = []
    for ray in rays:
        result = query_diagnostic(profile, index, ray['origin_m'], ray['direction'])
        rows.append({'ray_id': ray['id'], **result})
    elapsed = time.perf_counter() - start
    sums = {k: sum(row['counters'][k] for row in rows) for k in rows[0]['counters']}
    radial_errors = []
    for ray, row in zip(rays, rows):
        if ray['id'].startswith('radial') and row['candidate_distance'] is not None:
            p = math_atan2(ray['direction'][1], ray['direction'][0])
            exact_for_approximation = 5 - float(profile.value_derivative(p)[0]) - 0.1
            radial_errors.append(abs(row['candidate_distance'] - exact_for_approximation))
    return {'method_id': 'FT-006' if fraction is None else 'FT-005',
            'node_count': count, 'transition_fraction': fraction,
            'patch_count': len(index.patches), 'sampled_max_surface_error_m': position_error,
            'sampled_max_normal_error_deg': max(angle_errors),
            'conservative_position_bound_m': None if fraction is None else profile.positional_error_bound(),
            'max_sampled_radius_slope': float(np.max(np.abs(da))),
            'construction_seconds': construction, 'peak_traced_construction_bytes': peak,
            'instrumented_query_seconds': elapsed, 'query_count': len(rows), 'work_counters': sums,
            'queries_with_spline_candidates': sum(r['counters']['spline_candidates'] > 0 for r in rows),
            'selected_spline_candidate_count': sum(r['candidate_kind'] == 'spline' for r in rows),
            'radial_max_candidate_error_m_for_represented_surface': max(radial_errors) if radial_errors else None,
            'rows': rows, 'native_transport_seconds': None,
            'verdict': 'CLOSED_SYNTHETIC_MODEL_WITH_UNCERTIFIED_QUERY_CANDIDATES'}


def math_atan2(y, x):
    return float(np.arctan2(y, x))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id.startswith('run-') or not args.run_id[4:].isdigit():
        raise ValueError('run-id must be run-NNN (digits only)')
    attempt = ROOT / 'attempts/0002-patch-hybrid-20261009'
    out = attempt / args.run_id
    out.mkdir(exist_ok=False)
    source = out / 'source'
    source.mkdir()
    paths = [ROOT/'fourier_torus.py', ROOT/'test_fourier_torus.py', HERE/'patch_methods.py',
             HERE/'test_patch_methods.py', Path(__file__)]
    source_hashes = {}
    for path in paths:
        target = source/path.name
        target.write_bytes(path.read_bytes())
        source_hashes[path.name] = digest(target)
    input_manifest = json.loads((attempt/'input_manifest.json').read_text())
    input_checks = {row['snapshot']: digest(attempt/row['snapshot']) == row['sha256']
                    for row in input_manifest['inputs']}
    prior_manifest = json.loads((ROOT/'attempts/0001-initial-20261009/manifest.json').read_text())
    old_checks = {row['file']: digest(ROOT/row['file']) == row['sha256']
                  for row in prior_manifest['files']}
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT), pattern='test_fourier_torus.py'))
    suite.addTests(unittest.defaultTestLoader.discover(str(HERE), pattern='test_patch_methods.py', top_level_dir=str(HERE)))
    log = io.StringIO()
    start = time.perf_counter()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    test_seconds = time.perf_counter() - start
    (out/'tests.txt').write_text(log.getvalue(), encoding='utf-8')
    if not result.wasSuccessful() or not all(input_checks.values()) or not all(old_checks.values()):
        save(out/'receipt.json', {'status':'FAIL', 'tests': log.getvalue(),
                                  'input_checks': input_checks, 'prior_checks': old_checks})
        raise SystemExit(1)
    rays = ray_bank()
    save(out/'rays.json', rays)
    atlas = [atlas_study(8, 12, 0.0), atlas_study(8, 12, 0.12), atlas_study(16, 24, 0.12)]
    save(out/'torus_patch_results.json', atlas)
    quartics = [quartic_study(k) for k in (8, 24, 64)]
    save(out/'compiled_quartic_results.json', quartics)
    profiles = []
    for count in (12, 24, 48):
        profiles.append(profile_study(count, None, rays))
        for fraction in (0.1, 0.3, 0.6):
            profiles.append(profile_study(count, fraction, rays))
    save(out/'hybrid_results.json', profiles)
    receipt = {'schema':'fourier-torus-patch-trial-v1', 'time_utc':datetime.now(timezone.utc).isoformat(),
               'status':'FUNCTIONAL_CONTROLS_PASS_RESEARCH_RESULTS_UNQUALIFIED',
               'run_id':args.run_id, 'source_parent_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
               'source_hashes':source_hashes, 'input_manifest_sha256':digest(attempt/'input_manifest.json'),
               'input_checks':input_checks, 'prior_attempt_files_unchanged':old_checks,
               'runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
               'controls':{'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'seconds':test_seconds},
               'query_bank_sha256':digest(out/'rays.json'), 'query_count':len(rays),
               'costs':{'software_acquisition_bytes':0,'native_build_seconds':None,'wout_loading_seconds':None,
                        'construction':'per-method result fields','memory':'Python tracemalloc construction peaks, excludes untracked native allocations',
                        'query':'instrumented candidate diagnostics, per-method seconds; not speed qualification',
                        'native_transport_seconds':None},
               'evidence_hashes':{p.name:digest(p) for p in out.iterdir() if p.is_file()},
               'claim_boundary':'synthetic amplitude-modulated tube; no WISTELL, whole-domain atlas fidelity, certified general first roots, OpenMC scoring, or speed gate'}
    save(out/'receipt.json', receipt)
    print(json.dumps({'output':str(out),'tests':result.testsRun,'atlas':[{k:r[k] for k in ('supported_patches','sampled_max_surface_error_m','sampled_max_neighbor_seam_gap_m')} for r in atlas],
                      'quartic_ranks':[r['basis_rank'] for r in quartics], 'profile_configs':len(profiles)},indent=2))


if __name__ == '__main__':
    main()
