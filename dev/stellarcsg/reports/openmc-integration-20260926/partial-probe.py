"""Local inventory, then separately bounded compile of supplemental assertions."""
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys

root = Path.cwd()
report = root / 'dev/stellarcsg/reports/openmc-integration-20260926'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sys.argv[1] == 'inventory':
    old = json.loads((report / 'prebuild-wsl.json').read_text())
    for key, value in old.items():
        if isinstance(value, dict) and 'command' in value:
            result = subprocess.run(value['command'], capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise RuntimeError(f'Inventory failed: {key}')
            value.update(exit_code=result.returncode, output=result.stdout.splitlines()[:12], stderr=result.stderr)
    for name, value in old['local_paths'].items():
        value['exists'] = Path(name).exists()
        value['bytes'] = subprocess.check_output(['du', '-sb', name], text=True, timeout=30).strip() if value['exists'] else None
    old['build_cache'] = [line for line in (root/'build/astra-native/CMakeCache.txt').read_text().splitlines()
                          if line.startswith(('CMAKE_BUILD_TYPE:', 'OPENMC_USE_'))]
    old['timestamp'] = subprocess.check_output(['date', '--iso-8601=seconds'], text=True).strip()
    (report/'prepartial-wsl.json').write_text(json.dumps(old, indent=2)+'\n')
    print(json.dumps(old, indent=2))
elif sys.argv[1] == 'compile':
    for name in ('prepartial-windows.json', 'prepartial-wsl.json'):
        json.loads((report/name).read_text())
    previous = json.loads((report/'native-after/receipt.json').read_text())
    command = previous['commands'][-1]['command'][:]
    source = root/'dev/stellarcsg/qualification/check_spherical_partial_indices.cpp'
    command[command.index(str(root/'dev/stellarcsg/qualification/check_spherical_equator.cpp'))] = str(source)
    binary = root/'build/astra-native/bin/stellarcsg_spherical_partial_probe'
    command[-1] = str(binary)
    library = root/'build/astra-native/lib/libopenmc.so'
    identities = {str(p): sha(p) for p in (source, source.with_name('check_spherical_equator.cpp'),
        root/'src/mesh.cpp', root/'include/openmc/mesh.h', library, Path(__file__),
        report/'prepartial-windows.json', report/'prepartial-wsl.json')}
    output = report/'native-partial-02'
    output.mkdir(exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS, (1536*1024**2,)*2)
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (output/'compile.txt').write_text(result.stdout+result.stderr)
    if result.returncode:
        raise RuntimeError('Supplemental compile failed')
    test = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
    (output/'probe.txt').write_text(test.stdout+test.stderr)
    assert all(sha(p) == h for p, h in identities.items()), 'Inputs changed'
    assert sha(library) == previous['new_library_sha256'], 'Library changed'
    receipt = dict(identities=identities, command=command, compile_exit_code=result.returncode,
        test_exit_code=test.returncode, probe_sha256=sha(binary), output_sha256=sha(output/'probe.txt'),
        acquisition_bytes=0, memory_cap_bytes=1536*1024**2, parallel_jobs=1)
    (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(test.stdout+test.stderr)
    sys.exit(test.returncode)
else:
    raise SystemExit('Expected inventory or compile')
