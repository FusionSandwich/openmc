"""Run attempt 0003; output and frozen source are created once, never replaced."""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import shutil
import sys
import time
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))

import numpy as np
import scipy

from direct_algebraic import (DirectFourier, IncumbentBicubic, LocalQuartic,
                              field_jet, normal, position, query_candidates)
from patch_methods import polynomial_design


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,data):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def benchmark_evaluation(profiles,target):
    rng=np.random.default_rng(3057)
    t=rng.uniform(0,2*np.pi,4096);p=rng.uniform(0,2*np.pi,4096)
    points=position(target,t,p)+rng.uniform(-.03,.03,(4096,1))*normal(target,position(target,t,p))
    results={name:{'batch_4096_seconds':[],'scalar_128_seconds':[]} for name in profiles}
    names=list(profiles)
    for repeat in range(3):
        for name in names[repeat:]+names[:repeat]:
            model=profiles[name];field_jet(model,points[:8])
            begin=time.perf_counter();value,grad=field_jet(model,points)
            results[name]['batch_4096_seconds'].append(time.perf_counter()-begin)
            begin=time.perf_counter()
            for point in points[:128]:field_jet(model,point)
            results[name]['scalar_128_seconds'].append(time.perf_counter()-begin)
            results[name]['batch_checksum']=float(np.sum(value)+np.sum(grad))
    return {'models':results,'repeats':3,'same_cartesian_points':True,'includes_field_and_gradient':True,
            'not_native_query_or_transport_throughput':True,'points_sha256':hashlib.sha256(points.tobytes()).hexdigest()}


def make_bank(target):
    prior=ROOT/'attempts/0002-patch-hybrid-20261009/run-001/rays.json'
    bank=json.loads(prior.read_text())
    for ray in bank:ray['reference_first_distance_m']=None;ray['reference_status']='UNQUALIFIED_GENERIC'
    for i in range(24):
        theta=.13+2*np.pi*i/24;phi=.07+2*np.pi*((i*7)%24)/24
        u=np.array([np.cos(theta)*np.cos(phi),np.cos(theta)*np.sin(phi),np.sin(theta)])
        axis=np.array([5*np.cos(phi),5*np.sin(phi),0.])
        bank.append({'id':f'known-radial-{i:02}','origin_m':(axis+2*u).tolist(),'direction':(-u).tolist(),
                     'reference_first_distance_m':float(2-target.radius(theta,phi)[0]),
                     'reference_status':'EXACT_RADIAL_CHART_FIRST_CROSSING'})
    return bank


