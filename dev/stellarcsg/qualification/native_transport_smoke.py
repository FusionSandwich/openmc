"""Actual diagnostic transport, synthetic one-group absorption, no nuclear claim.

Run with an explicitly source-bound PYTHONPATH and executable. Every invocation
creates a new output directory and retains attempted transport before validation.
The parent coil cell provides an independent sum-versus-union tracklength tally.
"""
import argparse
import hashlib
import importlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import time

import numpy as np
import openmc
from scipy.spatial.transform import Rotation

from stellarcsg.coil import SweptSplineData, write_swept_collection
from stellarcsg.io import write_surface
from stellarcsg.surface import PeriodicRadialSurfaceData


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--case', choices=['torus', 'plasma', 'coil', 'two-coils', 'combined'], required=True)
    parser.add_argument('--histories', type=int, default=10000)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--timeout', type=float, default=180.)
    parser.add_argument('--shared', action='store_true')
    parser.add_argument('--distributed', action='store_true',
                        help='Freeze at least 10000 distinct spatial/angular source definitions')
    args = parser.parse_args()
    root = args.source_root.resolve()
    assert Path(openmc.__file__).resolve() == root / 'openmc/__init__.py'
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    executable = args.executable.resolve()
    expected_library = executable.parent.parent / 'lib/libopenmc.so'
    assert executable.is_file() and expected_library.is_file(), 'Declared native build is incomplete'
    execution_environment = {**os.environ, 'LD_LIBRARY_PATH': str(expected_library.parent)
        + (':' + os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else '')}
    linkage = subprocess.run(['/usr/bin/ldd', str(executable)],
        env=execution_environment, text=True, capture_output=True, timeout=20)
    (out / 'executable-ldd.log').write_text(linkage.stdout + linkage.stderr)
    assert linkage.returncode == 0 and 'not found' not in linkage.stdout
    assert 'libopenmc.so => '+str(expected_library)+' ' in linkage.stdout, 'Unbound native library'
    binary_before = dict(executable=digest(executable), library=digest(expected_library))
    assert args.histories >= 10 and args.histories % 10 == 0
    openmc.reset_auto_ids()
    n_coils = {'torus': 0, 'plasma': 0, 'coil': 1, 'two-coils': 2, 'combined': 2}[args.case]
    has_plasma = args.case in ('torus', 'plasma', 'combined')
    theta = np.arange(64) * (2 * np.pi / 64)
    points = np.column_stack((3*np.cos(theta), 3*np.sin(theta), .3*np.sin(2*theta)))
    coils = []
    for index in range(n_coils):
        coil = SweptSplineData.from_centerline(
            index + 1, points, major_radius_cm=.25, minor_radius_cm=.25,
            sample_count=64, source_metadata={'kind': 'synthetic circular transport verification'})
        coils.append(coil.rigid_transform(
            Rotation.from_rotvec([.15, -.1, .2] if index == 0 else [-.2, .15, -.1]).as_matrix(),
            [20. if index == 0 else -20., 0., 0.]))
    coil_file = out / 'coils.h5'
    if coils:
        write_swept_collection(coil_file, coils)
    surfaces = []
    for coil in coils:
        kwargs = dict(surface_id=500 + coil.coil_id)
        if args.shared:
            kwargs.update(dataset_prefix='/coils/coil_', dataset_start=1,
                          dataset_count=n_coils, member_id=coil.coil_id)
        else:
            kwargs.update(dataset=f'/coils/coil_{coil.coil_id:03d}', content_id=coil.content_id)
        surfaces.append(openmc.SweptSplineSurface(coil_file, **kwargs))
    plasma = None
    if has_plasma:
        if args.case == 'torus':
            plasma = openmc.ZTorus(a=10., b=2., c=2., surface_id=510)
        else:
            data = PeriodicRadialSurfaceData.analytic_torus(
                name='helical', major_radius_cm=10., minor_radius_cm=2.,
                n_field_periods=2, helical_amplitude_cm=.2, n_theta=24, n_phi=24)
            write_surface(out / 'plasma.h5', data)
            plasma = openmc.PeriodicSplineSurface(out / 'plasma.h5', '/surfaces/helical',
                                                 data.content_id, surface_id=510)
    boxes = [s.bounding_box('-') for s in surfaces]
    if plasma is not None:
        boxes.append(plasma.bounding_box('-'))
    gaps = [float(np.max(np.maximum(a.lower_left-b.upper_right, b.lower_left-a.upper_right)))
            for i, a in enumerate(boxes) for b in boxes[i+1:]]
    assert all(gap > 0. for gap in gaps), gaps
    groups = openmc.mgxs.EnergyGroups(group_edges=[0., 20.e6])
    library = openmc.MGXSLibrary(groups)
    xs = openmc.XSdata('synthetic_absorber', groups)
    xs.order = 0
    xs.set_total(np.array([.1]))
    xs.set_absorption(np.array([.1]))
    xs.set_scatter_matrix(np.zeros((1, 1, 1)))
    library.add_xsdata(xs)
    library.export_to_hdf5(out / 'synthetic_mg.h5')
    materials = openmc.Materials()
    for index in range(n_coils + int(has_plasma)):
        material = openmc.Material(material_id=11+index, name=f'diagnostic identity {index}')
        material.set_density('macro', 1.)
        material.add_macroscopic('synthetic_absorber')
        materials.append(material)
    materials.cross_sections = str(out / 'synthetic_mg.h5')
    boundary = openmc.Sphere(r=50., boundary_type='vacuum', surface_id=599)
    remaining = -boundary
    cells = []
    coil_cells = [openmc.Cell(cell_id=101+i, fill=materials[i], region=-s)
                  for i, s in enumerate(surfaces)]
    if coil_cells:
        union_region = -surfaces[0]
        for s in surfaces[1:]:
            union_region |= -s
        cells.append(openmc.Cell(cell_id=201, name='coil union parent', region=union_region,
                                 fill=openmc.Universe(universe_id=20, cells=coil_cells)))
        remaining &= ~union_region
    if plasma is not None:
        cells.append(openmc.Cell(cell_id=103, fill=materials[-1], region=-plasma))
        remaining &= +plasma
    cells.append(openmc.Cell(cell_id=202, name='void', region=remaining))
    sources = []
    for i, coil in enumerate(coils):
        center, _, normal, _ = coil.frame(0.)
        sources.append(openmc.IndependentSource(
            space=openmc.stats.Point(center+1.25*normal),
            angle=openmc.stats.Monodirectional(-normal),
            energy=openmc.stats.Discrete([14.e6], [1.]), strength=3. if i == 0 else 1.))
    if has_plasma:
        sources.append(openmc.IndependentSource(space=openmc.stats.Point((10., 0., 0.)),
            angle=openmc.stats.Monodirectional((1., 0., 0.)),
            energy=openmc.stats.Discrete([14.e6], [1.]), strength=1.))
    settings = openmc.Settings()
    settings.run_mode = 'fixed source'
    settings.energy_mode = 'multi-group'
    settings.particles = args.histories // 10
    settings.batches = 10
    settings.seed = 713
    settings.source = sources
    # Freeze an explicit physical source bank shared by separate/shared paths.
    rng = np.random.default_rng(713)
    strengths = np.array([source.strength for source in sources])
    bank_count = max(10000, args.histories) if args.distributed else args.histories
    choices = rng.choice(len(sources), bank_count, p=strengths/strengths.sum())
    if args.distributed:
        positions = np.empty((bank_count, 3))
        directions = np.empty((bank_count, 3))
        for i, coil in enumerate(coils):
            mask = choices == i
            count = int(np.count_nonzero(mask))
            center, tangent, normal, binormal = coil.frame(rng.uniform(0., coil.length_cm, count))
            angle = rng.uniform(0., 2*np.pi, count)
            radial = np.cos(angle)[:, None]*normal + np.sin(angle)[:, None]*binormal
            positions[mask] = center + rng.uniform(.75, 1.25, count)[:, None]*radial
            direction = -radial + rng.uniform(-.02, .02, count)[:, None]*tangent
            directions[mask] = direction/np.linalg.norm(direction, axis=1)[:, None]
        if has_plasma:
            mask = choices == n_coils
            count = int(np.count_nonzero(mask))
            angle = rng.uniform(0., 2*np.pi, count)
            positions[mask] = np.column_stack((10*np.cos(angle), 10*np.sin(angle), np.zeros(count)))
            direction = rng.normal(size=(count, 3))
            directions[mask] = direction/np.linalg.norm(direction, axis=1)[:, None]
        assert np.unique(np.column_stack((positions, directions)), axis=0).shape[0] == bank_count
        bank = [openmc.SourceParticle(r=r, u=u, E=14.e6) for r, u in zip(positions, directions)]
    else:
        bank = [openmc.SourceParticle(r=sources[i].space.xyz,
                 u=sources[i].angle.reference_uvw, E=14.e6) for i in choices]
    openmc.write_source_file(bank, out / 'source_bank.h5')
    settings.source = openmc.FileSource(out / 'source_bank.h5')
    settings.max_lost_particles = 1
    settings.rel_max_lost_particles = 1.e-12
    settings.track = [(1, 1, i) for i in range(1, min(101, settings.particles+1))]
    settings.output = {'summary': True, 'tallies': True}
    tallies = openmc.Tallies()
    if coils:
        for tid, name, filt in [(1, 'per coil', openmc.CellFilter(coil_cells)),
                                (2, 'union', openmc.CellFilter([201])),
                                (3, 'per material', openmc.MaterialFilter(materials[:n_coils]))]:
            tally = openmc.Tally(tally_id=tid, name=name)
            tally.filters = [filt]
            tally.scores = ['flux']
            tally.estimator = 'tracklength'
            tallies.append(tally)
    model = openmc.Model(openmc.Geometry(cells), materials, settings, tallies)
    model.export_to_xml(out)
    (out / 'attempt-start.json').write_text(json.dumps(dict(
        source_sha=args.source_sha, case=args.case, histories=args.histories,
        distributed=args.distributed, source_bank_particles=bank_count,
        shared=args.shared, threads=args.threads, executable=str(executable),
        executable_sha256=binary_before['executable'], library=str(expected_library),
        library_sha256=binary_before['library'], timeout_seconds=args.timeout,
        executable_linkage_sha256=digest(out / 'executable-ldd.log'),
        source_bank_sha256=digest(out / 'source_bank.h5')), indent=2)+'\n')
    assert binary_before == dict(executable=digest(executable), library=digest(expected_library)), \
        'Native build changed during model preparation'
    start = time.perf_counter()
    with (out / 'transport.log').open('x') as log:
        try:
            result = subprocess.run([str(executable), '-s', str(args.threads)], cwd=out, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=args.timeout,
                                    env={**execution_environment, **({'STELLARCSG_REPORT_SHARED': '1'}
                                         if args.shared else {})})
        except subprocess.TimeoutExpired:
            (out / 'attempt-timeout.json').write_text(json.dumps(dict(
                state='BLOCKED', timeout_seconds=args.timeout,
                completed_histories=None, lost_particles=None))+'\n')
            raise
    elapsed = time.perf_counter()-start
    binary_after = dict(executable=digest(executable), library=digest(expected_library))
    receipt = dict(case=args.case, diagnostic=True, qualification='NOT_RUN',
                   distributed=args.distributed, source_bank_particles=bank_count,
                   source_population='uniform coil arc/section angle and source offset, small directional tilt; '
                       'plasma ring with isotropic directions' if args.distributed else 'repeated point/direction definitions',
                   source_sha=args.source_sha, source_root=str(root), shared=args.shared,
                   executable_sha256=binary_before['executable'], library=str(expected_library),
                   library_sha256=binary_before['library'],
                   binary_hashes_before=binary_before, binary_hashes_after=binary_after,
                   binary_preserved=binary_before == binary_after, returncode=result.returncode,
                   executable_linkage_sha256=digest(out / 'executable-ldd.log'),
                   threads=args.threads, source_bank_sha256=digest(out / 'source_bank.h5'),
                   wall_seconds=elapsed, requested_histories=args.histories,
                   box_gaps_cm=gaps, physics='synthetic one-group pure absorber, not nuclear validation')
    (out / 'attempt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    assert receipt['binary_preserved'], 'Native executable or library changed during transport'
    assert result.returncode == 0, 'Transport failed; retained transport.log'
    log = (out / 'transport.log').read_text()
    assert 'lost particle' not in log.lower(), 'Lost-particle diagnostic retained'
    with openmc.StatePoint(out / 'statepoint.10.h5') as sp:
        receipt['completed_histories'] = int(sp.n_particles * sp.n_batches)
        receipt['runtime'] = sp.runtime
        assert receipt['completed_histories'] == args.histories
        if coils:
            scores = sp.get_tally(id=1).mean.ravel()
            union = float(sp.get_tally(id=2).mean.ravel()[0])
            material_scores = sp.get_tally(id=3).mean.ravel()
            assert np.all(scores > 0.)
            assert np.allclose(scores, material_scores, rtol=1.e-12, atol=1.e-14)
            assert np.isclose(np.sum(scores), union, rtol=1.e-12, atol=1.e-14)
            if n_coils == 2:
                assert scores[0] > 2* scores[1], 'Asymmetric attribution expectation'
            receipt.update(coil_flux=scores.tolist(), material_flux=material_scores.tolist(),
                           union_flux=union, closure_error=float(np.sum(scores)-union))
    tracks = openmc.Tracks(out / 'tracks.h5')
    pairs = set()
    transitions = 0
    for track in tracks:
        for particle in track:
            states = particle.states
            pairs.update((int(s['cell_id']), int(s['material_id'])) for s in states)
            transitions += int(np.count_nonzero(states['cell_id'][1:] != states['cell_id'][:-1]))
    for i in range(n_coils):
        assert (101+i, 11+i) in pairs
        assert all(material == 11+i for cell, material in pairs if cell == 101+i)
    receipt.update(state='PASS', lost_particles=0,
                   lostcount_evidence='Inferred from successful process, requested histories in statepoint, '
                       'and absence of lost-particle log diagnostics; not an independent lost-particle counter.',
                   track_evidence='Only the requested first-batch sample is retained; observed identity and '
                       'transitions do not establish nearest-root or crossing completeness.',
                   retained_tracks=len(tracks),
                   retained_cell_transitions=transitions, cell_material_pairs=sorted(pairs))
    # Fresh output directory: lib.init must not overwrite the transport summary.
    if coils and (root / 'openmc/lib/libopenmc.so').is_file():
        importlib.import_module('openmc.lib')
        assert digest(openmc.lib._filename) == digest(expected_library)
        probe = out / 'cell-probe'
        probe.mkdir()
        for name in ('geometry.xml', 'materials.xml', 'settings.xml', 'tallies.xml'):
            if (out / name).exists():
                shutil.copyfile(out / name, probe / name)
        previous = Path.cwd()
        checks = []
        try:
            os.chdir(probe)
            openmc.lib.init(output=False)
            try:
                for i, coil in enumerate(coils):
                    center, _, normal, _ = coil.frame(0.)
                    for distance, expected in [(0., 101+i), (.25-1.e-6, 101+i),
                                               (.25+1.e-6, 202)]:
                        point = center+distance*normal
                        cell, _ = openmc.lib.find_cell(point)
                        material = openmc.lib.find_material(point)
                        mid = None if material is None else material.id
                        assert cell.id == expected
                        assert mid == (11+i if expected == 101+i else None)
                        checks.append(dict(point=point.tolist(), cell=cell.id, material=mid))
            finally:
                openmc.lib.finalize()
        finally:
            os.chdir(previous)
        receipt['deterministic_cell_checks'] = checks
        receipt['library_sha256'] = digest(expected_library)
    receipt['files'] = {p.name: digest(p) for p in out.iterdir() if p.is_file()}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
