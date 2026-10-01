"""One fixed no-build local block, with separate round and P00 families."""
import json, os, pathlib, resource, shutil, subprocess, time
import xml.etree.ElementTree as ET
import h5py
import numpy as np
import meaningful_coil_009 as common

ROOT=common.ROOT; REPORT=common.REPORT; OUT=REPORT/'matched-replay-010'
LOCK=common.LOCK; PRIOR=common.PRIOR; FIX=common.FIXTURE
SIB=ROOT.parent
OLD=SIB/'stellarcsg-run-compare-06/build/native-old-control-06'
REC=SIB/'stellarcsg-run-compare-06/build/native-recovered-06'
LOCAL=SIB/'stellarcsg-local-continuation-20260925'
P00=LOCAL/'dev/stellarcsg/reports/local-cont-20260925/p00-magnet-material-bank-02'
P00PAY=LOCAL/'dev/stellarcsg/reports/local-cont-20260925/p00-periodic-facet-candidate-02.h5'
P00BIN=LOCAL/'build/native-local-20260925/bin/openmc'
P00LIB=LOCAL/'build/native-local-20260925/lib/libopenmc.so'
sha=common.sha; save=common.save; stamp=common.stamp

def log(status,reason,**extra):
    with (REPORT/'ATTEMPTS.jsonl').open('a') as f:
        f.write(json.dumps(dict(utc=stamp(),dispatch='method-comparison-010',disposition=status,reason=reason,**extra))+'\n')

def limited():
    resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824))
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})

def settings(case,source):
    tree=ET.parse(FIX.parent/'coil-spline-1741/settings.xml'); r=tree.getroot()
    r.find('particles').text='1000'; r.find('batches').text='20'
    r.find('state_point/batches').text='20'; r.find('source').set('file',str(source))
    tree.write(case/'settings.xml',encoding='utf-8',xml_declaration=True)

def p00_flat_geometry(original,case):
    """Eighteen declared PCA annular-envelope sizing proxies, not target equivalents."""
    with h5py.File(P00PAY) as f:
        group=f['facets/one_period']; tri=np.asarray(group['triangle_vertices']); ids=np.asarray(group['component_ids'])
    if tri.shape!=(3348,3,3) or ids.shape!=(3348,) or set(ids)!=set(range(8,26)):
        raise RuntimeError('P00 component payload layout differs')
    geom=ET.Element('geometry'); originals=ET.parse(original).getroot()
    for s in originals.findall('surface'):
        if int(s.get('id')) in [901,902,904,905,906]: geom.append(ET.fromstring(ET.tostring(s)))
    world='901 902 -904 905 -906'; inside=[]; params=[]
    for component in range(8,26):
        points=tri[ids==component].reshape(-1,3); unique=np.unique(points,axis=0)
        center=unique.mean(axis=0); shifted=unique-center
        eigenvalues,eigenvectors=np.linalg.eigh(shifted.T@shifted/len(unique))
        axis=eigenvectors[:,0]
        if axis[np.argmax(np.abs(axis))]<0: axis=-axis
        axial=shifted@axis; radial=np.linalg.norm(shifted-np.outer(axial,axis),axis=1)
        outer=float(radial.max()); inner=max(float(radial.min()),outer*0.05)
        low=float(axial.min()); high=float(axial.max())
        if not (np.isfinite([outer,inner,low,high]).all() and 0<inner<outer and low<high):
            raise RuntimeError('invalid flat-ring sizing '+str(component))
        matrix=np.eye(3)-np.outer(axis,axis); ac=matrix@center
        base=[matrix[0,0],matrix[1,1],matrix[2,2],2*matrix[0,1],2*matrix[1,2],2*matrix[0,2],-2*ac[0],-2*ac[1],-2*ac[2]]
        a,b,c,d=[3000+4*(component-8)+k for k in range(4)]
        for sid,radius in [(a,inner),(b,outer)]:
            values=base+[float(center@ac-radius*radius)]
            ET.SubElement(geom,'surface',id=str(sid),type='quadric',coeffs=' '.join(format(float(v),'.17g')for v in values))
        for sid,height in [(c,low),(d,high)]:
            values=list(axis)+[float(axis@center+height)]
            ET.SubElement(geom,'surface',id=str(sid),type='plane',coeffs=' '.join(format(float(v),'.17g')for v in values))
        region=f'{a} -{b} {c} -{d}'
        previous=' '.join(f'~({r})'for r in inside)
        ET.SubElement(geom,'cell',id=str(2000+component),material='7',universe='1',region=f'{world} {previous} ({region})')
        inside.append(region)
        params.append(dict(component_id=component,center_cm=center.tolist(),axis=axis.tolist(),inner_radius_cm=inner,outer_radius_cm=outer,axial_limits_cm=[low,high],eigenvalues=eigenvalues.tolist(),vertices=len(unique),triangles=int(np.count_nonzero(ids==component)),bbox_min_cm=points.min(axis=0).tolist(),bbox_max_cm=points.max(axis=0).tolist(),native_annular_volume_cm3=float(np.pi*(outer*outer-inner*inner)*(high-low)),fit='unweighted unique-vertex PCA, smallest eigenvector axis, min/max radial and axial envelope, inner floor 5% of outer',fidelity='NOT_EQUIVALENT; envelopes can fill large gaps and differ in periodic cap geometry; no volume/chord fit or containment proof'))
    ET.SubElement(geom,'cell',id='2000',material='void',universe='1',region=world+' '+' '.join(f'~({r})'for r in inside))
    ET.ElementTree(geom).write(case/'geometry.xml',encoding='utf-8',xml_declaration=True)
    save(case/'flat-ring-parameters.json',dict(method='18 native arbitrary-axis circular annular rectangles via two quadrics/two planes each',priority='ascending component IDs, same bookkeeping policy as facet family',components=params,source_payload_sha256=sha(P00PAY),geometry_fidelity='sizing control only; periodic faceted P00 target differs'))

