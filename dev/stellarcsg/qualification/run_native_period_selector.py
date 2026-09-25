"""Check the provisional one-period member list through native OpenMC import."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import h5py

source_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(source_root))
import openmc

if Path(openmc.__file__).resolve().parents[1] != source_root:
    raise RuntimeError("Native selector must round-trip with this checkout's OpenMC Python")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--h5", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    for path in (args.binary, args.library, args.h5, args.manifest, args.source):
        if not path.is_file():
            parser.error(f"missing input: {path}")
    if args.output.exists():
        parser.error("output must be new")
    manifest = json.loads(args.manifest.read_text())
    if manifest["schema"] != "stellarcsg.period-candidate-manifest/v1" or \
            manifest["input_hashes"]["h5_sha256"] != sha256(args.h5):
        raise ValueError("candidate manifest is not bound to the HDF5 input")
    selected = [row for row in manifest["members"] if row["sector_candidate"]]
    indices = [row["coil_id"] for row in selected]
    content_ids = [row["content_id"] for row in selected]
    if len(indices) != manifest["sector_candidate_count"] or len(indices) != 18 \
            or len(indices) != len(set(indices)) or any(
                row["dataset"] != f"/coils/coil_{row['coil_id']:03d}"
                for row in selected):
        raise ValueError("manifest has an invalid provisional member selection")
    selection = " ".join(map(str, indices))
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(args.library.resolve().parent)
    env["OMP_NUM_THREADS"] = "1"
    loader = subprocess.run(["ldd", str(args.binary.resolve())], text=True,
                            capture_output=True, timeout=10, env=env, check=False)
    bindings = [line.strip() for line in loader.stdout.splitlines()
                if "libopenmc.so" in line]
    if loader.returncode or len(bindings) != 1 or \
            str(args.library.resolve()) not in bindings[0]:
        raise RuntimeError("native helper is not bound to the selected libopenmc.so")
    args.output.mkdir(parents=True)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    summary = args.output / "statepoint-selector.h5"
    command = [str(args.binary.resolve()), str(args.h5.resolve()),
               selection, str(summary.resolve())]
    result = subprocess.run(command, text=True, capture_output=True,
                            timeout=120, env=env, check=False)
    (args.output / "stdout.jsonl").write_text(result.stdout)
    (args.output / "stderr.txt").write_text(result.stderr)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    registered = result.returncode == 0 and len(rows) == 1 and \
        rows[0].get("native_registered") is True and \
        rows[0].get("transport_run") is False
    serialized = False
    identities_serialized = False
    python_roundtrip = False
    if registered and summary.is_file():
        with h5py.File(summary, "r") as handle:
            group = handle["surface 9801"]
            value = group["dataset_indices"][()]
            if isinstance(value, bytes):
                value = value.decode()
            serialized = (value == selection and "dataset_count" not in group
                          and "dataset_start" not in group)
            identities = group["member_content_ids"][()]
            if isinstance(identities, bytes):
                identities = identities.decode()
            identities_serialized = identities == " ".join(content_ids)
            imported = openmc.Surface.from_hdf5(group)
            python_roundtrip = (
                isinstance(imported, openmc.SweptSplineSurface)
                and imported.dataset_indices == tuple(indices)
                and imported.member_content_ids == tuple(content_ids)
                and imported.dataset_prefix == "/coils/coil_"
                and imported.data_file == str(args.h5.resolve()))
    receipt = {
        "schema": "stellarcsg.native-period-selector/v1",
        "state": "PASS_REPRESENTATION_ONLY" if registered and serialized
                 and identities_serialized
                 and python_roundtrip else "FAIL",
        "command": command,
        "exit_code": result.returncode,
        "loader_binding": bindings[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "selected_member_ids": indices,
        "selected_member_content_ids": content_ids,
        "selected_member_count": len(indices),
        "native_registered": registered,
        "statepoint_selector_roundtrip": serialized,
        "statepoint_member_content_ids_roundtrip": identities_serialized,
        "python_statepoint_roundtrip": python_roundtrip,
        "native_transport_run": False,
        "hashes": {str(path.resolve()): sha256(path) for path in
                   (args.binary, args.library, args.h5, args.manifest,
                    args.source, Path(__file__), source_root / "openmc/surface.py")},
        "statepoint_sha256": sha256(summary) if summary.is_file() else None,
        "python_openmc_source": str(Path(openmc.__file__).resolve()),
        "claim_boundary": "Native registration, ordered member-ID serialization and Python readback of the 18 provisional whole-coil candidates only; no seam ownership, clipping, material transport or root proof.",
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "selected": len(indices)}))
    return 0 if receipt["state"] == "PASS_REPRESENTATION_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
