#!/usr/bin/env python3
"""Validate readiness evidence for the future matched protocol; NEVER launch it."""
import argparse
import json
from pathlib import Path
import sys

from portable_bench import Invalid, HEX, digest, fields, inside, need, read_json

GATES = (
    "candidate_numerics_and_admission", "old_fast_guardrails_and_same_session_ztorus",
    "physical_winding_pack_assembly", "nfp4_90deg_periodic_members_images_and_seams",
    "fidelity_ladder_and_clearance", "matched_sources_materials_tallies_settings_and_data",
    "frozen_h5m_and_native_geometry", "ordinary_dagmc_runtime_verified",
    "double_down_embree_runtime_verified", "lost_history_and_closure_contracts",
    "authorized_available_local_runtime", "resource_audit_current",
)


def check_manifest(path):
    path = Path(path).resolve()
    m = read_json(path)
    fields(m, ("schema", "gates"), label="gate manifest")
    need(m["schema"] == "stellarcsg.matched-readiness/v1", "wrong gate schema")
    fields(m["gates"], GATES, label="gates")
    blocked = []
    for name in GATES:
        gate = m["gates"][name]
        fields(gate, ("state", "reason", "evidence"), label=name)
        need(gate["state"] in ("PASS", "BLOCKED", "FAIL"), "invalid gate state")
        need(isinstance(gate["reason"], str) and gate["reason"], "gate reason required")
        if gate["state"] != "PASS":
            blocked.append({"gate": name, "state": gate["state"], "reason": gate["reason"]})
            continue
        evidence = gate["evidence"]
        need(isinstance(evidence, list) and evidence, "PASS gate needs evidence")
        for item in evidence:
            fields(item, ("path", "sha256", "reviewer", "scope"), label="gate evidence")
            need(isinstance(item["sha256"], str) and HEX.fullmatch(item["sha256"]), "bad evidence hash")
            need(isinstance(item["reviewer"], str) and item["reviewer"].strip(), "reviewer required")
            need(isinstance(item["scope"], str) and item["scope"].strip(), "review scope required")
            p = inside(path.parent, item["path"])
            need(p.is_file() and digest(p) == item["sha256"], "gate evidence hash mismatch")
    return {"readiness": "BLOCKED" if blocked else "EVIDENCE_PRESENT_REQUIRES_FINAL_REVIEW",
            "blocked": blocked, "execution": "NOT_IMPLEMENTED_NO_TRANSPORT_LAUNCH",
            "note": "Evidence hashes establish identity, not scientific validity or authorization by themselves."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    a = p.parse_args()
    try:
        result = check_manifest(a.manifest)
        print(json.dumps(result, indent=2))
        return 2 if result["blocked"] else 0
    except (Invalid, OSError, UnicodeError, TypeError) as exc:
        print(f"GATE_MANIFEST_INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
