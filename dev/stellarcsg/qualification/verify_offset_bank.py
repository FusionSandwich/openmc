"""Independent exact rational, bounded frozen-bank offset verifier.

The candidate supplies a proposed root only. Exact Bernstein positivity excludes
the complete earlier ray prefix, and exact center-ball witnesses cover inside
prefixes. Sampling/Newton merely proposes witnesses; it never accepts a claim.
No production geometry/proof implementation is imported.
"""
import argparse
from collections import Counter
import csv
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import resource
import struct
import time

import h5py
import numpy as np

EXPECTED_BANK = 'fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723'
FIELDS = ('centerline_coefficients', 'normal_coefficients',
          'binormal_coefficients', 'major_radius_coefficients',
          'minor_radius_coefficients')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key ' + key)
        result[key] = value
    return result


def reject(value):
    raise ValueError('nonstandard JSON constant ' + value)


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def split(values):
    work = list(values)
    left, right = [work[0]], [work[-1]]
    while len(work) > 1:
        work = [(a+b)/2 for a, b in zip(work, work[1:])]
        left.append(work[0])
        right.append(work[-1])
    return left, right[::-1]


def evaluate(control, u):
    work = list(control)
    while len(work) > 1:
        work = [(1-u)*a+u*b for a, b in zip(work, work[1:])]
    return work[0]


class BudgetExceeded(Exception):
    pass


class Geometry:
    def __init__(self, coil, arrays, characteristic):
        payload = struct.pack('<i', coil) + b''.join(
            struct.pack('<d', float(x)) for array in arrays
            for x in np.asarray(array).ravel())
        fnv = 1469598103934665603
        for byte in payload:
            fnv = ((fnv ^ byte)*1099511628211) & ((1 << 64)-1)
        self.fnv = format(fnv, 'x')
        self.sha = hashlib.sha256(payload).hexdigest()
        radii = [float(x) for array in arrays[3:] for x in array]
        if not radii or len(set(radii)) != 1 or radii[0] <= 0:
            raise ValueError('verifier supports constant isotropic radius only')
        self.r = F(radii[0])
        self.characteristic = characteristic
        points = [[F(float(x)) for x in p] for p in arrays[0]]
        self.bounds = [(min(p[a] for p in points)-self.r,
                        max(p[a] for p in points)+self.r) for a in range(3)]
        self.spans, self.elevated, self.square = [], [], []
        self.samples, self.sample_keys = [], []
        n = len(points)
        for s in range(n):
            c = []
            for a in range(3):
                p0, p1, p2, p3 = [points[(s+k) % n][a] for k in (-1, 0, 1, 2)]
                c.append(((p0+4*p1+p2)/6, (2*p1+p2)/3,
                          (p1+2*p2)/3, (p1+4*p2+p3)/6))
            self.spans.append(c)
            self.elevated.append([[sum(c[a][j]*F(math.comb(3,j)*math.comb(3,k-j),
                                  math.comb(6,k)) for j in range(4)
                                  if 0 <= k-j <= 3) for k in range(7)] for a in range(3)])
            self.square.append([sum(c[a][i]*c[a][j]*F(math.comb(3,i)*math.comb(3,j),
                                math.comb(6,k)) for a in range(3)
                                for i in range(4) for j in range(4) if i+j == k)
                                for k in range(7)])
            for j in range(17):
                u = j/16
                self.samples.append([float(evaluate(v, F(u))) for v in c])
                self.sample_keys.append((s, u))
        self.samples = np.asarray(self.samples)

    def ray_end(self, o, d):
        upper = None
        for a in range(3):
            if d[a]:
                t = max((b-o[a])/d[a] for b in self.bounds[a])
                upper = t if upper is None else min(upper, t)
            elif not self.bounds[a][0] <= o[a] <= self.bounds[a][1]:
                return F(0)
        return max(F(0), upper)

    def grid(self, s, o, d, l, h):
        p = [[o[a]+t*d[a] for a in range(3)] for t in (l, h)]
        pp = [dot(p[0],p[0]), dot(p[0],p[1]), dot(p[1],p[1])]
        pe = [p[0], [(x+y)/2 for x,y in zip(*p)], p[1]]
        c = self.elevated[s]
        return [[self.square[s][k]+pp[i]-self.r*self.r
                 -2*sum(pe[i][a]*c[a][k] for a in range(3))
                 for k in range(7)] for i in range(3)]

    def witness(self, o, d, t):
        p = [o[a]+t*d[a] for a in range(3)]
        pf = np.array([float(x) for x in p])
        indices = np.argsort(np.sum((self.samples-pf)**2, axis=1))[:3]
        for index in indices:
            s, u = self.sample_keys[index]
            cf = np.asarray(self.spans[s], dtype=float)
            # A bounded Newton proposal on one curve chart; exact checks follow.
            for _ in range(10):
                c = np.array([evaluate(v,u) for v in cf])
                dc = np.array([evaluate(3*np.diff(v),u) for v in cf])
                ddc = np.array([evaluate(6*np.diff(v,n=2),u) for v in cf])
                denom = float(dot(dc,dc)+dot(c-pf,ddc))
                if denom <= 0:
                    break
                updated = min(1.,max(0.,u-float(dot(c-pf,dc))/denom))
                if updated == u:
                    break
                u = updated
            uq = F(float(u))
            center = [evaluate(v,uq) for v in self.spans[s]]
            if dot([p[a]-center[a] for a in range(3)],
                   [p[a]-center[a] for a in range(3)]) < self.r*self.r:
                return s, uq, center
        return None


