"""Independent exact rational member-2 inside-prefix and next-exit proof."""
from __future__ import annotations
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import resource
import time

resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
import h5py
from exact_offset_seam_reference import EXPECTED_HASH, bezier, split, encode


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument('--h5', type=Path, required=True)
    parser.add_argument('--entry-probe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must be new')
    if sha(args.h5) != EXPECTED_HASH:
        raise ValueError('Analytic H5 identity differs')
    rows = [json.loads(line) for line in args.entry_probe.read_text().splitlines() if line.strip()]
    entries = [r for r in rows if r.get('kind') == 'native_surface']
    if (len(entries) != 1 or entries[0].get('state') != 'PASS'
            or type(entries[0].get('distance_cm')) not in (float, int)
            or not math.isfinite(entries[0]['distance_cm'])):
        raise ValueError('One finite native entry observation required')
    # The native Region probe constructs its new origin with binary64 subtraction.
    origin_x = F.from_float(550.0 - float(entries[0]['distance_cm']))
    with h5py.File(args.h5) as handle:
        group = handle['coils/coil_002']
        points = [[F.from_float(float(v)) for v in row]
                  for row in group['centerline_coefficients'][:]]
        normals = group['normal_coefficients'][:]
        major = group['major_radius_coefficients'][:]
        minor = group['minor_radius_coefficients'][:]
    if not (len(points) == 256 and all(p[2] == 0 for p in points)
            and all(n[0] == n[1] == 0 and n[2] > 0 for n in normals)
            and all(v == 24 for v in major) and all(v == 14 for v in minor)):
        raise ValueError('Required constant planar ellipse geometry differs')
    spans = [tuple(bezier([p[a] for p in points], s) for a in range(3))
             for s in range(len(points))]
    witness = tuple(spans[0][a][0] for a in range(3))
    epsilon = F(1, 10**12)
    inside_x, outside_x = F(506)+epsilon, F(506)-epsilon
    left, right = origin_x-inside_x, origin_x-outside_x

    def q(point, center):
        return sum((point[a]-center[a])**2 / (F(24) if a == 2 else F(14))**2
                   for a in range(3))

    inside_endpoint_q = [q((x,F(0),F(0)), witness) for x in (origin_x, inside_x)]
    if not (0 < left < right and max(inside_endpoint_q) < 1):
        raise ValueError('Single exact seam-center ball does not cover entire inside prefix')
    nodes, leaves, max_depth, minimum_margin = 0, 0, 0, None
    point = (outside_x,F(0),F(0))
    for span in spans:
        shifted = [[(point[a]-v)/(F(24) if a == 2 else F(14)) for v in span[a]]
                   for a in range(3)]
        controls = tuple(sum(shifted[a][i]*shifted[a][j]
                             * F(math.comb(3,i)*math.comb(3,j),math.comb(6,k))
                             for a in range(3) for i in range(4) for j in range(4)
                             if i+j == k)-1 for k in range(7))
        todo = [(controls,0)]
        while todo:
            controls, depth = todo.pop()
            nodes += 1
            if nodes > 100000 or depth > 100 or time.monotonic()-started > 30:
                raise RuntimeError('Exact reference proof budget exhausted')
            margin = min(controls)
            if margin > 0:
                leaves += 1
                max_depth = max(max_depth, depth)
                minimum_margin = margin if minimum_margin is None else min(minimum_margin, margin)
                continue
            if max(controls) <= 0:
                raise ValueError('Outside endpoint is not globally outside')
            a,b = split(controls)
            todo.extend(((a,depth+1),(b,depth+1)))
    report = {
        'schema':'stellarcsg.independent-native-region-exit/v1',
        'state':'FIRST_EXIT_AFTER_NATIVE_ENTRY_CERTIFIED_EXACT_RATIONAL',
        'h5_sha256':sha(args.h5), 'entry_probe_sha256':sha(args.entry_probe),
        'script_sha256':sha(__file__),
        'seam_helper_sha256':sha(Path(__file__).with_name('exact_offset_seam_reference.py')),
        'geometry_representation':'exact_control_offset',
        'origin_exact':[origin_x,F(0),F(0)], 'direction_exact':[-1,0,0],
        'origin_construction':'binary64 550.0 minus observed native entry distance',
        'radii_exact':{'a':24,'b':14}, 'center_witness_exact':witness,
        'inside_prefix_exact':[F(0),left],
        'inside_prefix_endpoint_witness_q':inside_endpoint_q,
        'inside_prefix_margin':1-max(inside_endpoint_q),
        'strict_outside_point_exact':point,
        'outside_bernstein_minimum_margin':minimum_margin,
        'outside_proof_nodes':nodes,'outside_proof_leaves':leaves,'outside_proof_max_depth':max_depth,
        'first_exit_enclosure_exact':[left,right], 'enclosure_width_exact':right-left,
        'proof':[
            'Exact seam-center squared metric distance is below one at both inside-prefix endpoints. Convexity in ray t puts the whole prefix strictly inside.',
            'Degree-six exact Bernstein coefficients are the square of each degree-three scaled offset, using exact binomial product factors. Exact de Casteljau restrictions cover every span and have strictly positive Q-1 coefficients at the outside endpoint.',
            'The compact-curve distance is continuous. The strict inside prefix excludes every earlier exit and the strictly outside right endpoint proves a first exit in the enclosure.'
        ],
        'claim_boundary':'Mathematical next-exit proof for the observed entry-derived origin. Does not attest a new native Region launch, signed surface output, normals, or particle histories.',
        'elapsed_seconds':time.monotonic()-started,'memory_cap_bytes':1024**3
    }
    args.output.write_text(json.dumps(encode(report),indent=2,allow_nan=False)+'\n')
    print(json.dumps({'state':report['state'],'exit_enclosure':[float(left),float(right)],
                      'nodes':nodes,'seconds':report['elapsed_seconds']}))


if __name__ == '__main__':
    main()
