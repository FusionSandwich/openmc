"""Exact support-contact reference for the unchanged synthetic ring payload.

Regenerates the source fixture in the recorded local libm environment, verifies
its complete FNV payload identity, then uses only Fraction geometry. A support
certificate applies to geometry conditions, never to query IDs in the engine.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct


EXPECTED_BANK = "fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723"
EXPECTED_PAYLOAD = "c5aec2165cdec18c"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value: object) -> object:
    if isinstance(value, F):
        return {"rational": str(value), "approximate": float(value)}
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", type=Path,
                        default=Path(__file__).with_name("recovery04_frozen_bank.csv"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    if digest(args.bank) != EXPECTED_BANK:
        raise ValueError("Frozen ray bank identity differs")
    center, normal, binormal = [], [], []
    for index in range(64):
        angle = 2 * math.pi * index / 64
        cosine, sine = math.cos(angle), math.sin(angle)
        center.extend((5 * cosine, 5 * sine, 0.0))
        normal.extend((0.0, 0.0, 1.0))
        binormal.extend((cosine, sine, 0.0))
    payload = struct.pack("<i", 9040) + b"".join(
        struct.pack("<d", value)
        for value in center + normal + binormal + [0.25] * 128)
    fnv = 1469598103934665603
    for byte in payload:
        fnv = ((fnv ^ byte) * 1099511628211) & ((1 << 64) - 1)
    if format(fnv, "x") != EXPECTED_PAYLOAD:
        raise ValueError("Local generated coefficient payload differs from frozen identity")
    points = [[F.from_float(center[3 * index + axis]) for axis in range(3)]
              for index in range(64)]

    def bezier(span: int, axis: int) -> tuple[F, ...]:
        p0, p1, p2, p3 = (points[(span + shift) % 64][axis]
                          for shift in (-1, 0, 1, 2))
        return ((p0 + 4 * p1 + p2) / 6, (2 * p1 + p2) / 3,
                (p1 + 2 * p2) / 3, (p1 + 4 * p2 + p3) / 6)

    with args.bank.open(newline="") as stream:
        rows = {row["id"]: row for row in csv.DictReader(stream)}
    certificates = []
    for query_id in ("a06", "a08"):
        row = rows[query_id]
        if row["coefficient_hash"] != EXPECTED_PAYLOAD:
            raise ValueError("Query coefficient association differs")
        origin = tuple(F.from_float(float(row["o" + axis])) for axis in "xyz")
        direction = tuple(F.from_float(float(row["d" + axis])) for axis in "xyz")
        if direction != (0, 1, 0):
            raise ValueError("Reference requires the supplied exact axis direction")
        radius = F(1, 4)
        cap = abs(origin[2]) == radius
        edge = origin[2] == 0
        if not (cap or edge):
            raise ValueError("Query is not a cardinal supporting contact")
        support = origin[0] if cap else origin[0] - radius
        all_controls = [bezier(span, 0) for span in range(64)]
        if any(control > support for controls in all_controls for control in controls):
            raise ValueError("Global supporting half-space not certified")
        if any(all(control == support for control in controls) for controls in all_controls):
            raise ValueError("Flat supporting chart needs continuum handling")
        seams = [span for span in range(64) if bezier(span, 0)[0] == support]
        contacts = []
        for span in seams:
            witness = tuple(bezier(span, axis)[0] for axis in range(3))
            t = witness[1] - origin[1]
            if t < 0:
                continue
            rounded = F.from_float(float(t))
            error = abs(t - rounded)
            # Supporting lower bound is Q>=1. At the returned ray point the
            # exact contact witness has Q=1+(time rounding error/radius)^2.
            residual_upper = (error / radius)**2
            contacts.append({"span": span, "center_exact": witness,
                             "t_exact": t, "returned_binary64_exact": rounded,
                             "return_error_exact": error,
                             "residual_upper_exact": residual_upper})
        contacts.sort(key=lambda item: item["t_exact"])
        if not contacts:
            raise ValueError("Expected exact positive contact was not certified")
        push = F.from_float(max(64 * 1e-11, 8 * 1e-10 * 5,
                               64 * 2**-52 * 5))
        suppressed = [item for item in contacts if item["t_exact"] >= push]
        certificates.append({
            "id": query_id, "origin_exact": origin, "direction_exact": direction,
            "case": "normal_cap" if cap else "outer_support_edge",
            "support_coordinate_exact": support,
            "global_bezier_support_upper_exact": max(max(c) for c in all_controls),
            "support_seams": seams,
            "all_support_spans_nonflat": True,
            "contacts_ordered": contacts,
            "first_eligible_unsuppressed_contact": contacts[0],
            "outward_normal_exact": [0, 0, 1] if cap else [1, 0, 0],
            "root_kind": "stationary_tangent",
            "strict_origin_outside": contacts[0]["t_exact"] > 0,
            "default_coincident_minimum_t_exact": push,
            "coincident_result": "hit" if suppressed else "no_hit",
            "coincident_first_contact": suppressed[0] if suppressed else None,
            "proof": [
                "All exact cardinal Bezier support controls are at or below M; every chart has at least one strict control, so all interior parameters lie strictly below M.",
                "Only canonical seam endpoints with support coordinate M can achieve equality. The cardinal edge/cap relation gives Q>=1 for every point on the complete ray.",
                "Q=1 exactly when the ray coordinate matches the corresponding support seam center; the finite ordered contact list therefore excludes every earlier root.",
                "All active centers at a contact have the same position and the same outward metric gradient, giving the stated exact normal. The tangent ray has zero normal dot direction."
            ]
        })
    report = {
        "schema": "stellarcsg.independent-exact-ring-support-contacts/v1",
        "state": "EXACT_SUPPORT_CONTACTS_CERTIFIED",
        "geometry_representation": "exact_control_offset",
        "script_sha256": digest(Path(__file__)),
        "bank_path": str(args.bank), "bank_sha256": EXPECTED_BANK,
        "generated_payload_fnv": format(fnv, "x"),
        "generated_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "generator": "Original torus_data(false) expression order; local libm sine/cosine; full payload FNV checked against unchanged frozen metadata.",
        "certificates": certificates,
        "claim_boundary": "Independent exact geometric contact proof for the verified generated ring payload. FNV is a fixture identifier, not a cryptographic attestation of a runtime dump. Does not qualify legacy geometry or tangent transport sense."
    }
    args.output.write_text(json.dumps(encode(report), indent=2, allow_nan=False) + "\n")
    print(json.dumps({"state": report["state"], "contacts": {
        c["id"]: str(c["first_eligible_unsuppressed_contact"]["t_exact"])
        for c in certificates}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