class Verifier:
    def __init__(self, g, deadline, nodes):
        self.g, self.deadline, self.limit = g, deadline, nodes
        self.nodes = self.outside_leaves = self.inside_leaves = 0
        self.minimum_outside_margin = None
        self.minimum_inside_margin = None

    def tick(self):
        self.nodes += 1
        if self.nodes > self.limit or time.monotonic() > self.deadline:
            raise BudgetExceeded()

    def outside(self, o, d, l, h):
        if h < l:
            return True
        for s in range(len(self.g.spans)):
            todo = [(self.g.grid(s,o,d,l,h),0,0)]
            while todo:
                grid, td, ud = todo.pop()
                self.tick()
                margin = min(min(row) for row in grid)
                if margin > 0:
                    self.outside_leaves += 1
                    self.minimum_outside_margin = (margin if self.minimum_outside_margin is None
                                                   else min(margin,self.minimum_outside_margin))
                    continue
                if max(max(row) for row in grid) <= 0:
                    return False
                if td+ud >= 100:
                    raise BudgetExceeded()
                # Alternate both dimensions. Every child grid is an exact
                # de Casteljau restriction of the parent polynomial.
                if td <= ud:
                    halves = [split([grid[i][k] for i in range(3)]) for k in range(7)]
                    children = [[[halves[k][part][i] for k in range(7)]
                                 for i in range(3)] for part in range(2)]
                    todo.extend((child,td+1,ud) for child in children)
                else:
                    halves = [split(row) for row in grid]
                    todo.extend(( [halves[i][part] for i in range(3)],td,ud+1)
                                for part in range(2))
        return True

    def inside(self, o, d, l, h):
        todo = [(l,h,0)]
        while todo:
            a,b,depth = todo.pop()
            self.tick()
            witness = self.g.witness(o,d,(a+b)/2)
            if witness:
                center = witness[2]
                distances = [sum((o[k]+t*d[k]-center[k])**2 for k in range(3))
                             for t in (a,b)]
                if max(distances) < self.g.r**2:
                    # The fixed-center squared distance is convex in t.
                    self.inside_leaves += 1
                    margin = self.g.r**2-max(distances)
                    self.minimum_inside_margin = (margin if self.minimum_inside_margin is None
                                                  else min(margin,self.minimum_inside_margin))
                    continue
            if depth >= 60:
                return False
            m = (a+b)/2
            todo.extend(((a,m,depth+1),(m,b,depth+1)))
        return True