def direct_study(out):
    target=DirectFourier()
    models={'direct_fourier':target}
    construction=[]
    for nt,np_ in [(8,12),(16,24),(32,48)]:
        begin=time.perf_counter();model=IncumbentBicubic(target,nt,np_)
        name=f'incumbent_bicubic_{nt}x{np_}';models[name]=model
        construction.append({'model':name,'construction_seconds':time.perf_counter()-begin,
                             'radius_coefficient_bytes':model.coefficients.nbytes})
    t,p=np.meshgrid((np.arange(65)+.37)*2*np.pi/65,(np.arange(73)+.41)*2*np.pi/73,indexing='ij')
    exact=position(target,t,p);nexact=normal(target,exact)
    fidelity=[]
    for name,model in models.items():
        fitted=position(model,t,p)
        error=np.linalg.norm(fitted-exact,axis=-1)
        n=normal(model,fitted)
        fidelity.append({'model':name,'sample_count':error.size,'max_same_parameter_error_m':float(error.max()),
                         'rms_same_parameter_error_m':float(np.sqrt(np.mean(error**2))),
                         'max_normal_error_deg':float(np.degrees(np.arccos(np.clip(np.sum(n*nexact,axis=-1),-1,1))).max()),
                         'certified_fidelity':False})
    bank=make_bank(target);save(out/'rays.json',bank)
    timings={name:[] for name in models};rows=[];names=list(models)
    for repeat in range(3):
        for name in names[repeat:]+names[:repeat]:
            begin=time.perf_counter()
            for ray in bank:
                result=query_candidates(models[name],ray['origin_m'],ray['direction'])
                if repeat==0:
                    ref=ray['reference_first_distance_m'];candidate=result['candidate_distance_m']
                    rows.append({'model':name,'ray_id':ray['id'],'reference_first_distance_m':ref,
                                 'candidate_error_vs_target_m':None if ref is None or candidate is None else abs(ref-candidate),**result})
            timings[name].append(time.perf_counter()-begin)
        print(f'direct bank repeat {repeat+1}/3 complete',flush=True)
    tangent_theta,tangent_phi=.3,.2
    circle=DirectFourier(circular=True)
    tangent=np.array([-np.sin(tangent_theta)*np.cos(tangent_phi),-np.sin(tangent_theta)*np.sin(tangent_phi),np.cos(tangent_theta)])
    origin=position(circle,tangent_theta,tangent_phi)-1.234*tangent
    tangent_control={'origin_m':origin.tolist(),'direction':tangent.tolist(),'reference_t_m':1.234,
                     'result':query_candidates(circle,origin,tangent,ceiling=2,samples=33)}
    save(out/'direct_fourier_results.json',{'target':{'major_radius_m':5,'m':[0,2,1],'stored_n':[0,3,-6],
                'cos_coefficients_m':target.c.tolist(),'sin_coefficients_m':target.s.tolist(),
                'positive_radius_bound_m':[.655,.945],'geometric_theta_not_raw_vmec_theta':True},
                'construction':construction,'fidelity':fidelity,'evaluation_cost':benchmark_evaluation(models,target),
                'diagnostic_query_bank_seconds':timings,'query_count_per_model':len(bank),'repeats':3,
                'query_rows':rows,'tangent_control':tangent_control,'native_speed_goal_status':'UNMEASURED',
                'scope':'Frozen incumbent radius evaluator in common constant-axis wrapper; not full incumbent tracker or native C++ comparison'})


