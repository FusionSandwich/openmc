"""Audit native facet-set registration and identity rejection without transport."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import h5py
import numpy as np

import openmc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], env: dict[str, str]) -> dict:
    result = subprocess.run(command, env=env, capture_output=True,
                            text=True, timeout=120, check=False)
    return {"command": command, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--payload-receipt", required=True, type=Path)
    parser.add_argument("--accepted-receipt", type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    source_receipt = json.loads(args.payload_receipt.read_text())
    accepted = source_receipt["schema"] == "stellarcsg.p00-facet-payload/v1"
    derived = source_receipt["schema"] == "stellarcsg.periodic-p00-facet-candidate/v1"
    if not (accepted or derived) or source_receipt["output_h5_sha256"] != sha256(args.payload):
        raise ValueError("facet payload or fixture differs from its receipt")
    if accepted:
        if source_receipt["input_sha256"]["fixture"] != sha256(args.fixture):
            raise ValueError("accepted facet fixture differs")
    else:
        if args.accepted_receipt is None:
            raise ValueError("derived payload requires --accepted-receipt")
        ancestor = json.loads(args.accepted_receipt.read_text())
        if (source_receipt["input_hashes"]["accepted_receipt"]
                != sha256(args.accepted_receipt)
                or source_receipt["input_hashes"]["accepted_payload"]
                != ancestor["output_h5_sha256"]
                or ancestor["input_sha256"]["fixture"] != sha256(args.fixture)):
            raise ValueError("derived facet ancestry or fixture differs")
    identity = source_receipt["content_id"]
    args.output.mkdir(parents=True)
    summary = args.output / "statepoint-facet.h5"
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(args.library.resolve().parent)
    env["OMP_NUM_THREADS"] = "1"
    loader = run(["ldd", str(args.binary.resolve())], env)
    bindings = [line.strip() for line in loader["stdout"].splitlines()
                if "libopenmc.so" in line]
    if (loader["exit_code"] or len(bindings) != 1
            or str(args.library.resolve()) not in bindings[0]):
        raise ValueError("native helper is not bound to the selected OpenMC library")
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    command = [str(args.binary.resolve()), str(args.payload.resolve()),
               identity, str(args.fixture.resolve()), str(summary)]
    positive = run(command, env)
    rows = [json.loads(line) for line in positive["stdout"].splitlines()]
    registered = (positive["exit_code"] == 0 and not positive["stderr"]
                  and rows == [{"native_registered": True,
                                "inside_probes": 54, "outside_probes": 54,
                                "transport_run": False}])
    serialized = False
    python_roundtrip = False
    if registered and summary.is_file():
        with h5py.File(summary, "r") as handle:
            group = handle["surface 9901"]
            def text(name: str) -> str:
                value = group[name][()]
                return value.decode() if isinstance(value, bytes) else str(value)
            serialized = (text("type") == "facet-set"
                          and text("dataset") == "/facets/one_period"
                          and text("content_id") == identity
                          and text("data_file") == str(args.payload.resolve()))
            imported = openmc.Surface.from_hdf5(group)
            python_roundtrip = (
                isinstance(imported, openmc.FacetSetSurface)
                and imported.content_id == identity
                and imported.bounding_box('-').lower_left.size == 3)
    wrong_id = run([str(args.binary.resolve()), str(args.payload.resolve()),
                    "sha256:" + "0" * 64, str(args.fixture.resolve()),
                    str(args.output / "wrong-id-statepoint.h5")], env)
    tampered = args.output / "tampered-one-ulp.h5"
    shutil.copyfile(args.payload, tampered)
    with h5py.File(tampered, "r+") as handle:
        vertices = handle["facets/one_period/triangle_vertices"]
        vertices[0, 0, 0] = np.nextafter(vertices[0, 0, 0], np.inf)
    tamper = run([str(args.binary.resolve()), str(tampered), identity,
                  str(args.fixture.resolve()),
                  str(args.output / "tampered-statepoint.h5")], env)
    inverted = args.output / "inward-winding.h5"
    shutil.copyfile(args.payload, inverted)
    with h5py.File(inverted, "r+") as handle:
        group = handle["facets/one_period"]
        vertices = group["triangle_vertices"][:]
        vertices[:, [1, 2]] = vertices[:, [2, 1]]
        group["triangle_vertices"][:] = vertices
        components = group["component_ids"][:]
        metadata = group.attrs["canonical_metadata_json"]
        if isinstance(metadata, bytes):
            metadata = metadata.decode()
        digest = hashlib.sha256(metadata.encode())
        digest.update(vertices.astype("<f8").tobytes())
        digest.update(components.astype("<i4").tobytes())
        inverted_id = "sha256:" + digest.hexdigest()
        group.attrs["content_id"] = inverted_id
    inversion = run([str(args.binary.resolve()), str(inverted), inverted_id,
                     str(args.fixture.resolve()),
                     str(args.output / "inward-statepoint.h5")], env)
    wrong_error = re.sub(r"\s+", " ", wrong_id["stderr"])
    tamper_error = re.sub(r"\s+", " ", tamper["stderr"])
    wrong_rejected = (wrong_id["exit_code"] != 0
                      and "Facet content_id mismatch" in wrong_error
                      and not (args.output / "wrong-id-statepoint.h5").exists())
    tamper_rejected = (tamper["exit_code"] != 0
                       and "Facet canonical payload SHA-256 does not verify"
                       in tamper_error
                       and not (args.output / "tampered-statepoint.h5").exists())
    inversion_rejected = (
        inversion["exit_code"] != 0
        and "Each connected facet shell must wind outward"
        in re.sub(r"\s+", " ", inversion["stderr"])
        and not (args.output / "inward-statepoint.h5").exists())
    passed = (registered and serialized and python_roundtrip
              and wrong_rejected and tamper_rejected and inversion_rejected)
    receipt = {
        "schema": "stellarcsg.native-facet-selector/v1",
        "state": "PASS_NATIVE_REGISTRATION_ONLY" if passed else "FAIL",
        "payload_classification": source_receipt["classification"],
        "positive": positive, "wrong_expected_id": wrong_id,
        "tampered_payload": tamper,
        "inward_winding": inversion,
        "native_registered": registered,
        "statepoint_serialized": serialized,
        "python_statepoint_roundtrip": python_roundtrip,
        "wrong_id_rejected": wrong_rejected,
        "tamper_rejected": tamper_rejected,
        "inward_winding_rejected": inversion_rejected,
        "loader_binding": bindings[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {
            "binary": sha256(args.binary),
            "library": sha256(args.library),
            "helper_source": sha256(args.source),
            "auditor": sha256(Path(__file__)),
            "payload": sha256(args.payload),
            "payload_receipt": sha256(args.payload_receipt),
            "accepted_receipt": sha256(args.accepted_receipt)
            if args.accepted_receipt else None,
            "fixture": sha256(args.fixture),
            "statepoint": sha256(summary) if summary.is_file() else None,
            "tampered_payload": sha256(tampered),
            "inward_winding_payload": sha256(inverted),
        },
        "claim_boundary": "Native OpenMC facet-set registration, 108 P00 reference probe sides, selector serialization and Python readback, plus wrong-ID, one-ULP tamper and hash-valid inward-winding rejection. Payload classification distinguishes accepted H5M facets from the derived periodic candidate. No particle transport, continuous CAD bound, overlap proof or performance qualification."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"],
                      "native_registered": registered,
                      "wrong_id_rejected": wrong_rejected,
                      "tamper_rejected": tamper_rejected,
                      "inward_winding_rejected": inversion_rejected}))
    if not passed:
        raise RuntimeError("native facet selector audit failed")


if __name__ == "__main__":
    main()
