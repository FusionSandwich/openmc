"""Prepare a hash-bound local triangle/probe fixture from accepted P00 records."""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--h5m", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    catalog_hash = sha256(args.catalog)
    bank_hash = sha256(args.bank)
    h5m_hash = sha256(args.h5m)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    expected = bank["input_sha256"]
    if catalog_hash != expected["facet_catalog"]:
        raise ValueError("facet catalog hash differs from accepted probe bank")
    if h5m_hash != expected["dagmc_h5m"]:
        raise ValueError("H5M hash differs from accepted probe bank")
    if catalog["dagmc_file"]["sha256"] != h5m_hash:
        raise ValueError("facet catalog does not identify this H5M")
    if catalog["magnet_count"] != 18 or catalog["facet_count"] != 3348:
        raise ValueError("unexpected accepted P00 facet counts")

    lines = [str(catalog["facet_count"])]
    facet_count = 0
    for magnet in catalog["magnets"]:
        for facet in magnet["facets"]:
            vertices = facet["triangle_vertices_global_cm"]
            values = [magnet["dagmc_volume_id"]]
            values.extend(value for vertex in vertices for value in vertex)
            lines.append(" ".join(map(repr, values)))
            facet_count += 1
    if facet_count != catalog["facet_count"]:
        raise ValueError("catalog facet count mismatch")

    probes = [(row["dagmc_volume_id"], probe["side"], probe["point_cm"])
              for row in bank["rows"] for probe in row["probes"]]
    if len(probes) != bank["probe_count"] or len(probes) != 108:
        raise ValueError("accepted probe count mismatch")
    if {side for _, side, _ in probes} != {"inside", "outside"}:
        raise ValueError("unexpected accepted probe side labels")
    lines.append(str(len(probes)))
    lines.extend(" ".join(map(repr, [component, int(side == "inside"), *point]))
                 for component, side, point in probes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(("\n".join(lines) + "\n").encode("ascii"))

    receipt = {
        "schema": "stellarcsg.p00-facet-fixture/v1",
        "claim_boundary": "Hash-bound accepted mesh catalog and inside/outside probe input for the standalone triangle kernel; not a CAD or continuous swept-surface certification.",
        "catalog_sha256": catalog_hash,
        "bank_sha256": bank_hash,
        "h5m_sha256": h5m_hash,
        "fixture_sha256": sha256(args.output),
        "facet_count": facet_count,
        "probe_count": len(probes),
    }
    receipt_path = args.output.with_suffix(args.output.suffix + ".receipt.json")
    receipt_path.write_bytes((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