def prepare(name,family):
    case=OUT/name; start=time.monotonic(); case.mkdir()
    if family=='P00':
        if name=='p00_facets': shutil.copy2(P00/'geometry.xml',case/'geometry.xml')
        else:p00_flat_geometry(P00/'geometry.xml',case)
        mat=ET.parse(FIX.parent/'coil-spline-1741/materials.xml'); mat.getroot().find('material').set('id','7')
        mat.write(case/'materials.xml',encoding='utf-8',xml_declaration=True)
        tally=ET.parse(FIX.parent/'coil-spline-1741/tallies.xml')
        for fil in tally.getroot().findall('filter'):
            if fil.get('type')=='cell':fil.find('bins').text=' '.join(str(2000+k)for k in range(8,26))
            if fil.get('type')=='material':fil.find('bins').text='7'
        tally.write(case/'tallies.xml',encoding='utf-8',xml_declaration=True)
        settings(case,P00/'source.h5')
    else:
        for item in ['geometry.xml','materials.xml','tallies.xml']:
            shutil.copy2(FIX.parent/'coil-spline-1741'/item,case/item)
        if name in ['composite_kernel_old_control','recovered_generic','current_legacy']:
            geom=ET.parse(case/'geometry.xml'); surface=geom.getroot().find("surface[@type='swept-spline']")
            surface.set('representation','legacy_rounded_frame'); surface.attrib.pop('bernstein_prefix',None)
            geom.write(case/'geometry.xml',encoding='utf-8',xml_declaration=True)
        settings(case,FIX/'source.h5')
    return case,time.monotonic()-start

