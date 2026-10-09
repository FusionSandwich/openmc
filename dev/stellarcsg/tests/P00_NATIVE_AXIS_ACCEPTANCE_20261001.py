"""Fixture generator and independent analytic/Fraction owner-interval oracle."""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts'
XS = None


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def fixture(name, axis, offset, reverse=False, huge=False, duplicate=False, guard=None, runtime=True):
    folder = OUT / name
    folder.mkdir()
    g = ET.Element('geometry')
    bound = []
    planes = []
    for j, kind in enumerate(['x-plane','y-plane','z-plane']):
        lo, hi = (-1.e20-65536., 1.e20) if huge and j == axis else (-4.,4.)
        if guard in ['sentinel', 'unbounded-extreme'] and j == axis:
            lo, hi = -float.fromhex('0x1.fffffffffffffp+1023'), float.fromhex('0x1.fffffffffffffp+1023')
        for upper, x in enumerate([lo,hi]):
            sid = 1+2*j+upper
            ET.SubElement(g, 'surface', id=str(sid), type=kind, coeffs=str(x), boundary='vacuum')
            planes.append((sid,j,x,True))
        bound.extend([str(1+2*j),str(-(2+2*j))])
    interiors = [(10,0.),(11,1.),(20,0. if duplicate else offset),(21,1. if duplicate else offset+1.),(30,.5)]
    if guard == 'sentinel':
        maximum = float.fromhex('0x1.fffffffffffffp+1023')
        interiors = [(10,maximum/2),(11,maximum*.75),(20,maximum*.875),(21,maximum),(30,.5)]
    for sid, x in interiors:
        vacuum = guard == 'masked-vacuum' and sid == 30
        attributes = {'boundary': 'vacuum'} if vacuum else {}
        ET.SubElement(g,'surface',id=str(sid),type=['x-plane','y-plane','z-plane'][axis],coeffs=str(x),**attributes)
        planes.append((sid,axis,x,vacuum))
    outer = ' '.join(bound)
    if guard == 'unbounded-extreme':
        outer = ' '.join(bound[2:])  # Deliberately omit x enclosure halfspaces.
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
    materials = ET.Element('materials')
    if XS is not None:
        # The void test needs catalog discovery, not hundreds of Windows-path
        # existence probes or nuclide loads. Preserve one authentic unused
        # library entry from the installed index, with its resolved real path.
        catalog = ET.parse(XS).getroot()
        library = catalog.find('library')
        assert library is not None
        entry = ET.Element('library', library.attrib)
        directory = Path(catalog.findtext('directory') or Path(XS).parent)
        entry.set('path', str((directory / entry.get('path')).resolve()))
        minimal = ET.Element('cross_sections')
        minimal.append(entry)
        ET.ElementTree(minimal).write(folder/'cross_sections.xml')
        ET.SubElement(materials, 'cross_sections').text = 'cross_sections.xml'
    ET.ElementTree(materials).write(folder/'materials.xml')
    opt = '<experimental_axis_plane_events>true</experimental_axis_plane_events>' if runtime else ''
    cutoff = '<cutoff><time_neutron>1</time_neutron></cutoff>' if guard == 'time' else ''
    banking = '<surf_source_write><max_particles>1</max_particles></surf_source_write>' if guard == 'surface-bank' else ''
    (folder/'settings.xml').write_text(f'<settings><run_mode>fixed source</run_mode><particles>1</particles>'
        f'<batches>1</batches><source><space type="point"><parameters>0.25 0.31 0.42</parameters>'
        '</space></source><output><summary>false</summary><tallies>false</tallies></output>'
        f'{opt}{cutoff}{banking}</settings>')
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
        qs[-1]['enclosure_halfspaces'] = guard != 'unbounded-extreme'
    if guard is None and not huge and runtime:
        # Exact-origin start uses the whole outgoing contact group, not one hint.
        pos = [.31,.42,.27]; pos[axis] = 1.
        d = [0.,0.,0.]; d[axis] = 1.
        qs.append({'id':len(qs),'p':pos,'d':d,'hint':11,'steps':4,'mode':0})
    if guard == 'sentinel':
        qs = [qs[0] | {'p':[-maximum/2,.42,.27], 'steps':1}]
    if guard in ['stale','collision','material','overflow']:
        # A healthy query after the injected faults proves restoration and reuse.
        qs.append({'id':len(qs),'p':[.25,.42,.27],'d':[1.,0.,0.], 'hint':0,'steps':5,'mode':0})
    (folder/'queries.txt').write_text(''.join(' '.join(map(str,[q['id'],*q['p'],*q['d'],q['hint'],q['steps'],q['mode']]))+'\n' for q in qs))
    save(f'{name}.inputs.json',{'files':{str(p.relative_to(OUT)):sha(p) for p in folder.iterdir()},'queries':qs})
    return folder, planes, qs


def expected(planes, axis, q):
    if not q.get('enclosure_halfspaces', True):
        raise ValueError('cell lacks explicit common enclosure halfspaces')
    sign = int(q['d'][axis]); start = F(q['p'][axis]); cursor = start
    active = [(sid,F(x),vac) for sid,j,x,vac in planes if j==axis]
    a0,a1 = [x for sid,x,v in active if sid in [10,11]]
    b0,b1 = [x for sid,x,v in active if sid in [20,21]]
    outer = sorted(x for sid,x,v in active if sid in [1+2*axis,2+2*axis])
    # Fixture admission is independent of C++: BCs belong exclusively to the
    # six common outer faces, never to the masked Boolean tautology or a slab.
    if {sid for sid,j,x,v in planes if v} != set(range(1,7)):
        raise ValueError('vacuum outside common outer enclosure')
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
        nxt = owner(x)
        if nxt == current: continue
        vacuum = nxt == -1
        if vacuum:
            assert x in outer and any(sid in [1+2*axis,2+2*axis] for sid in group)
        assert owner(x,False) == current
        length = float(sign*(x-cursor))
        assert length > 0 and math.isfinite(length)
        if length == float.fromhex('0x1.fffffffffffffp+1023'):
            raise ValueError('finite interval collides with disabled cutoff sentinel')
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
    # The corrected runner owns admission, isolated builds and both option modes.
    from axis_review_acceptance import main as corrected_main
    corrected_main()


if __name__ == '__main__':
    main()
