"""Exact, finite tally fixtures -- not Monte Carlo transport or a coil solver.

Axis-aligned unit-box interiors and rational axial track segments have closed
form lengths. The independently merged union ledger must close per history,
not just statistically after averaging. Boundary ownership is bookkeeping
only; zero-measure contact must not erase a genuine material overlap.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction as Q
import json
from pathlib import Path

import h5py
import pytest


@dataclass(frozen=True)
class Member:
    member_id: int
    surface_id: int
    cell_id: int
    material_id: int
    lo: tuple[Q, Q, Q]
    hi: tuple[Q, Q, Q]


MEMBERS = (
    Member(7, 301, 201, 101, (Q(0), Q(0), Q(0)), (Q(1), Q(1), Q(1))),
    Member(42, 302, 202, 102, (Q(2), Q(0), Q(0)), (Q(3), Q(1), Q(1))),
)
# Exactly specified finite diagnostic source, not a sampled correctness oracle.
# (start_x, end_x, y, z, statistical_weight), direction always +x.
TRACKS = (
    (Q(-1), Q(4), Q(1, 2), Q(1, 2), Q(1)),
    (Q(1, 2), Q(4), Q(1, 2), Q(1, 2), Q(2)),
    (Q(-1), Q(5, 2), Q(1, 4), Q(3, 4), Q(1, 2)),
    (Q(-1), Q(4), Q(2), Q(1, 2), Q(3)),
)


def admit(members):
    if not members:
        raise ValueError('empty finite member set')
    for field in ('member_id', 'surface_id', 'cell_id'):
        values = [getattr(m, field) for m in members]
        minimum = 0 if field == 'member_id' else 1
        if any(type(v) is not int or v < minimum for v in values):
            raise ValueError(f'invalid {field}')
        if len(values) != len(set(values)):
            raise ValueError(f'duplicate {field}')
    for m in members:
        if type(m.material_id) is not int or m.material_id <= 0:
            raise ValueError('invalid material association')
        if any(a >= b for a, b in zip(m.lo, m.hi)):
            raise ValueError('empty or inverted member')
    for index, a in enumerate(members):
        for b in members[index+1:]:
            if all(max(al, bl) < min(ah, bh)
                   for al, ah, bl, bh in zip(a.lo, a.hi, b.lo, b.hi)):
                raise ValueError('true positive-volume material overlap')


def boundary_owner(members, point):
    admit(members)
    candidates = [m.member_id for m in members
                  if all(a <= p <= b for a, p, b in zip(m.lo, point, m.hi))
                  and any(p in (a, b) for a, p, b in zip(m.lo, point, m.hi))]
    return min(candidates) if candidates else None


def intervals(members, track):
    x0, x1, y, z, _ = track
    if x1 <= x0:
        raise ValueError('fixture requires a forward finite axial segment')
    return [(m.member_id, max(x0, m.lo[0]), min(x1, m.hi[0])) for m in members
            if m.lo[1] < y < m.hi[1] and m.lo[2] < z < m.hi[2]
            and max(x0, m.lo[0]) < min(x1, m.hi[0])]


def union_length(parts):
    """Independent interval-union measure; includes overlap exactly once."""
    merged = []
    for _, lo, hi in sorted(parts, key=lambda part: part[1]):
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return sum((hi-lo for lo, hi in merged), Q(0))


def ledger(members, tracks):
    admit(members)
    by_member = {m.member_id: Q(0) for m in members}
    union = Q(0)
    for track in tracks:
        parts = intervals(members, track)
        weight = track[-1]
        per_history = sum((weight*(hi-lo) for _, lo, hi in parts), Q(0))
        union_history = weight * union_length(parts)
        assert per_history == union_history  # Exact event-level closure.
        union += union_history
        for member_id, lo, hi in parts:
            by_member[member_id] += weight*(hi-lo)
    by_material = {}
    for m in members:
        by_material[m.material_id] = by_material.get(m.material_id, Q(0)) + by_member[m.member_id]
    return by_member, by_material, union


def test_exact_weighted_distributed_source_closure():
    by_member, by_material, union = ledger(MEMBERS, TRACKS)
    assert by_member == {7: Q(5, 2), 42: Q(13, 4)}
    assert by_material == {101: Q(5, 2), 102: Q(13, 4)}
    assert union == Q(23, 4)


def test_permutation_preserves_ids_materials_and_closure():
    assert ledger(tuple(reversed(MEMBERS)), TRACKS) == ledger(MEMBERS, TRACKS)


def test_same_material_does_not_erase_member_bins():
    members = (MEMBERS[0], replace(MEMBERS[1], material_id=101))
    by_member, by_material, union = ledger(members, TRACKS)
    assert len(by_member) == 2 and by_material == {101: union}


def test_touching_boundary_is_not_material_overlap():
    members = (MEMBERS[0], replace(MEMBERS[1], lo=(Q(1), Q(0), Q(0)),
                                                   hi=(Q(2), Q(1), Q(1))))
    admit(members)
    point = (Q(1), Q(1, 2), Q(1, 2))
    assert boundary_owner(members, point) == 7
    assert boundary_owner(tuple(reversed(members)), point) == 7
    assert ledger(members, TRACKS)[2] == sum(ledger(members, TRACKS)[0].values())


def test_zero_measure_boundary_has_no_tracklength_double_count():
    assert union_length([(7, Q(0), Q(1)), (42, Q(1), Q(2))]) == Q(2)


def test_true_overlap_rejected_not_relabelled_coincident():
    overlap = replace(MEMBERS[1], lo=(Q(1, 2), Q(0), Q(0)), hi=(Q(3, 2), Q(1), Q(1)))
    with pytest.raises(ValueError, match='positive-volume'):
        admit((MEMBERS[0], overlap))
    # Independent negative control: naïve per-member sum would be 2, union 3/2.
    assert union_length([(7, Q(0), Q(1)), (42, Q(1, 2), Q(3, 2))]) == Q(3, 2)


@pytest.mark.parametrize('field', ['member_id', 'surface_id', 'cell_id'])
def test_duplicate_ids_rejected(field):
    with pytest.raises(ValueError, match='duplicate'):
        admit((MEMBERS[0], replace(MEMBERS[1], **{field: getattr(MEMBERS[0], field)})))


@pytest.mark.parametrize('bad', [float('inf'), float('nan'), True, -1])
def test_nonfinite_or_unsupported_member_identity_rejected(bad):
    with pytest.raises(ValueError, match='invalid member_id'):
        admit((replace(MEMBERS[0], member_id=bad),))


def test_rigid_axis_rotation_and_translation_preserve_ownership():
    # Exact +90-degree rotation about z, then translation (5, 7, 11).
    def transform(m):
        return replace(m, lo=(Q(5)-m.hi[1], Q(7)+m.lo[0], Q(11)+m.lo[2]),
                       hi=(Q(5)-m.lo[1], Q(7)+m.hi[0], Q(11)+m.hi[2]))
    transformed = tuple(map(transform, MEMBERS))
    admit(transformed)
    assert boundary_owner(transformed, (Q(9, 2), Q(7), Q(23, 2))) == 7
    assert [(m.member_id, m.material_id) for m in transformed] == [(7, 101), (42, 102)]


def test_manifest_real_hdf5_roundtrip(tmp_path):
    filename = tmp_path/'members.h5'
    with h5py.File(filename, 'w') as h5:
        for m in MEMBERS:
            group = h5.create_group(f'members/{m.member_id}')
            for field in ('member_id', 'surface_id', 'cell_id', 'material_id'):
                group.attrs[field] = getattr(m, field)
            group['lo_rational'] = [str(q).encode() for q in m.lo]
            group['hi_rational'] = [str(q).encode() for q in m.hi]
    with h5py.File(filename) as h5:
        recovered = tuple(Member(*(int(group.attrs[k]) for k in
                          ('member_id', 'surface_id', 'cell_id', 'material_id')),
                          tuple(Q(v.decode()) for v in group['lo_rational'][...]),
                          tuple(Q(v.decode()) for v in group['hi_rational'][...]))
                          for group in h5['members'].values())
    assert ledger(recovered, TRACKS) == ledger(MEMBERS, TRACKS)


def test_finite_fixture_manifest_hashable():
    payload = {'members': [dict(member_id=m.member_id, cell_id=m.cell_id,
                               surface_id=m.surface_id, material_id=m.material_id,
                               lower=list(map(str, m.lo)), upper=list(map(str, m.hi)))
                           for m in MEMBERS],
               'tracks': [list(map(str, track)) for track in TRACKS],
               'expected_weighted_length_cm': '23/4',
               'transport_result': False}
    assert json.loads(json.dumps(payload)) == payload
