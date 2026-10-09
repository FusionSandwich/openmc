"""Copy committed evidence to this experiment, without touching its owner."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[4] / 'stellarcsg-fourier-torus-prototype-20261009'
COMMIT = '9399a879926cb09658709ff030d0317e9e96b7e5'
PREFIX = 'tools/fourier_torus_prototype/'
DESTINATION = HERE / 'snapshot'


def main():
    paths = subprocess.check_output(
        ['git', '-C', str(OWNER), 'ls-tree', '-r', COMMIT, PREFIX],
        text=True).splitlines()
    rows = []
    for entry in paths:
        metadata, source = entry.split('\t', 1)
        blob = metadata.split()[2]
        data = subprocess.check_output(
            ['git', '-C', str(OWNER), 'cat-file', 'blob', blob])
        destination = DESTINATION / source[len(PREFIX):]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != data:
                raise ValueError(f'Refuse to replace different input: {source}')
        else:
            destination.write_bytes(data)
        rows.append(dict(source=source, snapshot=str(destination.relative_to(HERE)),
                         bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    (HERE / 'snapshot_manifest.json').write_text(json.dumps(dict(
        created_utc=datetime.now(timezone.utc).isoformat(), source_commit=COMMIT,
        owner_checkout=str(OWNER), files=rows), indent=2) + '\n', encoding='utf-8')
    print(f'Frozen {len(rows)} files; {sum(row["bytes"] for row in rows)} bytes')


if __name__ == '__main__':
    main()
