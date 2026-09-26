"""Read-only hash/receipt/math checks; does not run the production solver."""
from fractions import Fraction as F
import csv
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pairs(items):
    result = {}
    for key,value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def reject(value):
    raise ValueError('nonstandard JSON constant: '+value)


def parse(path):
    return json.loads(Path(path).read_text(),object_pairs_hook=pairs,parse_constant=reject)


def rows(path):
    return [json.loads(line,object_pairs_hook=pairs,parse_constant=reject)
            for line in Path(path).read_text().splitlines()]


root = Path(__file__).resolve().parents[3]
q = root/'dev/stellarcsg/qualification'
r = root/'dev/stellarcsg/reports/astra-20260926'
output = r/'final-acceptance.json'
require(not output.exists(),'acceptance output must be new')
observed = {}


def bind(path,expected=None):
    path = Path(path)
    actual = sha(path)
    if expected is not None:
        require(actual == expected, 'SHA mismatch: '+str(path))
    observed[str(path.relative_to(root)) if path.is_relative_to(root) else str(path)] = actual
    return actual


build = parse(r/'build-receipt-14.json')
bind(r/'build-receipt-14.json')
require(build['exit_code'] == 0 and build['changed_inputs'] == []
        and build['inputs_before'] == build['inputs_after'], 'unstable/failed build')
for section in ('inputs_after','outputs'):
    for path,expected in build[section].items():
        bind(root/path,expected)
for name,expected in (('offset-tests-08.txt','certified_offset_adversarial_controls PASS'),
                      ('legacy-cpp-tests-03.txt','All StellarCSG compiled-surface tests passed')):
    require((r/name).read_text().strip() == expected,'test receipt lacks PASS')
    bind(r/name)
with (q/'recovery04_frozen_bank.csv').open(newline='') as stream:
    bank = list(csv.DictReader(stream))
ids = [item['id'] for item in bank]
require(len(ids)==160 and len(set(ids))==160,'canonical query IDs')
qualified = []
for suffix,prefix_dir,enabled in [('04','independent-bank-accelerated-04',True),
                                  ('05','independent-bank-slab-05',False)]:
    aggregate_path = r/('independent-bank-qualified-'+suffix+'.json')
    aggregate = parse(aggregate_path)
    bind(aggregate_path)
    candidate_path = r/('frozen-offset-'+suffix)/'candidate.jsonl'
    paths = {'bank':q/'recovery04_frozen_bank.csv','candidate':candidate_path,
             'wistell':root.parent/'stellarcsg-root-repair-07/dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5',
             'verifier':q/'verify_offset_bank.py','prefix_receipt':r/prefix_dir/'receipt.json',
             'prefix_queries':r/prefix_dir/'queries.jsonl',
             'support_script':q/'exact_offset_ring_contact_reference.py',
             'aggregation_script':q/'aggregate_offset_qualification.py',
             'fresh_support_reference':r/('independent-bank-support-'+suffix+'.json')}
    require(aggregate['state']=='ALL_160_FROZEN_QUERIES_CERTIFIED'
            and aggregate['query_count']==160
            and aggregate['candidate_dispositions']=={'hit':69,'no_hit':91}
            and aggregate['absolute_distance_error_bound_cm_exact']=='1/100000000000',
            'aggregate claim mismatch')
    require(aggregate['hashes_before']==aggregate['hashes_after'],'aggregate inputs changed')
    for section in ('input_sha256','attachment_sha256','hashes_before'):
        for name,expected in aggregate[section].items():
            bind(paths[name],expected)
    launch_path=r/('frozen-offset-'+suffix)/'launch.json'
    execution_path=r/('frozen-offset-'+suffix)/'receipt.json'
    launch,execution=parse(launch_path),parse(execution_path)
    bind(launch_path);bind(execution_path)
    require(launch['hashes_before']==execution['hashes_after'],'bank execution input changed')
    require(launch['hashes_before']['binary']==build['outputs']['build/astra/stellarcsg_recovery04_bank'],
            'bank executable not final build')
    require(('--no-bernstein-prefix' not in launch['command']) == enabled,'wrong execution mode')
    require(execution['exit_code']==0 and execution['output_valid'] is True
            and execution['candidate_states']=={'PASS':160}
            and execution['dispositions']=={'hit':69,'no_hit':91}
            and execution['bernstein_prefix_enabled'] is enabled,'bank execution mismatch')
    candidate = [x for x in rows(candidate_path) if x.get('kind')=='query']
    proofs=rows(paths['prefix_queries'])
    require([x['id'] for x in candidate]==ids and [x['id'] for x in proofs]==ids,'query order mismatch')
    require({x['id'] for x in proofs if x['state']!='CERTIFIED'}=={'a06','a08'},'unexpected missing proof')
    for claim,proof in zip(candidate,proofs):
        require(claim['candidate_state']=='PASS','candidate blocked')
        if proof['state']=='CERTIFIED':
            require(proof['candidate_disposition']==claim['candidate_disposition'],'disposition mismatch')
            if claim['candidate_disposition']=='hit':
                lo,hi = map(F,proof['bracket'])
                actual=F(claim['candidate_distance'])
                require(lo<=actual<=hi and max(actual-lo,hi-actual)<=F(1,10**11),'root tolerance')
                require(proof['prefix_certified'] is True and proof['after_endpoint_certified'] is True,
                        'incomplete first-root certificate')
    for contact in aggregate['support_contacts']:
        actual=F(next(x for x in candidate if x['id']==contact['id'])['candidate_distance'])
        require(actual==F(contact['candidate_distance_exact_cm']) and actual>0
                and abs(actual-F(contact['exact_first_contact_cm']))<=F(1,10**11),'support contact mismatch')
    qualified.append({'mode':'bernstein_prefix' if enabled else 'ordered_slabs',
                      'aggregate_sha256':sha(aggregate_path),'candidate_sha256':sha(candidate_path),
                      'hits':69,'no_hits':91,'absolute_distance_error_bound_cm_exact':'1/100000000000'})

