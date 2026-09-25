"""Build a separate, exactly quarter-turn-related coefficient candidate.

This changes the supplied coil payload and is diagnostic until fidelity and
transport are independently qualified. The input HDF5 is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


VECTOR_FIELDS = ("centerline_coefficients", "normal_coefficients",
                 "binormal_coefficients")
RADIUS_FIELDS = ("major_radius_coefficients", "minor_radius_coefficients")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_text(value: object) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def rotate_quarter(values: np.ndarray, turns: int) -> np.ndarray:
    """Use only sign and coordinate swaps for 90-degree rotations."""
    result = np.asarray(values, dtype=np.float64).reshape(-1, 3).copy()
    for _ in range(turns):
        x, y = result[:, 0].copy(), result[:, 1].copy()
        result[:, 0], result[:, 1] = -y, x
    return result


def content_id(group: h5py.Group) -> str:
    digest = hashlib.sha256(as_text(group.attrs["canonical_metadata_json"]).encode())
    for field in (*VECTOR_FIELDS, *RADIUS_FIELDS):
        digest.update(np.asarray(group[field], dtype="<f8", order="C").tobytes())
    return "sha256:" + digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-h5", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-h5", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    if args.output_h5.exists() or args.receipt.exists():
        parser.error("output HDF5 and receipt must both be new")
    input_hash = sha256(args.input_h5)
    manifest = json.loads(args.manifest.read_text())
    if (manifest["input_hashes"]["h5_sha256"] != input_hash
            or manifest["field_period_degrees"] != 90
            or len(manifest["families"]) != 12
            or len(manifest["members"]) != 48):
        raise ValueError("input/manifest/period identity mismatch")
    expected_members = {row["member"] for row in manifest["members"]}
    if len(expected_members) != 48:
        raise ValueError("duplicate member identity")
    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with h5py.File(args.input_h5, "r") as source, h5py.File(args.output_h5, "x") as target:
        if set(source["coils"]) != expected_members:
            raise ValueError("source member set differs from manifest")
        for key, value in source.attrs.items():
            target.attrs[key] = value
        source.copy("coils", target)
        seen = set()
        for family in manifest["families"]:
            members = family["full_device_members"]
            if len(members) != 4 or len(set(members)) != 4:
                raise ValueError("invalid four-image family")
            canonical = source["coils"][members[0]]
            canonical_length = float(canonical.attrs["length_cm"])
            for turns, member in enumerate(members):
                if member in seen:
                    raise ValueError("member appears in multiple families")
                seen.add(member)
                original = source["coils"][member]
                group = target["coils"][member]
                deviations = {}
                for field in VECTOR_FIELDS:
                    expected = rotate_quarter(np.asarray(canonical[field]), turns)
                    existing = np.asarray(original[field], dtype=float).reshape(-1, 3)
                    if expected.shape != existing.shape:
                        raise ValueError("control shape changed across rotations")
                    deviations[field] = float(np.max(np.linalg.norm(
                        expected - existing, axis=1)))
                    group[field][...] = expected
                for field in RADIUS_FIELDS:
                    expected = np.asarray(canonical[field], dtype=float)
                    existing = np.asarray(original[field], dtype=float)
                    if expected.shape != existing.shape:
                        raise ValueError("radius shape changed across rotations")
                    deviations[field] = float(np.max(np.abs(expected - existing)))
                    group[field][...] = expected
                old_id = as_text(original.attrs["content_id"])
                metadata = json.loads(as_text(original.attrs["source_metadata_json"]))
                metadata["exact_period_candidate"] = {
                    "canonical_member": members[0], "quarter_turns": turns,
                    "input_h5_sha256": input_hash, "original_content_id": old_id}
                group.attrs["source_metadata_json"] = json.dumps(
                    metadata, sort_keys=True, separators=(",", ":"))
                group.attrs["length_cm"] = canonical_length
                group.attrs["canonical_metadata_json"] = json.dumps({
                    "schema_version": [1, 0], "coil_id": int(group.attrs["coil_id"]),
                    "units": "cm", "length_cm": canonical_length,
                    "source_metadata": metadata},
                    sort_keys=True, separators=(",", ":"))
                group.attrs["content_id"] = content_id(group)
                rows.append({"member": member, "canonical_member": members[0],
                             "quarter_turns": turns, "old_content_id": old_id,
                             "new_content_id": as_text(group.attrs["content_id"]),
                             "length_delta_cm": canonical_length
                                - float(original.attrs["length_cm"]),
                             "control_deviation": deviations})
        if seen != expected_members:
            raise ValueError("families do not partition all members")
    # Reopen and independently check the written payload, not just arrays in memory.
    with h5py.File(args.output_h5, "r") as target:
        for row in rows:
            group = target["coils"][row["member"]]
            canonical = target["coils"][row["canonical_member"]]
            turns = row["quarter_turns"]
            for field in VECTOR_FIELDS:
                if not np.array_equal(np.asarray(group[field]),
                                      rotate_quarter(np.asarray(canonical[field]), turns)):
                    raise ValueError("written vector is not exact quarter-turn image")
            for field in RADIUS_FIELDS:
                if not np.array_equal(np.asarray(group[field]),
                                      np.asarray(canonical[field])):
                    raise ValueError("written radius differs across family")
            if as_text(group.attrs["content_id"]) != content_id(group):
                raise ValueError("written content ID does not bind payload")
    receipt = {
        "schema": "stellarcsg.exact-period-frame-candidate/v1",
        "state": "SEPARATE_EXACT_COEFFICIENT_ROTATION_CANDIDATE_NOT_QUALIFIED",
        "hashes": {"input_h5_sha256": input_hash,
                   "manifest_sha256": sha256(args.manifest),
                   "output_h5_sha256": sha256(args.output_h5),
                   "builder_sha256": sha256(Path(__file__))},
        "field_period_degrees": 90,
        "family_count": len(manifest["families"]), "member_count": len(rows),
        "max_centerline_control_deviation_cm": max(
            row["control_deviation"]["centerline_coefficients"] for row in rows),
        "max_normal_control_deviation": max(
            row["control_deviation"]["normal_coefficients"] for row in rows),
        "max_binormal_control_deviation": max(
            row["control_deviation"]["binormal_coefficients"] for row in rows),
        "max_absolute_length_delta_cm": max(abs(row["length_delta_cm"]) for row in rows),
        "rows": rows,
        "claim_boundary": "All 48 written coefficient members are exact sign/swap 90-degree images of 12 canonical members, with radii copied and canonical content IDs recomputed. This is a changed diagnostic payload. Control deviations do not bound the full evaluated surface, establish physical winding-pack fidelity, wall clearance, seam ownership or particle transport."
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in
                      ("state", "member_count", "max_centerline_control_deviation_cm",
                       "max_normal_control_deviation", "max_binormal_control_deviation")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
