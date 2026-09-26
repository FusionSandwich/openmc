"""Bind 158 exact prefix proofs and two freshly executed exact support proofs."""
from fractions import Fraction as F
import csv
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys

resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
root = Path.cwd()
out = root/'dev/stellarcsg/reports/astra-20260926'
qualification = root/'dev/stellarcsg/qualification'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pairs(items):
    result = {}
    for k,v in items:
        if k in result:
            raise ValueError('duplicate key '+k)
        result[k] = v
    return result


def reject(x):
    raise ValueError('nonstandard JSON '+x)


def parse(text):
    return json.loads(text,object_pairs_hook=pairs,parse_constant=reject)


support_script = qualification/'exact_offset_ring_contact_reference.py'
support_output = out/'independent-bank-support-final-01.json'
command = [sys.executable,str(support_script),'--bank',
           str(qualification/'recovery04_frozen_bank.csv'),'--output',str(support_output)]
child = subprocess.run(command,check=True,capture_output=True,text=True,timeout=30)
prefix_path = out/'independent-bank-tight-01/receipt.json'
prefix = parse(prefix_path.read_text())
proof_path = out/'independent-bank-tight-01/queries.jsonl'
proofs = [parse(line) for line in proof_path.read_text().splitlines()]
support = parse(support_output.read_text())
candidate_path = out/'frozen-offset-03/candidate.jsonl'
candidate_rows = [parse(line) for line in candidate_path.read_text().splitlines()]
candidates = {r['id']:r for r in candidate_rows if r.get('kind') == 'query'}
bank_path = qualification/'recovery04_frozen_bank.csv'
with bank_path.open(newline='') as stream:
    bank = list(csv.DictReader(stream))
frozen_ids = [r['id'] for r in bank]
assert len(frozen_ids) == 160 and len(set(frozen_ids)) == 160
assert [r['id'] for r in proofs] == frozen_ids
assert list(candidates) == frozen_ids
assert prefix['hashes_before'] == prefix['hashes_after']
assert prefix['hashes_before']['bank'] == sha(bank_path) == support['bank_sha256']
assert prefix['hashes_before']['candidate'] == sha(candidate_path)
assert prefix['hashes_before']['verifier'] == sha(qualification/'verify_offset_bank.py')
fixture = root.parent/'stellarcsg-root-repair-07/dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5'
assert prefix['hashes_before']['wistell'] == sha(fixture)
assert prefix['states'] == {'CERTIFIED':158,'UNKNOWN':2}
assert {r['id'] for r in proofs if r['state'] != 'CERTIFIED'} == {'a06','a08'}
assert support['state'] == 'EXACT_SUPPORT_CONTACTS_CERTIFIED'
assert support['script_sha256'] == sha(support_script)
assert support['generated_payload_fnv'] == prefix['geometry_identities']['torus']['fnv']
assert support['generated_payload_sha256'] == prefix['geometry_identities']['torus']['payload_sha256']
assert {c['id'] for c in support['certificates']} == {'a06','a08'}
tol = F(1,10**11)
contacts = []
for proof in support['certificates']:
    query = candidates[proof['id']]
    frozen = next(row for row in bank if row['id'] == proof['id'])
    assert query['candidate_disposition'] == 'hit' and query['candidate_found'] is True
    assert query['candidate_state'] == 'PASS'
    assert query['coefficient_hash'] == support['generated_payload_fnv']
    assert [F(x['rational']) for x in proof['origin_exact']] == [F(float(frozen['o'+a])) for a in 'xyz']
    assert [F(x['rational']) for x in proof['direction_exact']] == [F(x) for x in query['normalized_direction']]
    assert type(query['candidate_distance']) in (float,int)
    exact = F(proof['first_eligible_unsuppressed_contact']['t_exact']['rational'])
    actual = F(query['candidate_distance'])
    assert exact > 0 and actual > 0
    error = abs(exact-actual)
    assert error <= tol
    contacts.append({'id':proof['id'],'exact_first_contact_cm':str(exact),
                     'candidate_distance_exact_cm':str(actual),
                     'distance_error_exact_cm':str(error),'state':'CERTIFIED'})
for proof in proofs:
    if proof['state'] != 'CERTIFIED':
        continue
    if proof['candidate_disposition'] == 'hit':
        l,h = [F(x) for x in proof['bracket']]
        t = F(candidates[proof['id']]['candidate_distance'])
        assert max(t-l,h-t) <= tol
        assert proof['prefix_certified'] is True and proof['after_endpoint_certified'] is True
    else:
        assert proof['candidate_disposition'] == 'no_hit'
        assert candidates[proof['id']]['candidate_found'] is False

report = {'schema':'stellarcsg.independent-offset-frozen-bank-qualification/v1',
          'state':'ALL_160_FROZEN_QUERIES_CERTIFIED',
          'query_count':160,'exact_Bernstein_or_fixed_ball_certificates':158,
          'exact_global_support_contact_certificates':2,
          'absolute_distance_error_bound_cm_exact':str(tol),
          'absolute_distance_error_bound_cm':1e-11,
          'candidate_dispositions':{'hit':sum(q['candidate_disposition']=='hit' for q in candidates.values()),
                                    'no_hit':sum(q['candidate_disposition']=='no_hit' for q in candidates.values())},
          'input_sha256':prefix['hashes_before'],
          'attachment_sha256':{'prefix_receipt':sha(prefix_path),'prefix_queries':sha(proof_path),
                               'fresh_support_reference':sha(support_output),
                               'support_script':sha(support_script),'aggregation_script':sha(__file__)},
          'support_reexecution':{'command':command,'exit_code':child.returncode,
                                 'stdout':child.stdout.strip()},
          'geometry_identities':prefix['geometry_identities'],'support_contacts':contacts,
          'claim_boundary':'Only these 160 unchanged frozen queries for the exact mathematical cardinal cubic of FNV-checked original binary64 controls and original isotropic radii, using the exported binary64 normalized ray components. Every hit has an independently proved first eligible boundary within 1e-11 cm; every no-hit excludes the complete eligible ray. No universal solver, legacy representation, transport acceptance, or matched performance claim.'}
path = out/'independent-bank-qualified-01.json'
if path.exists():
    raise ValueError('aggregation output already exists')
path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({'state':report['state'],'bound_cm_exact':str(tol),
                  'contacts':contacts,'output':str(path)},allow_nan=False))
