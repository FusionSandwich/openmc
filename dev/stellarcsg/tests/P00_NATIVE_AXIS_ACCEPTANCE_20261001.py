"""One admitted native build/acceptance phase. No acquisition or successors."""
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'dev/stellarcsg/reports/p00-native-axis-20261001-01'
LOCK = ROOT.parent / 'local-coil-wave-20260926/compute.lock'
INVENTORY = ROOT / 'dev/stellarcsg/reports/P00_NATIVE_AXIS_INVENTORY_20261001.json'
PINNED = {'current': '9bf312f3e556b586fec44b714f179b97fa8dd5a25a249951674b01174b49432d',
          'baseline': '546be4c8af7da69196d6b4408de7bfb9af6ac0ddb424a90205cd513b60c19b9a'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def linux(p):
    p = str(Path(p).resolve()).replace('\\', '/')
    return '/mnt/' + p[0].lower() + p[2:]


def retained():
    for kind, identity in PINNED.items():
        assert sha(ROOT / f'dev/stellarcsg/reports/p00-step1-20261001-01/{kind}/build/lib/libopenmc.so') == identity


def run(label, args, remaining):
    seconds = max(1, int(remaining))
    shell = ('ulimit -v 2097152; ulimit -c 0; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1; '
             + shlex.join(['timeout', '--kill-after=5s', f'{seconds}s', *args]))
    start = time.monotonic()
    try:
        result = subprocess.run(['wsl', '-d', 'Debian', '--', 'bash', '-lc', shell],
                                capture_output=True, text=True, timeout=seconds + 15)
    except subprocess.TimeoutExpired as e:
        # No terminal child certificate: caller conservatively retains the lease.
        (OUT / f'{label}.unknown').write_text(str(e))
        raise
    (OUT / f'{label}.stdout').write_text(result.stdout)
    (OUT / f'{label}.stderr').write_text(result.stderr)
    save(f'{label}.exit.json', {'exit': result.returncode, 'seconds': time.monotonic()-start,
                               'args': args})
    if result.returncode:
        raise RuntimeError(f'FIRST_FAILURE {label} exit={result.returncode}')
    return result.stdout


def fixture(name, axis, offset, reverse=False, huge=False, duplicate=False, guard=None, runtime=True):
    folder = OUT / name
    folder.mkdir()
    g = ET.Element('geometry')
    bound = []
    planes = []
    for j, kind in enumerate(['x-plane','y-plane','z-plane']):
        lo, hi = (-1.e20-65536., 1.e20) if huge and j == axis else (-4.,4.)
        for upper, x in enumerate([lo,hi]):
            sid = 1+2*j+upper
            ET.SubElement(g, 'surface', id=str(sid), type=kind, coeffs=str(x), boundary='vacuum')
            planes.append((sid,j,x,True))
        bound.extend([str(1+2*j),str(-(2+2*j))])
    for sid, x in [(10,0.),(11,1.),(20,0. if duplicate else offset),(21,1. if duplicate else offset+1.),(30,.5)]:
        ET.SubElement(g,'surface',id=str(sid),type=['x-plane','y-plane','z-plane'][axis],coeffs=str(x))
        planes.append((sid,axis,x,False))
    outer = ' '.join(bound)
    a, b = '10 -11', '20 -21'
    if reverse:
        a, b = '-11 10', '-21 20'
    regions = [(100, f'{outer} (-10 | 11) (-20 | 21)'),
               (108, f'{outer} {a}'),
               (109, f'{outer} (-10 | 11) {b}' if reverse else f'{outer} {b} (-10 | 11)')]
    for cid, expr in regions:
        ET.SubElement(g,'cell',id=str(cid),universe='1',material='void',region=f'({expr}) (-30 | 30)')
    if guard == 'nonplanar':
        ET.SubElement(g,'surface',id='99',type='sphere',coeffs='0 0 0 100')
    if guard == 'material':
        # A synthetic material index is injected by the native guard client;
        # no nuclear-data acquisition or load is needed.
        pass
    ET.ElementTree(g).write(folder/'geometry.xml')
    (folder/'materials.xml').write_text('<materials/>')
    opt = '<experimental_axis_plane_events>true</experimental_axis_plane_events>' if runtime else ''
    cutoff = '<cutoff><time_neutron>1</time_neutron></cutoff>' if guard == 'time' else ''
    (folder/'settings.xml').write_text(f'<settings><run_mode>fixed source</run_mode><particles>1</particles>'
        f'<batches>1</batches><source><space type="point"><parameters>0.25 0.31 0.42</parameters>'
        '</space></source><output><summary>false</summary><tallies>false</tallies></output>'
        f'{opt}{cutoff}</settings>')
    tally = ET.Element('tallies')
    cells = [100,108,109]
    ids = [p[0] for p in planes]
    for fid, kind, bins in [(1,'cell',cells),(2,'surface',ids)]:
        f = ET.SubElement(tally,'filter',id=str(fid),type=kind)
        ET.SubElement(f,'bins').text = ' '.join(map(str,bins))
    if guard == 'filter':
        f = ET.SubElement(tally,'filter',id='3',type='energy')
        ET.SubElement(f,'bins').text = '0 20000000'
    for tid, fid, score in [(1,'1 3' if guard == 'filter' else '1','flux'),(2,'2','current')]:
        t = ET.SubElement(tally,'tally',id=str(tid))
        ET.SubElement(t,'filters').text = fid
        ET.SubElement(t,'scores').text = score
    ET.ElementTree(tally).write(folder/'tallies.xml')
    qs = []
    for sign in [1,-1]:
        pos = [.31,.42,.27]
        pos[axis] = -1.e20 if huge else (.25 if sign > 0 else (.75 if duplicate else offset+.75))
        if huge and sign < 0: continue
        direction = [0.,0.,0.]
        direction[axis] = sign
        if guard == 'oblique': direction[(axis+1)%3] = .5
        if guard == 'nonunit': direction[axis] = .5
        if guard == 'coplanar': pos[(axis+1)%3] = -4.
        qs.append({'id':len(qs), 'p':pos,'d':direction,'hint':0,'steps':5 if not huge else 4,'mode':
                   {'stale':1,'collision':2,'material':3,'overflow':4}.get(guard,0)})
    if guard is None and not huge and runtime:
        # Exact-origin start uses the whole outgoing contact group, not one hint.
        pos = [.31,.42,.27]; pos[axis] = 1.
        d = [0.,0.,0.]; d[axis] = 1.
        qs.append({'id':len(qs),'p':pos,'d':d,'hint':11,'steps':4,'mode':0})
    if not runtime: qs = [qs[0] | {'steps':1}]
    (folder/'queries.txt').write_text(''.join(' '.join(map(str,[q['id'],*q['p'],*q['d'],q['hint'],q['steps'],q['mode']]))+'\n' for q in qs))
    save(f'{name}.inputs.json',{'files':{str(p.relative_to(OUT)):sha(p) for p in folder.iterdir()},'queries':qs})
    return folder, planes, qs


def expected(planes, axis, q):
    sign = int(q['d'][axis]); start = F(q['p'][axis]); cursor = start
    active = [(sid,F(x),vac) for sid,j,x,vac in planes if j==axis]
    a0,a1 = [x for sid,x,v in active if sid in [10,11]]
    b0,b1 = [x for sid,x,v in active if sid in [20,21]]
    outer = sorted(x for sid,x,v in active if v)
    def inside(x,lo,hi,after=True):
        side = sign if after else -sign
        return (x > lo or x == lo and side > 0) and (x < hi or x == hi and side < 0)
    def owner(x,after=True):
        if not inside(x,*outer,after): return -1
        if inside(x,a0,a1,after): return 108
        if inside(x,b0,b1,after): return 109
        return 100
    current = owner(start)
    events = []
    flux = [0.,0.,0.]; currents = [0.]*len(planes)
    coords = sorted({x for sid,x,v in active if sign*(x-start)>0},reverse=sign<0)
    for x in coords:
        group = sorted(sid for sid,c,v in active if c==x)
        vacuum = any(v for sid,c,v in active if c==x)
        nxt = owner(x)
        if nxt == current and not vacuum: continue
        assert owner(x,False) == current
        length = float(sign*(x-cursor))
        assert length > 0 and math.isfinite(length)
        flux[[100,108,109].index(current)] += length
        currents[[p[0] for p in planes].index(group[0])] += sign
        events.append({'before':current,'after':nxt,'length':length,'region_length':length,
                       'coordinate':float(x),'surface':sign*group[0],'contacts':group,
                       'context':True,'weight':0. if vacuum else 1.,'scores':[flux[:],currents[:]]})
        cursor = x; current = nxt
        if vacuum or len(events)==q['steps']: break
    return events


def check(row, want):
    assert row['error'] == '', row
    assert row['events'] == want, (row, want)
    assert row['scores'] == want[-1]['scores'], row


def main():
    inventory = json.loads(INVENTORY.read_text(encoding='utf-8-sig'))
    from datetime import datetime, timezone
    assert (datetime.now(timezone.utc)-datetime.fromisoformat(inventory['time_utc'])).total_seconds() < 300
    assert inventory['acquisition_bytes']==0
    assert min(d['Free'] for d in inventory['drives'] if d['Name'] in ['C','D']) > 2*2**30
    retained()
    LOCK.mkdir() # atomic, never reclaim another owner's lease
    token = f'native-axis-{os.getpid()}-{time.time_ns()}'
    own = LOCK / 'P00_NATIVE_AXIS_OWNER.json'
    own.write_text(json.dumps({'owner':token,'max_threads':1,'max_virtual_bytes':2*2**30,'phase_seconds':900}))
    unknown = False
    started = time.monotonic(); deadline = started+900
    try:
        OUT.mkdir()
        tracked = ['CMakeLists.txt','src/axis_plane_events.cpp','src/cell.cpp','src/geometry.cpp',
                   'src/particle.cpp','src/settings.cpp','include/openmc/axis_plane_context.h',
                   'include/openmc/axis_plane_events.h','include/openmc/particle_data.h',
                   'include/openmc/cell.h','include/openmc/settings.h',
                   'dev/stellarcsg/src/dyadic_axis_plane.cpp','dev/stellarcsg/include/stellarcsg/dyadic_axis_plane.hpp',
                   'dev/stellarcsg/tests/test_native_axis_events.cpp',str(Path(__file__).relative_to(ROOT)),
                   str(INVENTORY.relative_to(ROOT)),'dev/stellarcsg/reports/P00_NATIVE_AXIS_PLAN_20261001.md']
        identities = {p:sha(ROOT/p) for p in tracked}
        save('identities.json',identities)
        mem = run('admission', ['python3','-c',
            "from pathlib import Path; m={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines()}; assert m['MemAvailable']>3*2**30; print(m['MemAvailable'])"],10)
        run('configure',['cmake','-S',linux(ROOT),'-B',linux(OUT/'build'),'-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_CXX_FLAGS_RELEASE=-O0 -DNDEBUG','-DOPENMC_USE_MPI=OFF','-DOPENMC_USE_OPENMP=OFF',
            '-DOPENMC_BUILD_TESTS=OFF','-DOPENMC_FORCE_VENDORED_LIBS=ON','-DFETCHCONTENT_FULLY_DISCONNECTED=ON',
            '-DOPENMC_ENABLE_STRICT_FP=ON','-DOPENMC_ENABLE_EXPERIMENTAL_AXIS_PLANES=ON',
            '-DOPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=OFF'],min(60,deadline-time.monotonic()))
        run('build',['cmake','--build',linux(OUT/'build'),'--target','stellarcsg_native_axis_test','-j','1'],deadline-time.monotonic()-110)
        results = []
        for axis in range(3):
            for kind,offset,duplicate in [('gap48',1.+2**-48,False),('adjacent',math.nextafter(1.,2.),False),
                                           ('touching',1.,False),('duplicate',0.,True)]:
                for reverse in [False,True]:
                    name=f'{kind}-axis{axis}-tokens{int(reverse)}'
                    folder, planes, qs = fixture(name,axis,offset,reverse,duplicate=duplicate)
                    stdout=run(name,[linux(OUT/'build/bin/stellarcsg_native_axis_test'),linux(folder),linux(folder/'queries.txt')],min(8,deadline-time.monotonic()))
                    rows=[json.loads(x[4:]) for x in stdout.splitlines() if x.startswith('ROW ')]
                    assert len(rows)==len(qs), (name,len(rows))
                    for row,q in zip(rows,qs): check(row,expected(planes,axis,q))
                    results.append({'model':name,'rows':rows});save('results.json',results)
        folder,planes,qs=fixture('rounded-times',0,1.+2**-48,huge=True)
        stdout=run('rounded-times',[linux(OUT/'build/bin/stellarcsg_native_axis_test'),linux(folder),linux(folder/'queries.txt')],8)
        rows=[json.loads(x[4:]) for x in stdout.splitlines() if x.startswith('ROW ')]
        assert len(rows)==len(qs)
        for row,q in zip(rows,qs):check(row,expected(planes,0,q))
        results.append({'model':'rounded-times','rows':rows});save('results.json',results)
        # Acceptance-validator negative controls: equal total is insufficient.
        import copy
        row=results[0]['rows'][0];want=row['events'];rejected=0
        for corrupt in ['owner','missing_gap','redistributed_flux','wrong_current','missing_contact']:
            bad=copy.deepcopy(row)
            if corrupt=='owner':bad['events'][0]['after']=108
            elif corrupt=='missing_gap':bad['events'].pop(1)
            elif corrupt=='redistributed_flux':bad['events'][1]['scores'][0][1]+=bad['events'][1]['scores'][0][0];bad['events'][1]['scores'][0][0]=0.
            elif corrupt=='wrong_current':bad['events'][0]['scores'][1]=[0.]*len(planes)
            else:bad['events'][0]['contacts']=[]
            try:check(bad,want)
            except AssertionError:rejected+=1
        assert rejected==5
        for guard in ['oblique','nonunit','coplanar','nonplanar','time','filter','stale','collision','material','overflow']:
            folder,planes,qs=fixture('unsupported-'+guard,0,1.+2**-48,guard=guard)
            stdout=run('unsupported-'+guard,[linux(OUT/'build/bin/stellarcsg_native_axis_test'),linux(folder),linux(folder/'queries.txt')],8)
            rows=[json.loads(x[4:]) for x in stdout.splitlines() if x.startswith('ROW ')]
            assert len(rows)==len(qs)
            for row in rows:
                assert 'AXIS_PLANE_UNSUPPORTED:' in row['error'] and row['events']==[],row
                assert all(v==0 for t in row['scores'] for v in t),row
            results.append({'model':'unsupported-'+guard,'rows':rows});save('results.json',results)
        folder,planes,qs=fixture('runtime-off',0,1.+2**-48,runtime=False)
        stdout=run('runtime-off',[linux(OUT/'build/bin/stellarcsg_native_axis_test'),linux(folder),linux(folder/'queries.txt')],8)
        rows=[json.loads(x[4:]) for x in stdout.splitlines() if x.startswith('ROW ')]
        assert len(rows)==1 and rows[0]['error']=='' and rows[0]['events'][0]['context'] is False,rows
        results.append({'model':'runtime-off','rows':rows});save('results.json',results)
        retained()
        assert all(sha(ROOT/p)==h for p,h in identities.items())
        size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
        assert size<300*2**20
        save('receipt.json',{'status':'NATIVE_STAGE1_PASS_PENDING_ROOT_REVIEW','seconds':time.monotonic()-started,
             'models':len(results),'rows':sum(len(r['rows']) for r in results),'validator_corruptions_rejected':rejected,
             'output_bytes':size,'library_sha256':sha(OUT/'build/lib/libopenmc.so'),
             'client_sha256':sha(OUT/'build/bin/stellarcsg_native_axis_test'),'lease':'released after terminal children'})
    except subprocess.TimeoutExpired:
        unknown=True
        raise
    except Exception as e:
        if OUT.exists():save('failure.json',{'status':'FIRST_FAILURE_NO_RETRY','error':repr(e),'seconds':time.monotonic()-started})
        raise
    finally:
        if not unknown and own.exists() and json.loads(own.read_text())['owner']==token:
            own.unlink();LOCK.rmdir()


if __name__=='__main__':main()