native_path=r/'native-probe-03.jsonl'
bind(native_path)
native=rows(native_path)
seam=next(x for x in native if x['kind']=='member2_seam')
surface=next(x for x in native if x['kind']=='native_surface')
region=next(x for x in native if x['kind']=='native_csg_region')
controls=next(x for x in native if x['kind']=='controls')
require(seam['found'] is True and seam['unresolved'] is False and controls['state']=='PASS'
        and surface['state']=='PASS' and region['state']=='PASS'
        and region['entry_signed_surface']==-1 and region['exit_signed_surface']==1,
        'native smoke failed')
entry=F(surface['distance_cm'])
require(entry==F(seam['distance_cm'])==F(region['entry_cm']),'native entry mismatch')
entry_reference=parse(r/'exact-seam-reference-native-03.json')
exit_reference=parse(r/'independent-native-region-exit.json')
bind(r/'exact-seam-reference-native-03.json');bind(r/'independent-native-region-exit.json')
bind(root.parent/'stellarcsg-local-continuation-20260925/dev/stellarcsg/qualified/analytic_swept_coils.h5',
     exit_reference['h5_sha256'])
bind(r/'native-probe-02.jsonl',exit_reference['entry_probe_sha256'])
bind(q/'exact_native_region_exit_reference.py',exit_reference['script_sha256'])
bind(q/'exact_offset_seam_reference.py',exit_reference['seam_helper_sha256'])
require(entry==F(entry_reference['observed_distance_acceptance']['observed_binary64_distance_exact']['rational']),
        'reference entry origin changed')
new_origin=F.from_float(550.0-float(entry))
require(new_origin==F(exit_reference['origin_exact'][0]['rational']),'next-exit origin changed')
exit_distance=F(region['exit_after_coincident_entry_cm'])
left,right=[F(x['rational']) for x in exit_reference['first_exit_enclosure_exact']]
exit_error=max(abs(exit_distance-left),abs(exit_distance-right))
require(exit_error<=F(1,10**11),'native exit independent distance error')
entry_lo,entry_hi=[F(x['rational']) for x in entry_reference['first_boundary_enclosure']]
entry_error=max(abs(entry-entry_lo),abs(entry-entry_hi))
require(entry_error<=F(1,10**11),'native entry independent distance error')
report={
    'schema':'stellarcsg.independent-final-offset-acceptance/v1',
    'state':'NARROW_CHANGED_GEOMETRY_MILESTONES_ACCEPTED',
    'build_receipt':'build-receipt-14.json','all_live_build_inputs_and_outputs_match':True,
    'checked_build_input_count':len(build['inputs_after']),
    'checked_build_output_count':len(build['outputs']),
    'qualified_frozen_modes':qualified,
    'native_region':{'entry_exact':str(entry),'exit_exact':str(exit_distance),
                     'entry_worst_error_exact':str(entry_error),'exit_worst_error_exact':str(exit_error),
                     'entry_signed_surface':-1,'exit_signed_surface':1,
                     'normal_sense_contains_crossing_smoke':'PASS','particle_transport':False},
    'tests':{'offset_adversarial':'PASS','legacy_cpp':'PASS'},
    'performance':'NOT_ACCEPTED_BY_THIS_REVIEW',
    'observed_artifact_sha256':observed,
    'verification_script_sha256':sha(__file__),
    'claim_boundary':'Only recorded exact_control_offset subset/source mechanism, two unchanged 160-query scalar qualifications, legacy regression tests and one native Region entry/exit smoke. No physical varying-frame coil, universal solver, particle histories, tangent tracking, full-normal coverage, legacy equivalence or performance claim. Hash-bound receipts are execution observations, not cryptographic compilation attestation.'
}
with output.open('x') as stream:
    stream.write(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'state':report['state'],'build_inputs':len(build['inputs_after']),
                  'build_outputs':len(build['outputs']),'exit_worst_error_exact':str(exit_error)}))
