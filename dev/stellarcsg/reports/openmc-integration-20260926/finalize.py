"""Bind final local evidence and stage only explicitly selected text artifacts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[4]
report = Path(__file__).resolve().parent
rel = lambda p: Path(p).relative_to(root).as_posix()
sha = lambda data: hashlib.sha256(data).hexdigest()
run = lambda *args: subprocess.run(args, cwd=root, capture_output=True, check=True).stdout
source_names = [
    '.gitattributes', 'src/mesh.cpp',
    'dev/stellarcsg/python/stellarcsg/openmc_tally.py',
    'dev/stellarcsg/python/stellarcsg/plasma_source.py',
    'dev/stellarcsg/tests/test_local_tally_api.py',
    'dev/stellarcsg/tests/test_plasma_source_handoff.py',
    'dev/stellarcsg/docs/OPENMC_INTEGRATION.md',
    'dev/stellarcsg/docs/PLASMA_SOURCE_HANDOFF.md',
] + ['dev/stellarcsg/qualification/' + name for name in (
    'audit_openmc_integration.py', 'build_integration_probe.py',
    'check_openmc_integration.py', 'check_spherical_equator.cpp',
    'check_spherical_partial_indices.cpp', 'run_openmc_integration.py',
    'test_integration_artifact_controls.py')]

if sys.argv[1] == 'accept':
    after = json.loads((report/'comparison-after.json').read_text())
    before = json.loads((report/'comparison-before.json').read_text())
    negative = json.loads((report/'negative-controls.json').read_text())
    assert before['state'] == 'SPATIAL_TALLY_REGRESSION_DETECTED'
    assert after['state'] == 'SAMPLED_INTEGRATION_AGREEMENT'
    assert all(t['sampled_agreement'] for p in after['pairs'] for t in p['tallies'])
    assert len(negative['controls']) == 14
    assert all(c['state'] == 'REJECTED' for c in negative['controls'])
    native = json.loads((report/'native-after/receipt.json').read_text())
    expected = native['new_library_sha256']
    assert expected == 'f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6'
    assert sha((root/'openmc/lib/libopenmc.so').read_bytes()) == expected
    assert sha((root/'build/astra-native/lib/libopenmc.so').read_bytes()) == expected
    artifacts = [report/name for name in (
        'comparison-before.json', 'comparison-after.json', 'negative-controls.json',
        'unit-tests-02.txt', 'REVIEW.md', 'RESULTS.md', 'CONTINUATION_HANDOFF.md',
        'native-before/receipt.json', 'native-before/probe.txt',
        'native-after/receipt.json', 'native-after/probe.txt',
        'native-partial-02/receipt.json', 'native-partial-02/probe.txt',
        'preflight.json', 'prebuild-windows.json', 'prebuild-wsl.json',
        'prepartial-windows.json', 'prepartial-wsl.json',
        'repaired/campaign-plan.json', 'repaired/campaign-progress.json')]
    value = dict(state='ACCEPTED_FINITE_INTEGRATION_MILESTONE',
        previous_head=run('git', 'rev-parse', 'HEAD').decode().strip(),
        library_sha256=expected, runs=6, plasma_tally_comparisons=37,
        approximate_coil_tally_comparisons=18, python_tests=18, python_subtests=17,
        native_equator_checks=37, partial_point_index_checks=18,
        corrupt_artifact_rejections=14,
        artifacts={rel(p): sha(p.read_bytes()) for p in artifacts},
        source_raw_sha256={name: sha((root/name).read_bytes()) for name in source_names},
        limitations=['Physical plasma source not admitted', 'Partial-angle ray traversal unqualified',
            'Universal OpenMC compatibility unqualified', 'Full spectrum/device DPA unqualified',
            'Native speed goal unmet', 'Upstream readiness not established'])
    with (report/'acceptance.json').open('x') as handle:
        json.dump(value, handle, indent=2)
elif sys.argv[1] == 'stage':
    files = [root/name for name in source_names]
    files += sorted(p for p in report.rglob('*') if p.is_file()
                    and p.name != 'publication.json'
                    and (p.name == '.gitignore'
                         or p.suffix in {'.json', '.md', '.txt', '.py', '.xml', '.csv'}))
    run('git', 'add', '-f', '--', *map(rel, files))
    records = []
    for p in files:
        raw = p.read_bytes()
        blob = run('git', 'show', ':' + rel(p))
        assert blob == raw or blob == raw.replace(b'\r\n', b'\n'), rel(p)
        if p.is_relative_to(report):
            assert blob == raw, 'Raw evidence line endings changed: ' + rel(p)
        records.append(dict(path=rel(p), raw_sha256=sha(raw), staged_sha256=sha(blob),
                            bytes=len(blob), line_endings_only=raw != blob))
    value = dict(state='STAGED_BYTES_VERIFIED', files=records,
                 note='Report bytes preserved exactly; source differences limited to CRLF normalization. This receipt cannot include its own hash.')
    (report/'publication.json').write_text(json.dumps(value, indent=2)+'\n')
    run('git', 'add', '-f', '--', rel(report/'publication.json'))
    print(json.dumps(dict(state=value['state'], files=len(records)+1,
                         total_bytes=sum(r['bytes'] for r in records))))
elif sys.argv[1] == 'verify':
    value = json.loads((report/'publication.json').read_text())
    for row in value['files']:
        assert sha((root/row['path']).read_bytes()) == row['raw_sha256'], row['path']
        assert sha(run('git', 'show', 'HEAD:' + row['path'])) == row['staged_sha256'], row['path']
    assert run('git', 'show', 'HEAD:' + rel(report/'publication.json')) == (report/'publication.json').read_bytes()
    print(json.dumps(dict(state='COMMITTED_BYTES_VERIFIED', files=len(value['files'])+1)))
else:
    raise SystemExit('Expected accept, stage or verify')
