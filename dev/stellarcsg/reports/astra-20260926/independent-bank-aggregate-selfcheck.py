"""Bounded negative CLI checks for reusable qualification aggregation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path.cwd()
q = root/'dev/stellarcsg/qualification'
reports = root/'dev/stellarcsg/reports/astra-20260926'
script = q/'aggregate_offset_qualification.py'
baseline = reports/'frozen-offset-03/candidate.jsonl'
fixture = root.parent/'stellarcsg-root-repair-07/dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


history = [reports/'independent-bank-aggregate.py',reports/'independent-bank-qualified-01.json',
           reports/'independent-bank-support-final-01.json',
           reports/'independent-bank-tight-01/receipt.json',baseline]
before = {str(p):sha(p) for p in history}
results = []
with tempfile.TemporaryDirectory(prefix='offset-aggregate-negative-') as temporary:
    folder = Path(temporary)
    bad_json = folder/'duplicate.jsonl'
    lines = baseline.read_text().splitlines()
    lines[0] = lines[0][:-1]+',"kind":"query"}'
    bad_json.write_text('\n'.join(lines)+'\n')
    cases = [
        ('swapped_candidate',reports/'frozen-offset-02/candidate.jsonl',fixture,False,
         'prefix candidate SHA mismatch'),
        ('swapped_source',baseline,q/'recovery04_frozen_bank.csv',False,
         'prefix wistell SHA mismatch'),
        ('optimized_swapped_candidate',reports/'frozen-offset-02/candidate.jsonl',fixture,True,
         'prefix candidate SHA mismatch'),
        ('duplicate_JSON_key',bad_json,fixture,False,'duplicate JSON key: kind')]
    for name,candidate,source,optimized,expected in cases:
        output,support = folder/(name+'.json'),folder/(name+'-support.json')
        command = [sys.executable]+(['-O'] if optimized else [])+[
            str(script),'--candidate',str(candidate),'--prefix-dir',
            str(reports/'independent-bank-tight-01'),'--wistell',str(source),
            '--output',str(output),'--support-output',str(support)]
        child = subprocess.run(command,capture_output=True,text=True,timeout=20)
        passed = child.returncode != 0 and expected in child.stderr and not output.exists() and not support.exists()
        results.append({'case':name,'passed':passed,'exit_code':child.returncode,
                        'expected_error':expected,'output_created':output.exists(),
                        'support_output_created':support.exists(),
                        'observed_error':child.stderr.strip().splitlines()[-1]})
        if not passed:
            raise ValueError('negative CLI check failed: '+name)
after = {str(p):sha(p) for p in history}
if before != after:
    raise ValueError('historical evidence changed during check')
baseline_receipt = json.loads((reports/'aggregate-baseline-recheck-02.json').read_text())
if baseline_receipt['state'] != 'ALL_160_FROZEN_QUERIES_CERTIFIED' or baseline_receipt['query_count'] != 160:
    raise ValueError('baseline recheck missing certification')
report = {'schema':'stellarcsg.reusable-offset-aggregation-check/v1','all_pass':True,
          'reusable_source_sha256':sha(script),'baseline_receipt_sha256':sha(reports/'aggregate-baseline-recheck-02.json'),
          'baseline_query_count':160,'baseline_dispositions':baseline_receipt['candidate_dispositions'],
          'historical_evidence_unchanged':before==after,'historical_hashes':after,'negative_cases':results}
with (reports/'independent-bank-aggregate-selfcheck-02.json').open('x') as stream:
    stream.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