def quartic_atlas(nt,np_):
    target=DirectFourier();wt=2*np.pi/nt;wp=(2*np.pi/3)/np_
    patches={};errors=[];angles=[];failures=0;multiroots=0;bad_signs=0;ranks=[];conditions=[]
    records=[];rng=np.random.default_rng(4410);start=time.perf_counter()
    for i in range(nt):
        for j in range(np_):
            theta=(i+.5)*wt;phi=(j+.5)*wp
            patch=LocalQuartic.fit(target,theta,phi,wt/2,wp/2);patches[i,j]=patch
            ranks.append(patch.rank);conditions.append(patch.condition)
            records.append({'i':i,'j':j,'center_m':patch.center.tolist(),'frame':patch.frame.tolist(),
                            'scale_m':patch.scale,'coefficients':patch.coefficients.tolist(),
                            'rank':patch.rank,'condition':patch.condition})
            for _ in range(9):
                t=theta+rng.uniform(-wt/2,wt/2);p=phi+rng.uniform(-wp/2,wp/2)
                point=position(target,t,p);n=normal(target,point)
                q,qn,count=patch.project_along(point,n)
                multiroots+=count>1
                if q is None:failures+=1;continue
                errors.append(float(np.linalg.norm(q-point)))
                angles.append(float(np.degrees(np.arccos(np.clip(qn@n,-1,1)))))
                for offset in (-.02,.02):
                    cloud=(point+offset*patch.scale*n-patch.center)@patch.frame/patch.scale
                    value=(polynomial_design(cloud[None,:])@patch.coefficients).item()
                    bad_signs+=value*offset<=0
    gaps=[];seam_failures=0
    for (i,j),patch in patches.items():
        # Interior edges only; periodic edges require rotated neighbors and
        # remain explicitly unassessed rather than pretending they were tested.
        for key,t,p in [((i+1,j),(i+1)*wt,(j+.5)*wp),((i,j+1),(i+.5)*wt,(j+1)*wp)]:
            neighbor=patches.get(key)
            if neighbor is None:continue
            point=position(target,t,p);n=normal(target,point)
            a,_,_=patch.project_along(point,n);b,_,_=neighbor.project_along(point,n)
            if a is None or b is None:seam_failures+=1
            else:gaps.append(float(np.linalg.norm(a-b)))
    controls=[]
    for key in list(patches)[::max(1,len(patches)//12)]:
        patch=patches[key];point=position(target,patch.theta,patch.phi);n=normal(target,point)
        o=point+.05*n;result=patch.trimmed_ray_candidates(o,-n,ceiling=.1)
        controls.append({'patch':list(key),'reference_target_contact_m':.05,'origin_m':o.tolist(),
                         'direction':(-n).tolist(),**result})
    return {'theta_patches':nt,'phi_patches_one_period':np_,'patch_count':len(patches),
            'coefficient_count_per_patch':35,'min_rank':min(ranks),'max_rank':max(ranks),
            'max_design_condition':max(conditions),'holdout_sample_count':9*len(patches),
            'projection_failures':failures,'multiple_normal_line_candidates':multiroots,
            'max_sampled_normal_line_error_m':max(errors) if errors else None,
            'max_sampled_normal_error_deg':max(angles) if angles else None,
            'offset_sign_failures':bad_signs,'interior_midpoint_seam_sample_count':len(gaps),
            'max_sampled_interior_midpoint_seam_gap_m':max(gaps) if gaps else None,
            'seam_projection_failures':seam_failures,'periodic_seams_assessed':False,
            'construction_and_diagnostic_seconds':time.perf_counter()-start,'patch_records':records,
            'trimmed_local_ray_controls':controls,'closed_solid':False,'whole_domain_fidelity':False,
            'first_root_complete':False,'verdict':'LOCAL_FIT_DIAGNOSTICS_ONLY'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);args=parser.parse_args()
    if not re.fullmatch(r'run-\d{3}',args.run_id):parser.error('use run-NNN')
    attempt=ROOT/'attempts/0003-direct-fourier-algebraic-20261009';out=attempt/args.run_id
    out.mkdir(exist_ok=False);(out/'source').mkdir()
    sources=[ROOT/'fourier_torus.py',ROOT/'test_fourier_torus.py',HERE/'patch_methods.py',HERE/'test_patch_methods.py',
             HERE/'direct_algebraic.py',HERE/'test_direct_algebraic.py',Path(__file__)]
    for p in sources:shutil.copyfile(p,out/'source'/p.name)
    manifest=json.loads((attempt/'input_manifest.json').read_text())
    prior_changed=[name for name,h in manifest['prior_files_to_preserve'].items() if sha(ROOT/name)!=h]
    if prior_changed:raise RuntimeError(f'Prior files changed: {prior_changed}')
    suite=unittest.TestSuite()
    for folder,pattern in [(ROOT,'test_fourier_torus.py'),(HERE,'test_patch_methods.py'),(HERE,'test_direct_algebraic.py')]:
        suite.addTests(unittest.defaultTestLoader.discover(str(folder),pattern=pattern))
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (out/'tests.txt').write_text(log.getvalue(),encoding='utf-8')
    if not result.wasSuccessful():
        save(out/'failure.json',{'status':'FAILED_CONTROLS','tests':result.testsRun});raise SystemExit(1)
    direct_study(out)
    atlases=[]
    for nt,np_ in [(8,12),(16,24)]:
        atlases.append(quartic_atlas(nt,np_));print(f'quartic atlas {nt}x{np_} complete',flush=True)
    save(out/'local_quartic_results.json',atlases)
    save(out/'receipt.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'run_id':args.run_id,
         'status':'COMPLETED_SYNTHETIC_DIAGNOSTICS','tests_passed':result.testsRun,
         'runtime':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
         'source_hashes':{p.name:sha(p) for p in sources},
         'input_hashes':{name:sha(attempt/'inputs'/name) for name in manifest['inputs']},
         'output_hashes':{p.name:sha(p) for p in out.iterdir() if p.is_file()},
         'prior_files_unchanged':len(manifest['prior_files_to_preserve']),
         'native_build':False,'transport':False,'physical_fidelity_acceptance':False,'native_speed_acceptance':False})
    print(f'{result.testsRun} controls pass; receipt: {out}',flush=True)


if __name__=='__main__':main()
