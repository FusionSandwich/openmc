"""Compare priority and union P00 material-bank tracks bit for bit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import h5py


PRIORITY_RECEIPT_SHA256 = "d70216c45c454feef68e20d76318ee77b79772764760ce3a4a8bb3644842a5da"
UNION_RECEIPT_SHA256 = "e5f210464a2bc23f8ff63ea7a34ac341a154d0683a56bb32946d14dd69607d0e"
PHYSICAL_FIELDS = ("r", "u", "E", "time", "wgt", "cell_instance", "material_id")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--priority", type=Path, required=True)
    parser.add_argument("--union", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new file")
    priority_receipt = args.priority / "receipt.json"
    union_receipt = args.union / "receipt.json"
    if (sha256(priority_receipt) != PRIORITY_RECEIPT_SHA256
            or sha256(union_receipt) != UNION_RECEIPT_SHA256):
        raise ValueError("material-bank receipts differ")
    priority = json.loads(priority_receipt.read_text())
    union = json.loads(union_receipt.read_text())
    if (priority["state"] != "PASS_SAMPLED_18_MAGNET_MATERIAL_ENTRIES"
            or union["state"] != "PASS_SAMPLED_18_MAGNET_UNION_ENTRIES"
            or priority["histories"] != 360
            or union["histories"] != 360):
        raise ValueError("bank completion identity differs")
    for folder, receipt in ((args.priority, priority), (args.union, union)):
        for name in ("source.h5", "geometry.xml", "materials.xml", "settings.xml",
                     "tracks.h5", "statepoint.1.h5", "summary.h5"):
            if sha256(folder / name) != receipt["hashes"][name]:
                raise ValueError(f"changed {folder / name}")
    if (priority["hashes"]["source.h5"] != union["hashes"]["source.h5"]
            or priority["hashes"]["materials.xml"]
            != union["hashes"]["materials.xml"]):
        raise ValueError("material/source inputs differ")
    priority_xml = ET.parse(args.priority / "geometry.xml").getroot()
    union_xml = ET.parse(args.union / "geometry.xml").getroot()
    priority_cells = {int(cell.get("id")): cell
                      for cell in priority_xml.findall(".//cell")}
    union_cells = {int(cell.get("id")): cell
                   for cell in union_xml.findall(".//cell")}
    if (set(priority_cells) != {2000, *range(2008, 2026)}
            or set(union_cells) != {2000, 2001}
            or priority_cells[2000].get("material") != "void"
            or union_cells[2000].get("material") != "void"
            or union_cells[2001].get("material") != "7"
            or any(priority_cells[i].get("material") != "7"
                   for i in range(2008, 2026))):
        raise ValueError("material cell sets differ")
    first_surfaces = {int(surface.get("id")): ET.tostring(surface)
                      for surface in priority_xml.findall(".//surface")}
    second_surfaces = {int(surface.get("id")): ET.tostring(surface)
                       for surface in union_xml.findall(".//surface")}
    if first_surfaces != second_surfaces:
        raise ValueError("material runs use different surfaces")
    sector = "901 902 -904 905 -906"
    positives = [str(i) for i in range(1108, 1126)]
    if (priority_cells[2000].get("region") != sector + " " + " ".join(positives)
            or union_cells[2000].get("region")
            != priority_cells[2000].get("region")
            or union_cells[2001].get("region")
            != sector + " (" + " | ".join("-" + i for i in positives) + ")"):
        raise ValueError("union/complement region expression differs")
    for offset in range(18):
        expected = sector + " " + " ".join(positives[:offset]
                                            + ["-" + positives[offset]])
        if priority_cells[2008 + offset].get("region") != expected:
            raise ValueError(f"priority region {2008 + offset} differs")
    for positive_mask in range(1 << 18):
        priority_owners = sum(
            bool(positive_mask & ((1 << offset) - 1) == (1 << offset) - 1
                 and not positive_mask & (1 << offset))
            for offset in range(18))
        union_owner = positive_mask != (1 << 18) - 1
        if priority_owners != int(union_owner):
            raise ValueError("Boolean priority/union partition differs")
    n = priority["histories"]
    matched = {field: 0 for field in PHYSICAL_FIELDS}
    cell_differences = 0
    failures = []
    with h5py.File(args.priority / "tracks.h5") as first, h5py.File(
            args.union / "tracks.h5") as second:
        required = {f"track_1_1_{i}" for i in range(1, n + 1)}
        if set(first) != required or set(second) != required:
            raise ValueError("track history set differs")
        for i in range(1, n + 1):
            key = f"track_1_1_{i}"
            a, b = first[key][:], second[key][:]
            if len(a) != len(b) or a.dtype != b.dtype:
                failures.append({"history": i, "reason": "track_shape"})
                continue
            for field in PHYSICAL_FIELDS:
                if a[field].tobytes() == b[field].tobytes():
                    matched[field] += 1
                else:
                    failures.append({"history": i, "field": field})
            if a["cell_id"].tobytes() != b["cell_id"].tobytes():
                cell_differences += 1
            else:
                failures.append({"history": i, "reason": "cell_id_not_distinct"})
            if (a["cell_id"][0] != 2000 or b["cell_id"][0] != 2000
                    or b["cell_id"][1] != 2001
                    or a["cell_id"][1] not in range(2008, 2026)
                    or a["material_id"][1] != 7
                    or b["material_id"][1] != 7):
                failures.append({"history": i, "reason": "first_entry"})
    passed = (not failures and cell_differences == n
              and all(value == n for value in matched.values()))
    receipt = {
        "schema": "stellarcsg.p00-magnet-union-equivalence/v1",
        "state": "PASS_BITWISE_TRACK_PHYSICS_360" if passed
                 else "INCOMPLETE_TRACK_PHYSICS_COMPARISON",
        "histories": n,
        "boolean_surface_sign_cases": 1 << 18,
        "boolean_union_partition_pass": True,
        "bitwise_identical_histories_by_field": matched,
        "histories_with_distinct_cell_ids": cell_differences,
        "failures": failures,
        "hashes": {"auditor": sha256(Path(__file__)),
                   "priority_receipt": sha256(priority_receipt),
                   "union_receipt": sha256(union_receipt),
                   "priority_tracks": sha256(args.priority / "tracks.h5"),
                   "union_tracks": sha256(args.union / "tracks.h5")},
        "claim_boundary": "The actual XML priority partition and common-material union have the same magnet Boolean occupancy for every one of the 2^18 resolved surface-sign assignments inside the sector. For the same 360 sampled source histories, every stored position, direction, energy, time, weight, cell-instance and material-ID track field is byte-identical; cell IDs differ by construction. This is topological equivalence of the represented Boolean cells and sampled local transport equivalence, not a proof at unresolved surface coincidences, a winding-pack CAD/clearance certificate, a statistical tally comparison, or a matched speed benchmark.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
