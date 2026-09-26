"""Check native failure paths for malformed P00 facet component selection."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

from audit_periodic_facet_ray_bank import sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--positive-case", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--cross-sections", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    if not all((args.positive_case / name).exists() for name in
               ("geometry.xml", "settings.xml", "materials.xml",
                "tracks.h5", "statepoint.1.h5")):
        raise ValueError("positive native case is incomplete")
    if (not (args.positive_case / "receipt.json").exists()
            and args.positive_case.name != "volume-08"):
        raise ValueError("expected selected positive volume-08 case")
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS="1",
               LD_LIBRARY_PATH=str(args.library.resolve().parent),
               OPENMC_CROSS_SECTIONS=str(args.cross_sections.resolve()))
    args.output.mkdir(parents=True)
    cases = [
        ("wrong_cap", "x0", "8", "Requested periodic cap has no oriented triangles"),
        ("missing_component", "y0", "99", "Selected facet component_id is absent"),
        ("malformed_component", "y0", "1_6", "requires a positive int32 component_id"),
    ]
    rows = []
    for name, cap, component, expected in cases:
        target = args.output / name
        target.mkdir()
        for filename in ("settings.xml", "materials.xml"):
            shutil.copyfile(args.positive_case / filename, target / filename)
        tree = ET.parse(args.positive_case / "geometry.xml")
        facet = tree.find(".//surface[@id='1108']")
        if (facet is None or facet.get("component_id") != "8"
                or facet.get("periodic_caps") != "y0"):
            raise ValueError("positive geometry is not volume-8 component model")
        facet.set("periodic_caps", cap)
        facet.set("component_id", component)
        tree.write(target / "geometry.xml", encoding="utf-8", xml_declaration=True)
        run = subprocess.run([str(args.binary.resolve())], cwd=target, env=env,
                             capture_output=True, text=True, timeout=30)
        diagnostic = run.stdout + run.stderr
        normalized_diagnostic = " ".join(diagnostic.split())
        rows.append({
            "case": name, "exit_code": run.returncode,
            "expected_diagnostic": expected,
            "observed_expected_diagnostic": expected in normalized_diagnostic,
            "unexpected_track": (target / "tracks.h5").exists(),
            "geometry_xml_sha256": sha256(target / "geometry.xml"),
            "diagnostic_tail": diagnostic[-1200:],
            "pass": run.returncode != 0 and expected in normalized_diagnostic
                    and not (target / "tracks.h5").exists(),
        })
    passed = all(row["pass"] for row in rows)
    receipt = {
        "schema": "stellarcsg.component-facet-rejections/v1",
        "state": "PASS_NATIVE_COMPONENT_REJECTIONS" if passed else "INCOMPLETE_NATIVE_COMPONENT_REJECTIONS",
        "rows": rows,
        "hashes": {"auditor": sha256(Path(__file__)),
                   "positive_geometry": sha256(args.positive_case / "geometry.xml"),
                   "positive_track": sha256(args.positive_case / "tracks.h5"),
                   "binary": sha256(args.binary),
                   "library": sha256(args.library)},
        "claim_boundary": "Three edited copies of one previously passing void-only geometry were rejected natively before a track could be produced. These are selected malformed-input controls, not exhaustive parser or geometry coverage."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
