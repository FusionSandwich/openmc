"""Compare native OpenMC Python swept boxes with compiled analytic spans."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import openmc.surface


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiled-boxes", type=Path, required=True)
    parser.add_argument("--analytic-h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    root = Path(__file__).resolve().parents[3]
    python_surface = Path(openmc.surface.__file__).resolve()
    if python_surface != (root / "openmc" / "surface.py").resolve():
        raise ValueError("not running this checkout's native Python surface")
    table = {}
    with args.compiled_boxes.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = row["member"], row["span"]
            if key in table:
                raise ValueError("duplicate compiled span")
            table[key] = row
    expected = {(2, i) for i in range(256)} | {(3, i) for i in range(384)}
    if set(table) != expected:
        raise ValueError("compiled span coverage differs")
    checked = 0
    with h5py.File(args.analytic_h5) as h5:
        for member, count in ((2, 256), (3, 384)):
            group = h5[f"/coils/coil_{member:03d}"]
            boxes = openmc.surface._swept_compiled_member_boxes(group)
            if len(boxes) != count:
                raise ValueError("Python span count differs")
            for index, (center_lo, center_hi, _, _) in enumerate(boxes):
                row = table[member, index]
                for axis in range(3):
                    if (center_lo[axis].hex() !=
                            float.fromhex(row["lower_hex"][axis]).hex()
                            or center_hi[axis].hex() !=
                            float.fromhex(row["upper_hex"][axis]).hex()):
                        raise ValueError(f"Python/C++ box mismatch "
                                         f"{member}/{index}/{axis}")
                    checked += 2
    report = {
        "schema": "stellarcsg.native-python-swept-box-parity/v1",
        "state": "PYTHON_CENTERLINE_BOXES_MATCH_COMPILED_ANALYTIC",
        "member_spans": {"2": 256, "3": 384},
        "matched_binary64_endpoints": checked,
        "sha256": {
            "auditor": digest(Path(__file__)),
            "native_python_surface": digest(python_surface),
            "compiled_boxes": digest(args.compiled_boxes),
            "analytic_h5": digest(args.analytic_h5),
        },
        "claim_boundary": "The native OpenMC Python bounding-box helper reproduces all 3,840 compiled centerline box endpoints for two analytic shaped members, while the separate regression checks a control-hull escape. It does not prove C++ surface-box inflation or BVH traversal for arbitrary physical coils, root completeness, one-period ownership, transport or performance."
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["state"], checked)


if __name__ == "__main__":
    main()
