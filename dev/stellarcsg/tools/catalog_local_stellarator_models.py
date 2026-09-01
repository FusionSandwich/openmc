#!/usr/bin/env python3
"""Create a provenance-preserving catalog from an explicit local model index.

The scanner intentionally does not crawl a home directory.  It consumes an
explicit campaign manifest, hashes only referenced files, and reads VMEC NFP
from each equilibrium file.  It copies no source geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from scipy.io import netcdf_file


DEVICE_CLASSES = {
    "wistell_d": "stellarator reactor study",
    "fpp11p5": "stellarator reactor study",
    "qa_nfp1": "QA",
    "qa_nfp2": "QA",
    "qa_nfp3": "QA",
    "qa_nfp4": "QA",
    "qa_nfp5": "QA",
    "qa_nfp6": "QA",
    "qa_nfp7": "QA",
    "landreman_paul_qa": "QA",
    "qh_simple_scaled": "QH",
    "n3are_r7p75_b5p7": "stellarator equilibrium",
    "ncsx_c09r00": "QA",
    "helias5b": "HELIAS / QI-like",
    "w7x_standard": "HELIAS / QI-like",
}

ALIASES = {
    "wistell_d": ["WISTELL-D"],
    "fpp11p5": ["FPP11.5", "FP11", "FPP11pt5"],
    "landreman_paul_qa": ["Landreman-Paul QA", "LandremanPaul2021 QA"],
    "ncsx_c09r00": ["NCSX", "C09R00"],
    "helias5b": ["HELIAS 5B-like", "HELIAS5"],
    "w7x_standard": ["W7-X standard", "W7X standard"],
}

SAME_LINEAGE = {
    "wistell_d": True,
    "fpp11p5": True,
    "helias5b": True,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_git(path: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value or None


def repository_provenance(path: Path) -> tuple[str | None, str | None, str | None]:
    candidate = path.parent.resolve()
    git_parent: Path | None = None
    for parent in (candidate, *candidate.parents):
        marker = parent / ".git"
        if marker.is_dir() or marker.is_file():
            git_parent = parent
            break
    if git_parent is None:
        return None, None, None
    top_text = run_git(git_parent, "rev-parse", "--show-toplevel")
    if top_text is None:
        return None, None, None
    top = Path(top_text)
    commit = run_git(top, "rev-parse", "HEAD")
    repository = run_git(top, "remote", "get-url", "origin") or str(top)
    licenses: list[str] = []
    for pattern in ("LICENSE*", "COPYING*", "NOTICE*"):
        licenses.extend(str(item) for item in top.glob(pattern) if item.is_file())
    return repository, commit, "; ".join(sorted(set(licenses))) or None


def read_vmec_nfp(path: Path) -> int:
    # NFP is a scalar. Memory mapping avoids loading every large equilibrium
    # array merely to read this value.
    with netcdf_file(path, "r", mmap=True) as dataset:
        if "nfp" not in dataset.variables:
            raise ValueError(f"VMEC file has no nfp variable: {path}")
        return int(dataset.variables["nfp"].data.item())


def read_coil_nfp(path: Path) -> tuple[int | None, str | None]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            head = "".join(stream.readline() for _ in range(200))
    except OSError:
        return None, None
    patterns = (
        r"(?im)^\s*periods?\s*[:=]?\s*(\d+)\b",
        r"(?im)^\s*nfp\s*[:=]?\s*(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, head)
        if match:
            return int(match.group(1)), f"declared in {path.name}"
    return None, None


def angular_extent(nfp: int | None, kind: str) -> str | None:
    if nfp is None:
        return None
    if kind == "plasma":
        return f"VMEC Fourier equilibrium; full device implied by in-file nfp={nfp}"
    return f"coil file declares nfp={nfp}; full device extent depends on listed filament set"


def component_entry(record: dict[str, Any], kind: str, path: Path) -> dict[str, Any]:
    record_id = record["id"]
    paired_plasma = bool(record.get("wout") and Path(record["wout"]).is_file())
    paired_coil = bool(record.get("coils") and Path(record["coils"]).is_file())
    if kind == "plasma":
        nfp = read_vmec_nfp(path)
        nfp_source = f"variable nfp in {path.name}"
        units = "m (VMEC convention)"
    else:
        nfp, nfp_source = read_coil_nfp(path)
        units = None

    manifest_nfp = int(record["nfp"])
    if nfp is not None and nfp != manifest_nfp:
        raise ValueError(
            f"NFP mismatch for {path}: file={nfp}, manifest={manifest_nfp}"
        )

    repository, commit, license_evidence = repository_provenance(path)
    plot = Path(record["plot"]) if record.get("plot") else None
    h5m_available = bool(plot and plot.parent.is_dir() and next(plot.parent.glob("*.h5m"), None))
    blanket_available = record_id == "wistell_d" and any(
        candidate.is_file()
        for candidate in (
            path.parent / "blanket_boundary.npy",
            path.parent / "nwl.npy",
        )
    )
    notes = [
        f"component={kind}",
        f"campaign_family={record.get('family', 'unknown')}",
        f"manifest_nfp={manifest_nfp}",
    ]
    if nfp is None:
        notes.append("NFP was not readable from this component file; do not infer it from the filename")
    if kind == "coil" and record.get("coil_note"):
        notes.append(record["coil_note"])

    already_public_fixture = "dev\\stellarcsg\\test_data" in str(path).lower()
    return {
        "configuration_name": record["label"],
        "aliases": sorted(set([record_id, *ALIASES.get(record_id, [])])),
        "device_class": DEVICE_CLASSES.get(record_id, "unknown"),
        "source_repository": repository,
        "source_commit": commit,
        "local_path": str(path),
        "sha256": sha256(path),
        "file_type": path.suffix.lower().lstrip(".") or "unknown",
        "bytes": path.stat().st_size,
        "nfp": nfp,
        "nfp_source": nfp_source,
        "modeled_angular_extent": angular_extent(nfp, kind),
        "plasma_available": paired_plasma,
        "coil_available": paired_coil,
        "blanket_available": blanket_available,
        "dagmc_h5m_available": h5m_available,
        "units": units,
        "license_evidence": license_evidence,
        "reuse_evidence": "Explicit path in stellarcsg.multiconfig-atlas/v1 campaign manifest",
        "provenance_confidence": "high" if commit and license_evidence else "medium",
        "plasma_coil_same_lineage": SAME_LINEAGE.get(record_id),
        "public_fixture_suitability": "yes" if already_public_fixture else "unknown",
        "local_test_suitability": "yes",
        "qualification_status": record.get("classification", "NOT_ASSESSED"),
        "notes": notes,
    }


def markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# Local stellarator model catalog",
        "",
        f"Generated `{catalog['generated_at']}` from an explicit local campaign index.",
        "No source geometry was copied. Paths and hashes describe local-only inputs;",
        "`public fixture = unknown` means redistribution was not established.",
        "",
        "| Configuration | Component | Class | NFP read from file | Status | SHA-256 | Bytes | Public fixture |",
        "|---|---|---|---:|---|---|---:|---|",
    ]
    for entry in catalog["entries"]:
        component = next(
            note.split("=", 1)[1]
            for note in entry["notes"]
            if note.startswith("component=")
        )
        nfp = entry["nfp"] if entry["nfp"] is not None else "—"
        lines.append(
            "| {configuration_name} | {component} | {device_class} | {nfp_display} | "
            "{qualification_status} | `{short_hash}` | {bytes} | {public_fixture_suitability} |".format(
                component=component,
                nfp_display=nfp,
                short_hash=entry["sha256"][:16],
                **entry,
            )
        )
    lines.extend(
        [
            "",
            "## Qualification boundary",
            "",
            "The statuses above are retained prior single-chart admissibility results,",
            "not dual-track performance qualification. Coil-file NFP remains null when",
            "the coil file does not declare periods/NFP; the paired VMEC record supplies",
            "the independently read equilibrium NFP. License-unclear files remain local.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--search-root",
        action="append",
        default=[],
        help="Additional explicitly inspected root to retain in the catalog",
    )
    args = parser.parse_args()

    source = json.loads(args.manifest.read_text(encoding="utf-8"))
    if source.get("schema") != "stellarcsg.multiconfig-atlas/v1":
        raise ValueError("unsupported source campaign schema")

    entries: list[dict[str, Any]] = []
    missing: list[str] = []
    for record in source["records"]:
        for kind, key in (("plasma", "wout"), ("coil", "coils")):
            value = record.get(key)
            if not value:
                continue
            path = Path(value)
            if not path.is_file():
                missing.append(str(path))
                continue
            entries.append(component_entry(record, kind, path))

    if missing:
        raise FileNotFoundError("manifest references missing files:\n" + "\n".join(missing))

    search_roots = sorted(
        set(args.search_root)
        | {
            str(Path(record[key]).anchor + Path(record[key]).parts[1])
            for record in source["records"]
            for key in ("wout", "coils")
            if record.get(key)
        }
    )
    catalog = {
        "schema_version": "stellarcsg.local-geometry-catalog/v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "search_roots": search_roots,
        "entries": entries,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "LOCAL_STELLARATOR_MODEL_CATALOG.json").write_text(
        json.dumps(catalog, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "LOCAL_STELLARATOR_MODEL_CATALOG.md").write_text(
        markdown(catalog), encoding="utf-8"
    )
    print(f"cataloged {len(entries)} files across {len(source['records'])} configurations")


if __name__ == "__main__":
    main()
