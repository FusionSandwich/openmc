"""Bind unchanged frozen rays to exact prefix and fresh support certificates.

This aggregates existing proofs; it never invokes the production solver or the
full prefix verifier. All acceptance guards remain active under Python -O.
"""
import argparse
from collections import Counter
import csv
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys


EXPECTED_BANK = 'fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723'
TOLERANCE = F(1, 10**11)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key: '+key)
        result[key] = value
    return result


def reject(value):
    raise ValueError('nonstandard JSON constant: '+value)


def parse(text):
    value = json.loads(text, object_pairs_hook=pairs, parse_constant=reject)
    require(isinstance(value, dict), 'JSON record must be an object')
    return value


def jsonl(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    require(all(line.strip() for line in lines), 'blank JSONL record')
    return [parse(line) for line in lines]


def numeric(value):
    return type(value) in (float, int) and math.isfinite(value)


def aggregate(args):
    qualification = Path(__file__).resolve().parent
    support_script = qualification/'exact_offset_ring_contact_reference.py'
    verifier_script = qualification/'verify_offset_bank.py'
    prefix_path = args.prefix_dir/'receipt.json'
    proof_path = args.prefix_dir/'queries.jsonl'
    require(not args.output.exists(), 'qualification output already exists')
    require(not args.support_output.exists(), 'support output already exists')
    require(args.output.resolve() != args.support_output.resolve(), 'outputs must differ')
    paths = {'bank': args.bank, 'candidate': args.candidate,
             'wistell': args.wistell, 'verifier': verifier_script,
             'prefix_receipt': prefix_path, 'prefix_queries': proof_path,
             'support_script': support_script, 'aggregation_script': Path(__file__)}
    before = {name: sha(path) for name, path in paths.items()}
    require(before['bank'] == EXPECTED_BANK, 'frozen bank SHA mismatch')
    prefix = parse(prefix_path.read_text())
    proofs = jsonl(proof_path)
    candidate_rows = jsonl(args.candidate)
    queries = [r for r in candidate_rows if r.get('kind') == 'query']
    summaries = [r for r in candidate_rows if r.get('kind') == 'summary']
    with args.bank.open(newline='', encoding='utf-8') as stream:
        bank = list(csv.DictReader(stream))
    frozen_ids = [r['id'] for r in bank]
    require(len(frozen_ids) == 160 and len(set(frozen_ids)) == 160,
            'frozen bank count/unique IDs mismatch')
    require(len(candidate_rows) == 161 and len(summaries) == 1 and
            [r.get('id') for r in queries] == frozen_ids,
            'candidate count/order/unique IDs mismatch')
    require([r.get('id') for r in proofs] == frozen_ids,
            'prefix proof count/order/unique IDs mismatch')
    require(prefix.get('hashes_before') == prefix.get('hashes_after'),
            'prefix inputs changed during proof execution')
    for name in ('bank', 'candidate', 'wistell', 'verifier'):
        require(prefix['hashes_before'].get(name) == before[name],
                'prefix '+name+' SHA mismatch')
    require(prefix.get('states') == {'CERTIFIED': 158, 'UNKNOWN': 2} and
            dict(Counter(r.get('state') for r in proofs)) == prefix['states'],
            'prefix receipt/row certification counts mismatch')
    require({r['id'] for r in proofs if r['state'] != 'CERTIFIED'} == {'a06', 'a08'},
            'unsupported UNKNOWN cases outside exact support contacts')
    candidates = {r['id']: r for r in queries}
    for frozen, query in zip(bank, queries):
        require(query.get('geometry_representation') == 'exact_control_offset',
                'candidate representation mismatch')
        require(query.get('candidate_state') == 'PASS', 'candidate is not resolved PASS')
        require(query.get('coefficient_hash') == frozen['coefficient_hash'] and
                query.get('source_sha256') == frozen['source_sha256'],
                'candidate coefficient/source association mismatch')
        require(prefix['geometry_identities'][frozen['geometry']]['fnv'] ==
                frozen['coefficient_hash'], 'prefix coefficient association mismatch')
        origin, direction = query.get('ray_origin'), query.get('normalized_direction')
        require(isinstance(origin, list) and len(origin) == 3 and all(map(numeric, origin)),
                'invalid exported origin')
        require(isinstance(direction, list) and len(direction) == 3 and all(map(numeric, direction)),
                'invalid exported normalized direction')
        require([F(x) for x in origin] == [F(float(frozen['o'+a])) for a in 'xyz'],
                'exported origin differs from frozen ray')
        disposition = query.get('candidate_disposition')
        require(disposition in ('hit', 'no_hit'), 'invalid candidate disposition')
        if disposition == 'hit':
            require(query.get('candidate_found') is True and
                    numeric(query.get('candidate_distance')) and query['candidate_distance'] >= 0,
                    'candidate hit fields inconsistent')
        else:
            require(query.get('candidate_found') is False and query.get('candidate_distance') is None,
                    'candidate no-hit fields inconsistent')
    require(type(summaries[0].get('query_count')) is int and summaries[0]['query_count'] == 160 and
            type(summaries[0].get('blocked')) is int and summaries[0]['blocked'] == 0 and
            type(summaries[0].get('candidate_failures')) is int and summaries[0]['candidate_failures'] == 0,
            'candidate summary counts inconsistent')
    for proof in proofs:
        if proof['state'] != 'CERTIFIED':
            continue
        query = candidates[proof['id']]
        require(proof.get('candidate_disposition') == query['candidate_disposition'],
                'prefix/candidate disposition mismatch')
        if proof['candidate_disposition'] == 'hit':
            require(len(proof['bracket']) == 2, 'invalid root bracket')
            left, right = [F(x) for x in proof['bracket']]
            actual = F(query['candidate_distance'])
            require(left <= actual <= right and max(actual-left, right-actual) <= TOLERANCE,
                    'root bracket fails declared tolerance')
            require(proof.get('prefix_certified') is True and
                    proof.get('after_endpoint_certified') is True,
                    'hit prefix or endpoint not certified')

    command = [sys.executable, str(support_script), '--bank', str(args.bank),
               '--output', str(args.support_output)]
    child = subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
    support = parse(args.support_output.read_text())
    require(support.get('state') == 'EXACT_SUPPORT_CONTACTS_CERTIFIED',
            'fresh support reference is not certified')
    require(support.get('bank_sha256') == before['bank'] and
            support.get('script_sha256') == before['support_script'],
            'support bank/source SHA mismatch')
    torus = prefix['geometry_identities']['torus']
    require(support.get('generated_payload_fnv') == torus['fnv'] and
            support.get('generated_payload_sha256') == torus['payload_sha256'],
            'support/prefix ring payload identity mismatch')
    require(len(support['certificates']) == 2 and
            {c['id'] for c in support['certificates']} == {'a06', 'a08'},
            'support contact IDs/count mismatch')
    contacts = []
    for proof in support['certificates']:
        query = candidates[proof['id']]
        require(query['candidate_disposition'] == 'hit', 'support candidate is not a hit')
        require(query['coefficient_hash'] == torus['fnv'], 'support coefficient mismatch')
        require([F(x['rational']) for x in proof['origin_exact']] ==
                [F(x) for x in query['ray_origin']], 'support origin mismatch')
        require([F(x['rational']) for x in proof['direction_exact']] ==
                [F(x) for x in query['normalized_direction']], 'support direction mismatch')
        exact = F(proof['first_eligible_unsuppressed_contact']['t_exact']['rational'])
        actual = F(query['candidate_distance'])
        require(exact > 0 and actual > 0, 'support first contact must be positive')
        error = abs(exact-actual)
        require(error <= TOLERANCE, 'support contact fails declared distance tolerance')
        contacts.append({'id': proof['id'], 'exact_first_contact_cm': str(exact),
                         'candidate_distance_exact_cm': str(actual),
                         'distance_error_exact_cm': str(error), 'state': 'CERTIFIED'})
    after = {name: sha(path) for name, path in paths.items()}
    require(before == after, 'aggregation inputs changed during execution')
    report = {
        'schema': 'stellarcsg.independent-offset-frozen-bank-qualification/v1',
        'state': 'ALL_160_FROZEN_QUERIES_CERTIFIED', 'query_count': 160,
        'exact_Bernstein_or_fixed_ball_certificates': 158,
        'exact_global_support_contact_certificates': 2,
        'absolute_distance_error_bound_cm_exact': str(TOLERANCE),
        'absolute_distance_error_bound_cm': float(TOLERANCE),
        'candidate_dispositions': dict(Counter(q['candidate_disposition'] for q in queries)),
        'input_sha256': {name: before[name] for name in ('bank', 'candidate', 'wistell', 'verifier')},
        'hashes_before': before, 'hashes_after': after,
        'attachment_sha256': {**{name: before[name] for name in
            ('prefix_receipt', 'prefix_queries', 'support_script', 'aggregation_script')},
            'fresh_support_reference': sha(args.support_output)},
        'aggregation_script_sha256': before['aggregation_script'],
        'support_reexecution': {'command': command, 'exit_code': child.returncode,
                               'stdout': child.stdout.strip()},
        'geometry_identities': prefix['geometry_identities'], 'support_contacts': contacts,
        'claim_boundary': 'Only these 160 unchanged frozen queries for the exact mathematical cardinal cubic of FNV-checked original binary64 controls and original isotropic radii, using the exported binary64 normalized ray components. Every hit has an independently proved first eligible boundary within 1e-11 cm; every no-hit excludes the complete eligible ray. No universal solver, legacy representation, transport acceptance, or matched performance claim.'}
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--prefix-dir', type=Path, required=True)
    parser.add_argument('--wistell', type=Path, required=True)
    parser.add_argument('--support-output', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bank', type=Path,
                        default=Path(__file__).resolve().with_name('recovery04_frozen_bank.csv'))
    args = parser.parse_args()
    report = aggregate(args)
    print(json.dumps({key: report[key] for key in
                      ('state', 'query_count', 'candidate_dispositions')}, allow_nan=False))


if __name__ == '__main__':
    main()
