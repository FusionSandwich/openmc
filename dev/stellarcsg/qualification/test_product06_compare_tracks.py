from __future__ import annotations

import importlib.util
from pathlib import Path

import h5py
import numpy as np


SCRIPT = Path(__file__).with_name("product06_compare_tracks.py")
SPEC = importlib.util.spec_from_file_location("product06_tracks", SCRIPT)
tracks = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(tracks)


DTYPE = np.dtype([("r", "f8", (3,)), ("u", "f8", (3,)), ("E", "f8"), ("time", "f8"), ("wgt", "f8"),
                  ("cell_id", "i4"), ("cell_instance", "i4"), ("material_id", "i4")])


def _write(path: Path, changed: bool = False) -> None:
    values = np.zeros(2, dtype=DTYPE)
    values[0]["r"] = [1.0, 2.0, 3.0]
    values[0]["u"] = [0.0, 1.0, 0.0]
    values[0]["E"] = 14.0
    values[0]["wgt"] = 1.0
    values[0]["cell_id"] = 10
    values[1]["cell_id"] = 11 if changed else 10
    values[1]["time"] = 1.0e-9 if changed else 0.0
    with h5py.File(path, "w") as handle:
        handle["track_1_1_17"] = values


def test_first_track_difference_preserves_raw_values(tmp_path) -> None:
    exact, candidate = tmp_path / "exact.h5", tmp_path / "candidate.h5"
    _write(exact)
    _write(candidate, changed=True)
    result = tracks.compare_lane(exact, candidate, 0.0)
    entry = result["shared"][0]
    assert entry["exact_step_count"] == 2
    assert entry["first_difference"]["event_index"] == 1
    assert entry["first_difference"]["fields"]["cell_id"]["candidate"] == 11
    assert entry["max_abs_differences"]["time"] == 1.0e-9


def test_campaign_keeps_missing_track_lane_status(tmp_path) -> None:
    exact = tmp_path / "seed-19" / "exact"
    exact.mkdir(parents=True)
    _write(exact / "tracks.h5")
    result = tracks.compare_campaign(tmp_path, 0.0)
    assert result["seeds"][0]["lanes"]["old"]["status"] == "TRACKS_MISSING"
