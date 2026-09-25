"""Check actual WISTELL-D one-period candidate member selectors in Python.

This is a representation/bounding-box check, not a transport model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import openmc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    manifest = json.loads(args.manifest.read_text())
    if manifest["input_hashes"]["h5_sha256"] != sha256(args.h5):
        raise ValueError("manifest does not bind the selected HDF5 input")
    selected = [row for row in manifest["members"] if row["sector_candidate"]]
    if len(selected) != 18 or len({row["coil_id"] for row in selected}) != 18:
        raise ValueError("expected eighteen unique candidate surface IDs")
    rows = []
    with h5py.File(args.h5, "r") as handle:
        for row in selected:
            group = handle[row["dataset"]]
            content_id = group.attrs["content_id"]
            if isinstance(content_id, bytes):
                content_id = content_id.decode()
            if content_id != row["content_id"]:
                raise ValueError("manifest content ID differs from HDF5")
            openmc.reset_auto_ids()
            surface = openmc.SweptSplineSurface(
                args.h5.resolve(), row["dataset"], row["content_id"],
                surface_id=row["coil_id"])
            element = surface.to_xml_element()
            openmc.reset_auto_ids()
            imported = openmc.Surface.from_xml_element(element)
            if not imported.is_equal(surface) or imported.id != row["coil_id"]:
                raise ValueError("selected surface XML round trip lost identity")
            bounds = surface.bounding_box("-")
            lower = np.asarray(bounds.lower_left, dtype=np.float64)
            upper = np.asarray(bounds.upper_right, dtype=np.float64)
            if not (np.isfinite(lower).all() and np.isfinite(upper).all()
                    and np.all(lower <= upper)):
                raise ValueError("selected surface has invalid Python bounds")
            rows.append({
                "member": row["member"],
                "surface_id": surface.id,
                "rotational_family": row["rotational_family"],
                "quarter_turns_from_canonical":
                    row["quarter_turns_from_canonical"],
                "dataset": imported.dataset,
                "content_id": imported.content_id,
                "bounds_cm": [lower.tolist(), upper.tolist()],
            })
    args.output.mkdir(parents=True)
    report = {
        "schema": "stellarcsg.period-candidate-selector-check/v1",
        "state": "PYTHON_SELECTORS_18_OF_18_NO_TRANSPORT",
        "hashes": {
            "h5_sha256": sha256(args.h5),
            "manifest_sha256": sha256(args.manifest),
            "surface_py_sha256": sha256(Path(openmc.surface.__file__)),
            "verifier_sha256": sha256(Path(__file__)),
        },
        "selected_count": len(rows),
        "rows": rows,
        "native_cpp_transport_run": False,
        "claim_boundary": "Actual candidate HDF5 selectors round-trip through the local OpenMC Python API with finite broad bounds. Whole surfaces remain untrimmed; physical-image identity, seam ownership, C++ roots, one-period transport and fidelity are unqualified.",
    }
    (args.output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"state": report["state"], "selected_count": len(rows),
                      "families": len({row["rotational_family"] for row in rows})}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