def make_geometries(h5):
    result = {}
    for rigid in (False, True):
        center,normal,binormal = [],[],[]
        for i in range(64):
            a = 2*math.pi*i/64
            c,s = math.cos(a),math.sin(a)
            p,n,b = (5*c,5*s,0.),(0.,0.,1.),(c,s,0.)
            if rigid:
                p = (.6*p[0]-.8*p[2]+11,p[1]-7,.8*p[0]+.6*p[2]+3)
                n = (.6*n[0]-.8*n[2],n[1],.8*n[0]+.6*n[2])
                b = (.6*b[0]-.8*b[2],b[1],.8*b[0]+.6*b[2])
            center.append(p); normal.append(n); binormal.append(b)
        result['torus_rigid' if rigid else 'torus'] = Geometry(
            9041 if rigid else 9040,[center,normal,binormal,[.25]*64,[.25]*64],5.)
    with h5py.File(h5) as f:
        g = f['/coils/coil_031']
        result['wistell_coil031'] = Geometry(int(g.attrs['coil_id']),
            [g[field][...] for field in FIELDS],float(g.attrs['length_cm']))
    return result


def exact_selfchecks(geometries):
    """Check polynomial construction against direct exact curve evaluation."""
    checked = 0
    for g in geometries.values():
        o, d = [F(7,3),F(-5,7),F(2,11)], [F(1,2),F(-3,5),F(1,9)]
        l,h,v,u = F(1,7),F(13,5),F(2,5),F(3,7)
        for s in (0,len(g.spans)//3,len(g.spans)-1):
            grid = g.grid(s,o,d,l,h)
            q = evaluate([evaluate(row,u) for row in grid],v)
            t = l+(h-l)*v
            delta = [o[a]+t*d[a]-evaluate(g.spans[s][a],u) for a in range(3)]
            if q != dot(delta,delta)-g.r**2:
                raise ValueError('exact Bernstein construction selfcheck failed')
            halves = [split(row) for row in grid]
            for part in (0,1):
                child = [halves[i][part] for i in range(3)]
                if evaluate([evaluate(row,u) for row in child],v) != evaluate(
                        [evaluate(row,(u+part)/2) for row in grid],v):
                    raise ValueError('exact de Casteljau restriction selfcheck failed')
            checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bank',type=Path,default=Path(__file__).with_name('recovery04_frozen_bank.csv'))
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--wistell',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=float,default=540)
    parser.add_argument('--nodes',type=int,default=18000)
    parser.add_argument('--epsilon',type=float,default=2e-8,
                        help='absolute candidate distance error bound in cm')
    parser.add_argument('--ids',default='')
    parser.add_argument('--allow-axis-without-export',action='store_true')
    args = parser.parse_args()
    if not math.isfinite(args.epsilon) or args.epsilon <= 0:
        parser.error('epsilon must be positive and finite')
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    started = time.monotonic()
    deadline = started+args.seconds
    args.output.mkdir(exist_ok=False)
    hashes = {k:sha(p) for k,p in [('bank',args.bank),('candidate',args.candidate),
                                  ('wistell',args.wistell),('verifier',__file__)]}
    if hashes['bank'] != EXPECTED_BANK:
        raise ValueError('wrong frozen bank SHA256')
    with args.bank.open(newline='') as stream:
        bank = list(csv.DictReader(stream))
    candidate = [json.loads(line,object_pairs_hook=unique,parse_constant=reject)
                 for line in args.candidate.read_text().splitlines()]
    queries = [r for r in candidate if r.get('kind') == 'query']
    if (len(candidate) != 161 or len(queries) != 160 or
            sum(r.get('kind') == 'summary' for r in candidate) != 1 or
            [r.get('id') for r in queries] != [r['id'] for r in bank]):
        raise ValueError('candidate strict schema/order/count mismatch')
    summary = next(r for r in candidate if r.get('kind') == 'summary')
    if (type(summary.get('query_count')) is not int or summary['query_count'] != 160 or
            summary.get('candidate_failures') != sum(r.get('candidate_state') == 'FAIL' for r in queries) or
            summary.get('blocked') != sum(r.get('candidate_state') == 'BLOCKED' for r in queries)):
        raise ValueError('candidate summary disagrees with rows')
    for claim in queries:
        disposition = claim.get('candidate_disposition')
        found = claim.get('candidate_found')
        distance = claim.get('candidate_distance')
        if type(found) is not bool or disposition not in ('hit','no_hit','unresolved'):
            raise ValueError('candidate disposition/found invalid')
        if disposition == 'hit':
            if not found or type(distance) not in (float,int) or not math.isfinite(distance) or distance < 0:
                raise ValueError('candidate hit fields inconsistent')
        elif found or distance is not None:
            raise ValueError('candidate no-hit/unresolved fields inconsistent')
    geometries = make_geometries(args.wistell)
    selfchecks = exact_selfchecks(geometries)
    construction_seconds = time.monotonic()-started
    for row in bank:
        g = geometries[row['geometry']]
        if g.fnv != row['coefficient_hash']:
            raise ValueError('coefficient FNV mismatch '+row['geometry'])
        if row['source_sha256'] and row['source_sha256'] != hashes['wistell']:
            raise ValueError('fixture SHA mismatch')
    receipts = []
    selected = set(args.ids.split(',')) if args.ids else None
    with (args.output/'queries.jsonl').open('w') as stream:
        for row,claim in zip(bank,queries):
            if selected and row['id'] not in selected:
                continue
            report = {'id':row['id'],'state':'UNKNOWN','candidate_disposition':claim['candidate_disposition']}
            g = geometries[row['geometry']]
            v = Verifier(g,deadline,args.nodes)
            query_started = time.monotonic()
            try:
                if claim.get('geometry_representation') != 'exact_control_offset':
                    raise ValueError('wrong candidate geometry representation')
                if claim.get('candidate_state') != 'PASS':
                    report['reason'] = 'candidate_not_resolved_PASS'
                    raise BudgetExceeded()
                if (claim.get('coefficient_hash') != row['coefficient_hash'] or
                        claim.get('source_sha256') != row['source_sha256']):
                    raise ValueError('candidate coefficient/source association mismatch')
                o = [F(float(row['o'+a])) for a in 'xyz']
                if 'ray_origin' in claim and [F(x) for x in claim['ray_origin']] != o:
                    raise ValueError('candidate ray origin differs from frozen bank')
                direction = claim.get('normalized_direction')
                if direction is None:
                    raw = [float(row['d'+a]) for a in 'xyz']
                    if not args.allow_axis_without_export or sum(x != 0 for x in raw) != 1:
                        report['reason'] = 'normalized_direction_export_missing'
                        raise BudgetExceeded()
                    direction = [math.copysign(1.,x) if x else 0. for x in raw]
                if len(direction) != 3 or not all(type(x) in (float,int) and math.isfinite(x) for x in direction):
                    raise ValueError('bad normalized_direction')
                d = [F(x) for x in direction]
                raw = [float(row['d'+a]) for a in 'xyz']
                scale = max(abs(x) for x in raw)
                reduced = [x/scale for x in raw]
                norm = math.hypot(*reduced)
                proposed = [x/norm for x in reduced]
                if any(abs(x-y) > 8*math.ulp(y) for x,y in zip(direction,proposed)):
                    raise ValueError('exported normalized direction is inconsistent with frozen ray')
                report['direction_hex'] = [float(x).hex() for x in d]
                minimum = F(0)
                if row['category'].startswith('coincident_'):
                    # Use an exact lower bound on the engine's rounded factor
                    # times characteristic product. This is safe whether its
                    # arithmetic uses binary64 or a wider long double.
                    # Covering this slightly longer prefix covers every engine
                    # eligible t, without assuming a binary64-rounded push.
                    factor = 1-F(1,2**52)
                    minimum = max(F(64*1e-11),F(8*1e-10)*F(g.characteristic)*factor,
                                  F(64*2**-52)*F(g.characteristic)*factor)
                    report['coincident_minimum_lower_bound_exact'] = str(minimum)
                end = g.ray_end(o,d)
                if time.monotonic() > deadline:
                    raise BudgetExceeded()
                if claim['candidate_disposition'] == 'no_hit':
                    ok = v.outside(o,d,minimum,end)
                    report.update(state='CERTIFIED' if ok else 'UNKNOWN',
                                  proof='exact_positive_bivariate_Bernstein_entire_ray_with_control_hull_tail',
                                  interval=[str(minimum),str(end)])
                elif claim['candidate_disposition'] == 'hit':
                    distance = claim['candidate_distance']
                    if type(distance) not in (float,int) or not math.isfinite(distance) or distance < 0:
                        raise ValueError('bad hit distance')
                    epsilon = F(args.epsilon)
                    l,h = max(minimum,F(distance)-epsilon),F(distance)+epsilon
                    if l > h:
                        raise ValueError('hit is suppressed by coincident minimum')
                    origin_inside = g.witness(o,d,minimum) is not None
                    if origin_inside:
                        prefix = v.inside(o,d,minimum,l)
                        after = v.outside(o,d,h,h)
                        proof = 'exact_fixed_center_ball_inside_prefix_and_exact_Bernstein_outside_endpoint'
                    else:
                        prefix = v.outside(o,d,minimum,l)
                        witness = g.witness(o,d,h)
                        after = witness is not None
                        if witness:
                            report['inside_endpoint_witness'] = {
                                'span':witness[0], 'u_exact':str(witness[1]),
                                'center_exact':[str(x) for x in witness[2]],
                                'squared_distance_margin_exact':str(g.r**2-sum(
                                    (o[a]+h*d[a]-witness[2][a])**2 for a in range(3)))}
                        proof = 'exact_positive_Bernstein_outside_prefix_and_exact_inside_center_witness'
                    report.update(state='CERTIFIED' if prefix and after else 'UNKNOWN',
                                  prefix_certified=prefix,after_endpoint_certified=after,
                                  proof=proof,bracket=[str(l),str(h)],
                                  absolute_distance_error_bound_cm=float(epsilon),
                                  initial_inside=origin_inside)
                else:
                    report['reason'] = 'candidate_unresolved'
            except BudgetExceeded:
                report.setdefault('reason','bounded_nodes_depth_or_time_exhausted')
            report.update(nodes=v.nodes,outside_leaves=v.outside_leaves,inside_leaves=v.inside_leaves,
                          proof_seconds=time.monotonic()-query_started,
                          minimum_positive_Bernstein_margin_exact=str(v.minimum_outside_margin)
                            if v.minimum_outside_margin is not None else None,
                          minimum_fixed_ball_inside_margin_exact=str(v.minimum_inside_margin)
                            if v.minimum_inside_margin is not None else None)
            receipts.append(report)
            stream.write(json.dumps(report,allow_nan=False)+'\n'); stream.flush()
            print(json.dumps({k:report[k] for k in ('id','state','nodes')}),flush=True)
    final_hashes = {k:sha(p) for k,p in [('bank',args.bank),('candidate',args.candidate),
                                       ('wistell',args.wistell),('verifier',__file__)]}
    receipt = {'schema':'stellarcsg.independent-exact-offset-bank/v1',
               'state':'FULL_BANK_CERTIFIED' if len(receipts)==160 and all(r['state']=='CERTIFIED' for r in receipts) and hashes==final_hashes else 'PARTIAL_CERTIFICATION',
               'states':dict(Counter(r['state'] for r in receipts)),
               'hashes_before':hashes,'hashes_after':final_hashes,
               'geometry_identities':{k:{'fnv':g.fnv,'payload_sha256':g.sha} for k,g in geometries.items()},
               'seconds':time.monotonic()-started,'memory_cap_bytes':1024**3,
               'geometry_construction_and_selfcheck_seconds':construction_seconds,
               'exact_polynomial_and_subdivision_selfchecks':selfchecks,
               'absolute_distance_error_bound_cm':args.epsilon,
               'claim_boundary':'Exact mathematical cardinal cubic of original binary64 controls, constant isotropic radii, binary64 normalized ray components as exported by candidate. Certificates prove existence of a boundary in the stated bracket and exclude every earlier eligible boundary. Candidate proposals guide brackets only. FNV is an identity check, not cryptographic runtime binding. UNKNOWN never becomes PASS.'}
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(json.dumps(receipt,allow_nan=False),flush=True)


if __name__ == '__main__':
    main()
