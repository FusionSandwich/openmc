"""Compare provisional one-period identity and admission across HDF5 variants."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    baseline = json.loads(args.baseline.read_text())
    candidate = json.loads(args.candidate.read_text())
    if (baseline["schema"] != "stellarcsg.period-candidate-manifest/v1"
            or candidate["schema"] != "stellarcsg.period-candidate-manifest/v1"):
        raise ValueError("unexpected candidate manifest schema")
    baseline_rows = {row["member"]: row for row in baseline["members"]}
    candidate_rows = {row["member"]: row for row in candidate["members"]}
    if set(baseline_rows) != set(candidate_rows):
        raise ValueError("HDF5 variants have different member sets")
    identity_fields = ("coil_id", "dataset", "rotational_family",
                       "family_canonical_member", "quarter_turns_from_canonical")
    admission_fields = ("sector_candidate", "span_count",
                        "admitted_span_indices", "admitted_span_count",
                        "inside_box_span_count", "touches_x_zero_box_count",
                        "touches_y_zero_box_count")
    identity_differences = []
    admission_differences = []
    content_id_changes = []
    for member in sorted(baseline_rows):
        left, right = baseline_rows[member], candidate_rows[member]
        if any(left[field] != right[field] for field in identity_fields):
            identity_differences.append(member)
        if any(left[field] != right[field] for field in admission_fields):
            admission_differences.append(member)
        if left["content_id"] != right["content_id"]:
            content_id_changes.append(member)
    same_families = baseline["families"] == candidate["families"]
    if identity_differences or admission_differences or not same_families:
        raise ValueError("candidate frame changes family or sector admission")
    report = {
        "schema": "stellarcsg.period-candidate-manifest-comparison/v1",
        "state": "IDENTITY_AND_ADMISSION_SAME_GEOMETRY_NOT_CERTIFIED",
        "hashes": {"baseline_sha256": sha256(args.baseline),
                   "candidate_sha256": sha256(args.candidate),
                   "comparator_sha256": sha256(Path(__file__))},
        "member_count": len(baseline_rows),
        "family_count": len(baseline["families"]),
        "same_family_mapping": same_families,
        "identity_difference_members": identity_differences,
        "admission_difference_members": admission_differences,
        "content_id_changed_count": len(content_id_changes),
        "content_id_changed_members": content_id_changes,
        "baseline_minimum_excluded_margin_cm":
            baseline["minimum_excluded_whole_box_margin_cm"],
        "candidate_minimum_excluded_margin_cm":
            candidate["minimum_excluded_whole_box_margin_cm"],
        "claim_boundary": "The frame-repaired candidate preserves provisional member-family mapping and per-span sector admission. Changed content IDs indicate different coefficient payloads; exact rotational symmetry, physical fidelity, seam ownership and transport are not proved.",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"state": report["state"],
                      "members": len(baseline_rows),
                      "content_id_changed": len(content_id_changes),
                      "admission_differences": len(admission_differences)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