def main():
    if not OUT.is_dir() or not (OUT/'windows-inventory.json').is_file():raise RuntimeError('fresh Windows inventory required')
    try:LOCK.mkdir()
    except FileExistsError:
        log('COMPUTE_DEFERRED','lease held; no retries')
        save(OUT/'TERMINAL.json',dict(disposition='COMPUTE_DEFERRED')); return
    owner=dict(owner='profile',thread='01a0e00b-8dbd-7402-933f-c6fb0089fb53',pid=os.getpid(),run=OUT.name,utc=stamp())
    (LOCK/'owner.json').write_text(json.dumps(owner));log('PASS','lease acquired',owner=owner)
    start=time.monotonic(); workers=[]
    try:
        common.OUT=OUT; common.inventory()
        old_receipt_path=SIB/'stellarcsg-run-compare-06/dev/stellarcsg/reports/product06/old-control-build-receipt.json'
        old_receipt=json.loads(old_receipt_path.read_text())
        material_receipt=json.loads((P00/'receipt.json').read_text())
        old_source=SIB/'openmc-stellarcsg-composite/dev/stellarcsg/src/compiled_swept_surface.cpp'
        if sha(old_source)!=old_receipt['source']['sha256']:raise RuntimeError('composite kernel differs from retained old control')
        expected={common.SOURCE:common.CURRENT,common.NATIVE:common.LIB,PRIOR/'candidate.so':common.DSO,
                  OLD/'libopenmc.so':old_receipt['output']['library_sha256'],
                  OLD/'openmc':old_receipt['output']['executable_sha256'],
                  REC/'lib/libopenmc.so':old_receipt['base']['library_sha256'],
                  P00BIN:material_receipt['hashes']['binary'],P00LIB:material_receipt['hashes']['library'],
                  P00PAY:material_receipt['hashes']['facet_payload'],P00/'source.h5':material_receipt['hashes']['source.h5'],
                  P00/'geometry.xml':material_receipt['hashes']['geometry.xml']}
        for p,h in expected.items():
            if sha(p)!=h:raise RuntimeError('input identity gate '+str(p))
        runtime=json.loads((REPORT/'profile-02/runtime-identities.json').read_text())
        for item in ['data_index','data_file']:
            if sha(runtime[item])!=runtime[item+'_sha256']:raise RuntimeError('nuclear data changed')
        fixture_manifest=json.loads((FIX/'manifest.json').read_text())
        for item in ['coil.h5','source.h5']:
            if sha(FIX/item)!=fixture_manifest['hashes'][item]:raise RuntimeError('round fixture changed')
        methods=[
            ('p00_facets','P00',P00BIN,P00LIB,None),
            ('p00_flat_rings','P00',P00BIN,P00LIB,None),
            ('certified_cache','round',common.EXE,common.NATIVE,PRIOR/'candidate.so'),
            ('composite_kernel_old_control','round',OLD/'openmc',OLD/'libopenmc.so',None),
            ('recovered_generic','round',REC/'bin/openmc',REC/'lib/libopenmc.so',None),
            ('current_legacy','round',common.EXE,common.NATIVE,None)]
        frozen=list(expected)+[REC/'bin/openmc',common.EXE,old_source,old_receipt_path,P00/'receipt.json',
            FIX/'coil.h5',FIX/'source.h5',pathlib.Path(runtime['data_index']),pathlib.Path(runtime['data_file']),
            pathlib.Path(__file__),pathlib.Path(common.__file__),
            SIB/'stellarcsg-local-continuation-20260925/dev/stellarcsg/reports/local-cont-20260925/strict-old-01/oracle-comparison.json']
        identities={str(p):sha(p)for p in frozen};save(OUT/'identities.json',identities)
        save(OUT/'PLAN.json',dict(workers=[dict(name=a,family=b,binary=str(c),library=str(d),preload=str(e)if e else None)for a,b,c,d,e in methods],histories_per_worker=20000,batches=20,particles=1000,seed=1741,tallies='on',threads=1,affinity='same single allowed CPU',worker_memory_bytes=1073741824,worker_timeout_seconds=600,block_timeout_seconds=1800,software_build='NOT_RUN; existing coherent runtimes',acquisition_bytes=0,rollback='no source/binary/environment mutation; retain fresh artifacts',round_geometry='same HDF5 coefficient payload, legacy moving-frame round tube versus restricted constant-metric offset; equivalence OPEN',P00_geometry='accepted periodic 18-component faceted P00 mesh versus fitted native flat-ring sizing envelopes, Fe56 diagnostic replaces historical 51-nuclide magnet mixture, retained 18-site 1MeV source',excluded=['exact C0 direct native adapter: original complete composite runtime dependencies unavailable; kernel control adapter differs','current uncached offset: inventoried retained baseline, omitted from this fixed block to prioritize full-pack facet and legacy methods','new BVH proposal: source-only, not compiled','DAGMC/Embree: dependency closure unsupported'],failure_policy='first capability, native, identity or completeness failure stops whole block; no retries; partial successful rows retained',promotion='old generic wrong-first-root/tangent cases remain disqualifying; no fastest-production claim'))
        loader=[]
        for name,family,exe,lib,preload in methods:
            env=os.environ.copy();env.pop('LD_PRELOAD',None);env['LD_LIBRARY_PATH']=str(lib.parent)
            p=subprocess.run(['ldd',str(exe)],env=env,capture_output=True,text=True,timeout=15)
            loader.append(dict(method=name,binary=str(exe),library=str(lib),stdout=p.stdout,stderr=p.stderr,exit_code=p.returncode))
            save(OUT/'loader-bindings.json',loader)
            if p.returncode or 'not found' in p.stdout or str(lib) not in p.stdout:
                raise RuntimeError('unresolved or wrong complete loader '+name)
        # Current legacy adapter uses checked distance; unresolved must throw, not become a miss.
        for name,family,exe,lib,preload in methods:
            if any(sha(p)!=h for p,h in identities.items()):raise RuntimeError('frozen identity changed')
            case,prep=prepare(name,family)
            env=os.environ.copy();env.pop('LD_PRELOAD',None)
            env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                       LD_LIBRARY_PATH=str(lib.parent),OPENMC_CROSS_SECTIONS=runtime['data_index'])
            if preload:env['LD_PRELOAD']=str(preload)
            remaining=1800-(time.monotonic()-start)
            if remaining<=0:raise RuntimeError('block deadline')
            timeout=min(600,remaining); launched=time.monotonic()
            with (case/'process.stdout').open('w')as a,(case/'process.stderr').open('w')as b:
                try:
                    child=subprocess.run([str(exe)],cwd=case,env=env,stdout=a,stderr=b,preexec_fn=limited,timeout=timeout)
                    run=dict(exit_code=child.returncode,timeout=False)
                except subprocess.TimeoutExpired:run=dict(exit_code=None,timeout=True)
            wall=time.monotonic()-launched
            run.update(command=[str(exe)],environment={k:env[k]for k in ['OMP_NUM_THREADS','LD_LIBRARY_PATH','OPENMC_CROSS_SECTIONS']},preload=str(preload)if preload else None,process_wall_seconds=wall,preparation_seconds=prep,timeout_seconds=timeout,threads=1,address_space_bytes=1073741824)
            save(case/'process-receipt.json',run)
            if run['exit_code']!=0:raise RuntimeError('native worker failed '+name)
            text=(case/'process.stdout').read_text()+(case/'process.stderr').read_text()
            failures=[line for line in text.splitlines()if any(key in line.lower()for key in ['lost particle','could not locate','unresolved','error:','fatal error'])]
            if failures:raise RuntimeError('native diagnostics '+name+repr(failures))
            sp=case/'statepoint.20.h5'; arrays=[]; audit_start=time.monotonic()
            with h5py.File(sp)as f:
                counters={k:int(f[k][()])for k in ['n_particles','n_batches','current_batch','n_realizations']}
                if counters!=dict(n_particles=1000,n_batches=20,current_batch=20,n_realizations=20):raise RuntimeError('incomplete histories '+name)
                timers={k:float(v[()])for k,v in f['runtime'].items()}
                if not all(np.isfinite(v)and v>=0 for v in timers.values()):raise RuntimeError('invalid timer '+name)
                def capture(path,obj):
                    if isinstance(obj,h5py.Dataset)and path.startswith('tallies/')and path.endswith('/results'):
                        values=obj[()]
                        if not np.isfinite(values).all():raise RuntimeError('nonfinite tally '+name+path)
                        arrays.append(dict(path=path,shape=list(values.shape),nonzero_elements=int(np.count_nonzero(values)),raw_values=values.tolist()))
                f.visititems(capture)
                if len(arrays)!=3:raise RuntimeError('missing scoring arrays '+name)
            worker=dict(method=name,family=family,completed_histories=20000,counters=counters,
                        geometry_prepare_reuse_or_fit_export_seconds=prep,cold_source_CAD_or_coefficient_build_seconds='UNKNOWN',
                        initialization_seconds=timers['total initialization'],geometry_load_compile_seconds='UNKNOWN separately; nested initialization',
                        transport_seconds=timers['transport'],recorded_statepoint_write_seconds=timers['writing statepoints'],
                        complete_output_finalization_seconds='UNKNOWN separately; external wall contains it',
                        process_wall_seconds=wall,result_validation_seconds=time.monotonic()-audit_start,
                        raw_native_timers_seconds=timers,binary_sha256=sha(exe),library_sha256=sha(lib),preload_sha256=sha(preload)if preload else None,
                        xml_hashes={p.name:sha(p)for p in case.glob('*.xml')},statepoint_sha256=sha(sp),tallies=arrays,raw_failure_diagnostics=failures,
                        fidelity='P00 sampled faceted lineage only; flat-ring proxy differs'if family=='P00'else'same input coefficients; moving-frame versus constant-metric solids not proved identical',
                        promotion='NOT_ACCURACY_ACCEPTED; known old first-root defects remain'if name in ['composite_kernel_old_control','recovered_generic','current_legacy']else'NOT_FULL_TARGET_ACCEPTED')
            save(case/'receipt.json',worker);workers.append(worker)
            save(OUT/'PARTIAL_RESULTS.json',workers)
            log('PASS','20k matched-family worker completed',method=name,transport_seconds=worker['transport_seconds'],process_wall_seconds=wall,evidence=str(case/'receipt.json'))
            print(json.dumps(dict(event='worker_complete',method=name,histories=20000,transport_seconds=worker['transport_seconds'],process_wall_seconds=wall)),flush=True)
        for names in [['p00_facets','p00_flat_rings'],['certified_cache','composite_kernel_old_control','recovered_generic','current_legacy']]:
            for item in ['materials.xml','settings.xml','tallies.xml']:
                if len({sha(OUT/name/item)for name in names})!=1:raise RuntimeError('same-family physics contract mismatch '+item)
        if any(sha(p)!=h for p,h in identities.items()):raise RuntimeError('final frozen identities changed')
        summary=dict(disposition='COMPLETED_MATCHED_WORK_DIAGNOSTICS',workers=workers,
                     family_ratios=dict(P00_facets_to_flat_rings=workers[0]['transport_seconds']/workers[1]['transport_seconds'],
                       cache_to_composite_kernel_old_control=workers[2]['transport_seconds']/workers[3]['transport_seconds']),
                     statistical_equivalence='NOT_CLAIMED',solid_equivalence='NOT_PROVED',fastest_current_production='NOT_ESTABLISHED',
                     builds='NOT_RUN',block_seconds=time.monotonic()-start,independent_acceptance='PENDING')
        save(OUT/'SUMMARY.json',summary);save(OUT/'TERMINAL.json',dict(disposition=summary['disposition'],completed_histories=20000*len(workers),summary_sha256=sha(OUT/'SUMMARY.json'),utc=stamp()))
        log('PASS','fixed no-build block complete; no successor',evidence=str(OUT/'SUMMARY.json'))
    except Exception as e:
        save(OUT/'TERMINAL.json',dict(disposition='FAILED_STOPPED',reason=repr(e),completed_workers=len(workers),completed_histories=20000*len(workers),utc=stamp()))
        log('FAIL','matched method block stopped; no retry',reason_detail=repr(e),evidence=str(OUT));raise
    finally:
        (LOCK/'owner.json').unlink();LOCK.rmdir();log('PASS','lease released after all child exits',owner=owner)

if __name__=='__main__':main()
