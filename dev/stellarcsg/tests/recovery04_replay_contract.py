"""Lightweight contract checks for a frozen recovery04 CSV and JSON receipt."""
from __future__ import annotations

import csv
import json
from pathlib import Path


def validate_bank(path: Path) -> None:
    rows = list(csv.DictReader(path.open(newline="", encoding="ascii")))
    assert len(rows) == 160
    assert len({row["id"] for row in rows}) == 160
    assert any(row["geometry"] == "wistell_coil031" for row in rows)
    required = {"clear_miss", "transverse", "inside", "near_entry_002",
                "near_entry_502", "competing_roots", "seam", "grazing",
                "tangent", "direction_scaling", "rigid_transform"}
    assert required <= {row["category"] for row in rows}
    assert any(row["heldout"] == "1" for row in rows)
    assert all(row["coefficient_hash"] for row in rows)
    wistell = [row for row in rows if row["geometry"] == "wistell_coil031"]
    assert wistell and all(row["source_sha256"] for row in wistell)


def validate_receipt(path: Path) -> None:
    receipt = json.loads(path.read_text(encoding="ascii"))
    assert receipt["repetitions"] == 7
    assert receipt["cache_policy"].startswith("one unique persisted bank")
    for side in ("archive", "latest"):
        assert len(receipt[side]) == 7
        for run in receipt[side]:
            assert run["summary"] is not None
            assert run["summary"]["query_count"] == 160
