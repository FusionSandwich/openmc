"""Compare staged Git blobs with captured bytes; no scientific execution."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
staged = subprocess.run(
    ["git", "ls-files", "--stage", "-z", "--", "tools/method_documentation_audit"],
    cwd=REPO, capture_output=True, check=True,
).stdout
rows = []
mismatches = []
for entry in staged.split(b"\0"):
    if not entry:
        continue
    meta, name = entry.split(b"\t", 1)
    oid = meta.split()[1].decode()
    path = name.decode()
    if Path(path).name in {"GIT_PRESERVATION.json", "AUDIT_MANIFEST.json"}:
        continue
    raw = (REPO / path).read_bytes()
    expected = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    rows.append({"path": path, "git_blob": oid, "sha256": hashlib.sha256(raw).hexdigest()})
    if oid != expected:
        mismatches.append(path)
receipt = {
    "checked_utc": datetime.now(timezone.utc).isoformat(),
    "status": "FAIL" if mismatches else "PASS",
    "staged_files_checked": len(rows),
    "byte_conversion_mismatches": mismatches,
    "mechanism": "Scoped .gitattributes disables text conversion; staged Git blob identity compared with captured bytes",
    "generated_receipt_and_seal_excluded_from_self_check": True,
    "files": rows,
}
(HERE / "GIT_PRESERVATION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: receipt[k] for k in ["status", "staged_files_checked", "byte_conversion_mismatches"]}))
if mismatches:
    raise SystemExit(1)
