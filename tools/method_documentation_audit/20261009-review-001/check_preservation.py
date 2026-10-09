"""Check audit links and byte identities; does not run scientific tests."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REPO = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8-sig"))


docs = read("document_catalog_final.json")
late_docs = read("late_document_catalog.json")
docs += late_docs
latest_by_path = {x["canonical_path"]: x["sha256"] for x in late_docs}
raw = read("source_data_manifest.json")
late_files = read("late_source_manifest.json")["files"]
catalog = read("METHOD_RESULTS.json")
capture_mismatch = []
original_changes = []
for item in docs + raw:
    if sha(HERE / item["snapshot"]) != item["sha256"]:
        capture_mismatch.append(item["snapshot"])
    original = ROOT / item.get("canonical_path", item.get("original_path"))
    if not original.exists() or sha(original) != item["sha256"]:
        path = item.get("canonical_path", item.get("original_path"))
        original_changes.append({"path": path, "old_sha256": item["sha256"],
                                 "later_version_captured": original.exists() and sha(original) == latest_by_path.get(path)})
for item in late_files:
    if sha(HERE / item["snapshot"]) != item["sha256"]:
        capture_mismatch.append(item["snapshot"])

prior_attempt_checks = []
for item in read("source_inventory_final.json")["files"]:
    if "/tools/fourier_torus_prototype/" in item["path"]:
        prior_attempt_checks.append(item)
        if not (ROOT / item["path"]).exists() or sha(ROOT / item["path"]) != item["sha256"]:
            original_changes.append({"path": item["path"], "old_sha256": item["sha256"], "later_version_captured": False})
bad_links = []
checked_links = 0
for name in ["METHOD_RESULTS.md", "DOCUMENTATION_INDEX.md", "README.md", "AUDIT_FINDINGS.md"]:
    for target in re.findall(r"\]\(([^)]+)\)", (HERE / name).read_text(encoding="utf-8")):
        if "://" in target:
            continue
        if target.startswith("#"):
            continue
        checked_links += 1
        if not (HERE / target.split("#")[0]).exists() and target != "PRESERVATION_CHECK.json":
            bad_links.append({"file": name, "target": target})

prior_tracked_changes = subprocess.run(
    ["git", "diff", "HEAD", "--name-only"], cwd=REPO, capture_output=True, text=True, check=True
).stdout.splitlines()
prior_tracked_changes = [p for p in prior_tracked_changes if not p.startswith("tools/method_documentation_audit/")]
receipt = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "operation": "documentation/file-identity review; no scientific tests or builds",
    "method_entries": len(catalog["methods"]),
    "markdown_snapshots_checked": len(docs),
    "additional_machine_snapshots_checked": len(raw),
    "late_source_files_checked": len(late_files),
    "prior_prototype_artifact_hashes_checked": len(prior_attempt_checks),
    "snapshot_hash_mismatches": capture_mismatch,
    "canonical_original_changes_since_capture": original_changes,
    "review_links_checked": checked_links,
    "broken_review_links": bad_links,
    "preexisting_tracked_file_changes": prior_tracked_changes,
    "limitations": "Canonical copies plus selected receipts checked; every duplicate or all6227 original files not rehashed. Original frozen-doc internal links intentionally not rewritten.",
    "status": "PASS_WITH_CAPTURED_EXTERNAL_UPDATE" if original_changes and all(x["later_version_captured"] for x in original_changes) and not capture_mismatch and not bad_links and not prior_tracked_changes else "PASS" if not original_changes and not capture_mismatch and not bad_links and not prior_tracked_changes else "FAIL",
}
(HERE / "PRESERVATION_CHECK.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt))
if receipt["status"] == "FAIL":
    raise SystemExit(1)
