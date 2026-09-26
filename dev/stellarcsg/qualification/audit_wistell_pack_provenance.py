"""Bind the local WISTELL-D filament and nominal ParaStell coil-section inputs.

This is a source/provenance audit, not a CAD or continuous-surface comparison.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scalar(text: str, key: str) -> str:
    match = re.search(rf"(?m)^  {re.escape(key)}: ([^\r\n#]+)", text)
    if match is None:
        raise ValueError(f"missing magnet_coils.{key}")
    return match.group(1).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--optimization-root", type=Path, required=True)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--parastell-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    opt_coils = args.optimization_root / "wistell-d_data/coils.wistell-d"
    local_coils = repo_root / "dev/stellarcsg/test_data/wistell_d/coils.wistell-d"
    constants = args.optimization_root / "stellarator_optimization/geometry/constants.py"
    config = args.case_dir / "parastell_config.yaml"
    case_receipt = args.case_dir / "case_receipt.json"
    parastell = args.parastell_root / "parastell/magnet_coils.py"
    compiler = repo_root / "dev/stellarcsg/qualification/qualify_coils.py"

    hashes = {name: sha256(path) for name, path in {
        "optimization_coils": opt_coils,
        "stellarcsg_coils": local_coils,
        "optimization_constants": constants,
        "p00_config": config,
        "p00_case_receipt": case_receipt,
        "local_parastell_magnet_coils": parastell,
        "stellarcsg_ellipse_compiler": compiler,
    }.items()}
    case = json.loads(case_receipt.read_text(encoding="utf-8"))
    if not (hashes["optimization_coils"] == hashes["stellarcsg_coils"]
            == case["authoritative_input_sha256"]["coils.wistell-d"]):
        raise ValueError("WISTELL-D coil filament hashes disagree")
    if hashes["p00_config"] != case["configuration"]["sha256"]:
        raise ValueError("P00 configuration hash disagrees with its receipt")
    if case["field_periods"] != 4:
        raise ValueError("unexpected WISTELL-D field periods")

    config_text = config.read_text(encoding="utf-8")
    magnet_block = config_text.split("\nmagnet_coils:\n", 1)[1].split("\nsource_mesh:", 1)[0]
    width = float(scalar(magnet_block, "width"))
    thickness = float(scalar(magnet_block, "thickness"))
    sample_mod = int(scalar(magnet_block, "sample_mod"))
    extent = float(scalar(magnet_block, "toroidal_extent"))
    if scalar(magnet_block, "coils_file") != "coils.wistell-d":
        raise ValueError("P00 references another coil file")
    if (width, thickness, sample_mod, extent) != (30.0, 30.0, 6, 90.0):
        raise ValueError("P00 magnet recipe changed; review this audit")

    constants_text = constants.read_text(encoding="utf-8")
    match = re.search(r"(?m)^magnet_thickness\s*=\s*([0-9.]+)\s*$", constants_text)
    if match is None or float(match.group(1)) != 30.0:
        raise ValueError("optimization continuous magnet-layer thickness changed")
    parastell_text = parastell.read_text(encoding="utf-8")
    for marker in ("outward_dirs = coords - self.center_of_mass",
                   "normals = outward_dirs - parallel_parts[:, np.newaxis] * tangents",
                   "binormals = np.cross(tangents, normals)",
                   "edge_offsets = np.array([[-1, -1], [-1, 1], [1, 1], [1, -1]])",
                   "cq.Edge.makeSpline(coord_vectors, tangents=tangent_vectors).close()",
                   "cq.Face.makeRuledSurface(edge1, edge2)"):
        if marker not in parastell_text:
            raise ValueError(f"local ParaStell recipe marker missing: {marker}")
    compiler_text = compiler.read_text(encoding="utf-8")
    if "major_radius_cm=10.0" not in compiler_text or "minor_radius_cm=8.0" not in compiler_text:
        raise ValueError("StellarCSG diagnostic ellipse changed")

    try:
        parastell_commit = subprocess.check_output(
            ["git", "-C", str(args.parastell_root), "rev-parse", "HEAD"],
            text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        parastell_commit = None

    receipt = {
        "schema": "stellarcsg.wistell-pack-provenance/v1",
        "classification": "NOMINAL_P00_SECTION_SOURCE_IDENTIFIED_CAD_UNVERIFIED",
        "input_sha256": hashes,
        "source_paths": {
            "optimization_root": str(args.optimization_root.resolve()),
            "p00_case_dir": str(args.case_dir.resolve()),
            "local_parastell_root": str(args.parastell_root.resolve()),
        },
        "p00_case_sha256": case["parastell_case_sha256"],
        "p00_case_status": case["status"],
        "field_periods": case["field_periods"],
        "p00_magnet_coils": {
            "width_cm": width,
            "thickness_cm": thickness,
            "sample_mod": sample_mod,
            "toroidal_extent_deg": extent,
            "section": "nominal rectangle",
            "frame": "project(centerline - filament center of mass, tangent normal plane); binormal = tangent cross normal",
            "edge_construction": "CadQuery spline through sampled offset corners, then ruled faces",
        },
        "local_parastell_commit": parastell_commit,
        "optimization_magnet_layer_thickness_cm": float(match.group(1)),
        "diagnostic_ellipse": {
            "major_radius_cm": 10.0,
            "minor_radius_cm": 8.0,
            "area_cm2": 80.0 * math.pi,
        },
        "nominal_section_comparison": {
            "rectangle_area_cm2": width * thickness,
            "rectangle_to_ellipse_area_ratio": width * thickness / (80.0 * math.pi),
            "rectangle_min_in_plane_support_cm": min(width, thickness) / 2.0,
            "ellipse_max_in_plane_support_cm": 10.0,
            "minimum_support_gap_cm_if_same_center_and_tangent_plane": min(width, thickness) / 2.0 - 10.0,
        },
        "p00_step_files_in_local_case_dir": sorted(
            str(path.relative_to(args.case_dir)) for path in args.case_dir.rglob("*.step")),
        "claim_boundary": "Identifies nominal local P00 parameters and a local ParaStell construction recipe. Does not establish the exact ParaStell revision used for accepted P00 CAD, compare STEP surfaces, certify continuous support, or qualify StellarCSG transport geometry.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{receipt['classification']}: {args.output}")


if __name__ == "__main__":
    main()
