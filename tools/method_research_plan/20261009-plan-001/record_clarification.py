"""Preserve the initial proposal registry and add an explicit clarification."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
initial = HERE / "EXPERIMENT_REGISTRY.json"
raw = initial.read_bytes()
original_sha = hashlib.sha256(raw).hexdigest()
registry = json.loads(raw)
proposal = next(p for p in registry["proposals"] if p["id"] == "NEXT-P01")
old = "M22 sense counterexample"
new = "M22 failed-sense probe: recover exact point/direction with diagnostic before freezing a regression"
assert old in proposal["negative_controls"]
now = datetime.now(timezone.utc).isoformat()
correction = {
    "recorded_utc": now,
    "kind": "proposal wording clarification; no execution or outcome change",
    "initial_registry_sha256": original_sha,
    "proposal_id": "NEXT-P01",
    "field": "negative_controls",
    "old_text_retained_in_initial_registry": old,
    "clarified_text": new,
    "reason": "Retained M22 report establishes sense failure but lacks exact point/direction; planned control needs input recovery",
    "all_proposals_remain": "PROPOSED_NOT_RUN",
}
proposal["negative_controls"] = [new if x == old else x for x in proposal["negative_controls"]]
registry["clarification_revision"] = 1
registry["initial_registry_preserved"] = {"path": "EXPERIMENT_REGISTRY.json", "sha256": original_sha}
registry["clarification_record"] = "REGISTRY_CORRECTIONS.json"
for name in ["REGISTRY_CORRECTIONS.json", "EXPERIMENT_REGISTRY_REVISION_001.json"]:
    if (HERE / name).exists():
        raise FileExistsError("Clarification record already exists: " + name)
with (HERE / "REGISTRY_CORRECTIONS.json").open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(correction, indent=2) + "\n")
with (HERE / "EXPERIMENT_REGISTRY_REVISION_001.json").open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(registry, indent=2) + "\n")
with (HERE / "EVENTS.jsonl").open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({"recorded_utc": now, "event": "PROPOSAL_CLARIFICATION", "id": "NEXT-P01", "status": "PROPOSED_NOT_RUN", "record": "REGISTRY_CORRECTIONS.json", "initial_registry_sha256": original_sha}) + "\n")
assert initial.read_bytes() == raw
print(json.dumps({"status": "INITIAL_REGISTRY_PRESERVED", "scientific_executions": 0, "clarification_revision": 1}))
