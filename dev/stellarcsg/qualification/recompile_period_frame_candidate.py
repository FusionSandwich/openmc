"""Compile a separate rotation-covariant WISTELL-D coil candidate and receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from stellarcsg import (SweptSplineData, read_makegrid_filaments,
                       write_swept_collection)


EXPECTED_SOURCE_SHA256 = "7748369407d28a70f35b5c4a7c0ab860495a08fd0030002112ea933fe570159b"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output_h5.exists() or args.receipt.exists():
        parser.error("output HDF5 and receipt must both be new")
    source_hash = sha256(args.source)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise ValueError("WISTELL-D filament source hash differs from pinned input")
    periods, curves = read_makegrid_filaments(args.source)
    if periods != 4 or len(curves) != 48:
        raise ValueError("expected four field periods and 48 full-device coils")
    coils = [SweptSplineData.from_centerline(
        1000 + index, curve, major_radius_cm=10.0, minor_radius_cm=8.0,
        sample_count=256,
        source_metadata={"kind": "makegrid_filament",
                         "source_file": args.source.name,
                         "source_sha256": source_hash,
                         "periods": periods,
                         "frame_seed": "cylindrical_radial_fallback_v1"})
        for index, curve in enumerate(curves)]
    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    write_swept_collection(args.output_h5, coils)
    receipt = {
        "schema": "stellarcsg.period-frame-candidate/v1",
        "source_sha256": source_hash,
        "output_h5_sha256": sha256(args.output_h5),
        "field_periods": periods,
        "full_device_coils": len(coils),
        "id_offset": 1000,
        "sample_count": 256,
        "major_radius_cm": 10.0,
        "minor_radius_cm": 8.0,
        "frame_seed": "cylindrical_radial_fallback_v1",
        "claim_boundary": "Separate coefficient candidate; no continuous-surface, physical winding-pack, one-period closure or transport qualification.",
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in
                      ("full_device_coils", "output_h5_sha256", "frame_seed")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
