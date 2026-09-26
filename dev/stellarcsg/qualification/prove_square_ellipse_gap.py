"""Prove a section-shape lower bound for the source WISTELL-D coil.

The proof concerns a planar 30 x 30 cm square and *any* filled ellipse,
including translated and rotated ellipses. It is a section result, not a
Hausdorff bound for the complete ParaStell CAD or accepted P00 mesh.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re

import h5py
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text(value: object) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", required=True, type=Path)
    parser.add_argument("--constants", required=True, type=Path)
    parser.add_argument("--filaments", required=True, type=Path)
    parser.add_argument("--parastell", required=True, type=Path)
    parser.add_argument("--swept-implementation", required=True, type=Path)
    parser.add_argument("--candidate-h5", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new path")

    generator = args.generator.read_text()
    constants = args.constants.read_text()
    parastell = args.parastell.read_text()
    swept = args.swept_implementation.read_text()
    if not re.search(r"\bmagnet_thickness\s*=\s*30\b", constants):
        raise ValueError("source magnet thickness is no longer 30 cm")
    if (not re.search(r'\bcoils_file\s*=\s*["\']coils\.wistell-d["\']', constants)
            or args.filaments.name != "coils.wistell-d"):
        raise ValueError("source filament file identity changed")
    if not re.search(
        r"gc\.coils_file\s*,\s*gc\.magnet_thickness\s*,"
        r"\s*gc\.magnet_thickness\s*,", generator):
        raise ValueError("source no longer passes 30 cm for both coil axes")
    for expression in (
        "binormals = np.cross(tangents, normals)",
        "edge_offset[0] * binormals * (width / 2)",
        "edge_offset[1] * normals * (thickness / 2)",
    ):
        if expression not in parastell:
            raise ValueError(f"ParaStell section frame changed: {expression}")
    for expression in (
        "normal_value = normalized(normal_value);",
        "binormal_value = normalized(cross(tangent, normal_value));",
        "normal_value = cross(binormal_value, tangent);",
        "normal_value = normalized(normal_value - dot(normal_value, tangent) * tangent);",
        "value.major_radius * std::cos(alpha) * value.normal",
        "value.minor_radius * std::sin(alpha) * value.binormal",
    ):
        if expression not in swept:
            raise ValueError(f"swept section evaluation changed: {expression}")

    manifest = json.loads(args.manifest.read_text())
    if manifest["input_hashes"]["h5_sha256"] != sha256(args.candidate_h5):
        raise ValueError("candidate HDF5 differs from selector manifest")
    selected = [row for row in manifest["members"] if row["sector_candidate"]]
    if len(selected) != 18 or len({row["member"] for row in selected}) != 18:
        raise ValueError("expected 18 distinct provisional sector members")
    with h5py.File(args.candidate_h5, "r") as handle:
        for row in selected:
            group = handle["coils"][row["member"]]
            if text(group.attrs["content_id"]) != row["content_id"]:
                raise ValueError("manifest member content ID differs")
            major = np.asarray(group["major_radius_coefficients"])
            minor = np.asarray(group["minor_radius_coefficients"])
            if not np.all(major == 10.0) or not np.all(minor == 8.0):
                raise ValueError("provisional candidate no longer has 10 x 8 cm radii")

    with localcontext() as context:
        context.prec = 60
        a = Decimal(15)
        sqrt2 = Decimal(2).sqrt()
        # The exact optimum over all filled, translated, rotated ellipses.
        optimum = a * (sqrt2 - 1) / 2
        optimal_circle_radius = a * (1 + sqrt2) / 2
        # Any ellipse whose largest semiaxis is at most 10 cm has paired
        # diagonal support at most 10 cm; the square has 15*sqrt(2) cm.
        candidate_lower = a * sqrt2 - Decimal(10)
        assert optimum > 3 and candidate_lower > 11
        receipt = {
            "schema": "stellarcsg.square-ellipse-section-gap/v1",
            "classification": "ELLIPTICAL_SECTION_CANNOT_MATCH_SOURCE_SQUARE",
            "source_section_cm": {"shape": "square", "width": 30,
                                  "thickness": 30, "half_side": 15},
            "infimum_hausdorff_gap_over_all_ellipses_cm": str(optimum),
            "attaining_circle_radius_cm": str(optimal_circle_radius),
            "provisional_candidate_semiaxes_cm": [10, 8],
            "candidate_section_gap_lower_bound_cm": str(candidate_lower),
            "proof": [
                "For a centered square S=[-a,a]^2, h_S(u)=a(|u_x|+|u_y|).",
                "An ellipse with center c and shape matrix Q has h_E(u)=c dot u+sqrt(u^T Q u). Pairing u and -u cancels c, so translation cannot improve the maximum support error.",
                "If every support error is at most delta, the two cardinal directions imply sqrt(Q_11),sqrt(Q_22)<=a+delta.",
                "For d_+=(1,1)/sqrt(2) and d_-=(1,-1)/sqrt(2), d_+^T Q d_+ + d_-^T Q d_- = Q_11+Q_22. Hence at least one diagonal ellipse support radius is <=a+delta.",
                "The square support is a*sqrt(2) on both diagonals, so a*sqrt(2)-delta<=a+delta and delta>=a*(sqrt(2)-1)/2.",
                "A circle of radius a*(1+sqrt(2))/2 attains this bound because square support ranges from a to a*sqrt(2).",
                "For the provisional candidate, every ellipse section support radius is <=10 cm; paired diagonal support therefore differs from the square by at least 15*sqrt(2)-10 cm."
            ],
            "input_sha256": {
                "generator": sha256(args.generator),
                "constants": sha256(args.constants),
                "filaments": sha256(args.filaments),
                "parastell_magnet_coils": sha256(args.parastell),
                "swept_implementation": sha256(args.swept_implementation),
                "candidate_h5": sha256(args.candidate_h5),
                "selector_manifest": sha256(args.manifest),
                "proof_script": sha256(Path(__file__)),
            },
            "claim_boundary": "Rigorous planar support-distance bound for the 30 x 30 cm square specified at ParaStell coil sections, and a larger bound for the selected 10 x 8 cm elliptical payload sections. It does not bound complete swept CAD or mesh Hausdorff distance, determine sector clipping, or qualify transport."
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in (
        "classification", "infimum_hausdorff_gap_over_all_ellipses_cm",
        "candidate_section_gap_lower_bound_cm")}))


if __name__ == "__main__":
    main()
