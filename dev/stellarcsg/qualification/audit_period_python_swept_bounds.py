"""Exercise Python swept bounds on the provisional 18-member period image."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import h5py
import openmc
import openmc.surface


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--selector-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    root = Path(__file__).resolve().parents[3]
    python_surface = Path(openmc.surface.__file__).resolve()
    if python_surface != (root / "openmc" / "surface.py").resolve():
        raise ValueError("not running this checkout's native Python surface")
    manifest = json.loads(args.manifest.read_text())
    selector = json.loads(args.selector_receipt.read_text())
    source_hash = digest(args.h5)
    if (manifest["input_hashes"]["h5_sha256"] != source_hash
            or selector["state"] != "PASS_REPRESENTATION_ONLY"
            or selector["selected_member_count"] != 18
            or manifest["sector_candidate_count"] != 18
            or selector["hashes"].get(next((key for key in selector["hashes"]
                if key.endswith("/" + args.h5.name)), "")) != source_hash):
        raise ValueError("provisional period identity mismatch")
    ids = selector["selected_member_ids"]
    if len(ids) != 18 or len(set(ids)) != 18 or any(type(i) is not int for i in ids):
        raise ValueError("invalid selected IDs")
    manifest_members = {row["coil_id"]: row for row in manifest["members"]
                        if row["sector_candidate"]}
    if set(manifest_members) != set(ids):
        raise ValueError("manifest and native selected members differ")
    admitted_span_count = sum(row["admitted_span_count"]
                              for row in manifest_members.values())
    whole_span_count = sum(row["span_count"]
                           for row in manifest_members.values())
    if admitted_span_count != manifest["sector_candidate_span_count"]:
        raise ValueError("manifest admitted span count differs")
    with h5py.File(args.h5) as h5:
        span_count = sum(len(h5[f"/coils/coil_{member:03d}/centerline_coefficients"])
                         for member in ids)
    if span_count != whole_span_count:
        raise ValueError("whole-coil span count differs from manifest")
    surface = openmc.SweptSplineSurface(
        args.h5, dataset_prefix="/coils/coil_", dataset_indices=ids)
    box = surface.bounding_box("-")
    lower = list(map(float, box.lower_left))
    upper = list(map(float, box.upper_right))
    if (not all(math.isfinite(value) for value in lower + upper)
            or any(lo >= hi for lo, hi in zip(lower, upper))):
        raise ValueError("nonfinite or inverted Python period box")
    report = {
        "schema": "stellarcsg.period-python-swept-bounds/v1",
        "state": "PROVISIONAL_PERIOD_PYTHON_BOUNDS_FINITE",
        "selected_member_ids": ids,
        "selected_member_count": len(ids),
        "registered_whole_coil_span_count": span_count,
        "manifest_admitted_span_count": admitted_span_count,
        "registered_unadmitted_span_count": span_count - admitted_span_count,
        "box_lower_cm": lower,
        "box_upper_cm": upper,
        "sha256": {
            "auditor": digest(Path(__file__)),
            "native_python_surface": digest(python_surface),
            "candidate_h5": source_hash,
            "manifest": digest(args.manifest),
            "native_selector_receipt": digest(args.selector_receipt),
        },
        "claim_boundary": "The corrected Python bounding-box path computes a finite noninverted box for 18 provisionally selected whole coils. Native registration includes all their spans, while the manifest admits only a subset as sector candidates; the unadmitted spans have not been clipped away. The exact-rotation coefficient image is not an accepted physical winding pack. This does not compare every physical compiled C++ box, prove periodic-plane ownership, root completeness, source clearance, transport or latency."
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["state"], span_count, lower, upper)


if __name__ == "__main__":
    main()
