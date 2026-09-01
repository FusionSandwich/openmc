from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


HARNESS = Path(__file__).parents[2] / "benchmarks" / "dual_track_harness.py"
SPEC = importlib.util.spec_from_file_location("dual_track_harness", HARNESS)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_summary_retains_required_statistics():
    result = MODULE.summary([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["median"] == 3.0
    assert result["mean"] == 3.0
    assert result["iqr"] == 2.0
    assert result["coefficient_of_variation"] > 0.0


def test_balanced_schedule_rotates_each_method_through_first_position():
    result = MODULE.schedule(["a", "b", "c"], 9, "balanced", 17)
    assert len(result) == 9
    assert all(sorted(row) == ["a", "b", "c"] for row in result)
    first_counts = {name: sum(row[0] == name for row in result) for name in "abc"}
    assert max(first_counts.values()) - min(first_counts.values()) <= 1


def test_schedule_rejects_too_few_repetitions():
    with pytest.raises(ValueError, match="seven"):
        MODULE.schedule(["a", "b"], 6, "balanced", 1)


def test_paired_bootstrap_identity_is_exact():
    interval = MODULE.paired_bootstrap_ratio(
        [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0],
        [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0],
        seed=9,
        samples=1000,
    )
    assert interval == [1.0, 1.0]
