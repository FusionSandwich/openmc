#!/usr/bin/env python3
"""Conservative finite-coil membership audit for the first WISTELL field period.

This is a compiler input manifest, not a transport-qualified periodic model.
"""
import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
from scipy.io import netcdf_file


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(vmec, filament, coils):
    with netcdf_file(vmec, 'r', mmap=False) as file:
        nfp = int(file.variables['nfp'].data.item())
    with filament.open() as stream:
        header = stream.readline().split()
    if header != ['periods', str(nfp)] or nfp != 4:
        raise ValueError('This axis-plane sector audit requires verified NFP=4 in both inputs')
    result = {'nfp': nfp, 'sector_degrees': [0, 90],
        'interior_halfspaces': ['x >= 0', 'y >= 0'],
        'sources': {str(p): digest(p) for p in (vmec, filament, coils)},
        'membership_method': 'For each periodic cubic B-spline span, retain its four-control convex hull enlarged by a bound on the section radius. Exclude only if its outward x or y upper bound is negative.',
        'status': 'CONSERVATIVE_INPUT_MANIFEST_ONLY',
        'precondition': 'Payload must be accepted by the swept compiler with a regular orthonormalizable frame; this membership audit does not validate that frame.',
        'members': [], 'excluded': []}
    centers = {}
    with h5py.File(coils) as file:
        for name, group in file['coils'].items():
            control = np.array(group['centerline_coefficients'])
            if control.ndim != 2 or control.shape[1] != 3 or not np.isfinite(control).all():
                raise ValueError('Invalid centerline controls')
            centers[name] = control
            axes = [np.array(group[key]) for key in ('major_radius_coefficients', 'minor_radius_coefficients')]
            if any(axis.shape != (len(control),) for axis in axes):
                raise ValueError('Radius arrays must match the centerline control count')
            radii = np.concatenate(axes)
            if not np.isfinite(radii).all() or np.min(radii) <= 0:
                raise ValueError('Invalid radius coefficients')
            # Positive B-spline weights bound section semiaxes by max control.
            radius = float(np.max(radii))
            n = len(control)
            support = control[(np.arange(n)[:, None] + np.array([-1, 0, 1, 2])) % n]
            upper = np.nextafter(support.max(axis=1) + radius, np.inf)
            lower = np.nextafter(support.min(axis=1) - radius, -np.inf)
            retained = np.flatnonzero((upper[:, 0] >= 0) & (upper[:, 1] >= 0))
            crossing0 = np.flatnonzero((lower[:, 1] <= 0) & (upper[:, 1] >= 0) & (upper[:, 0] >= 0))
            crossing90 = np.flatnonzero((lower[:, 0] <= 0) & (upper[:, 0] >= 0) & (upper[:, 1] >= 0))
            record = {'dataset': '/coils/' + name, 'coil_id': int(group.attrs['coil_id']),
                'radius_bound_cm': radius, 'retained_span_count': len(retained),
                'retained_spans': retained.tolist(), 'crosses_0_plane_candidate': bool(len(crossing0)),
                'crosses_90_plane_candidate': bool(len(crossing90))}
            result['members' if len(retained) else 'excluded'].append(record)
    pairs = []
    for name, control in centers.items():
        rotated = np.column_stack((-control[:, 1], control[:, 0], control[:, 2]))
        # This is an alignment diagnostic, not a symmetry certificate.
        same_shape = [(other, c) for other, c in centers.items() if c.shape == rotated.shape]
        target, error = min(((other, float(np.max(np.linalg.norm(c-rotated, axis=1))))
            for other, c in same_shape), key=lambda pair: pair[1])
        pairs.append({'source': name, 'rotation90_target': target, 'max_aligned_control_error_cm': error})
    result['rotation_diagnostic'] = pairs
    result['periodic_mapping_limit'] = ('Nonzero input symmetry discrepancies are not assumed to be rounding. '
        'A periodic transport model must declare whether to preserve each supplied coil or impose exact rotated copies, '
        'measure that representation change, and map member/material identities across the planes.')
    result['geometry_policy'] = ('Retain complete finite coil members listed here and intersect their material cells '
        'with the sector halfspaces. Boundary-crossing members include neighboring-period portions; do not truncate '
        'the coefficient curves or identify a period by the first 12 coil IDs. This conservative list can overinclude.')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--vmec', type=Path, required=True)
    p.add_argument('--filament', type=Path, required=True)
    p.add_argument('--coils', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = audit(a.vmec, a.filament, a.coils)
    with a.output.open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps({'nfp': result['nfp'], 'sector_degrees': result['sector_degrees'],
        'members': [m['dataset'] for m in result['members']],
        'status': result['status']}))
