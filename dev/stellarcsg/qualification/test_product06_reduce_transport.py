from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("product06_reduce_transport.py")
SPEC = importlib.util.spec_from_file_location("product06_reduce", SCRIPT)
reducer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(reducer)


def _attempt(lane: str, *, flux: float, hps: float, complete: bool = True) -> dict:
    return {"lane": lane, "seed": 17, "completion": "COMPLETE" if complete else "INCOMPLETE", "warnings": ["warning retained"],
            "statepoint": {"metrics_valid": complete, "histories_per_active_second": hps,
            "n_particles": 64, "runtime_seconds": {"active batches": 2.0, "total initialization": 0.1, "transport": 1.0}, "global_flux": flux,
            "flux_closure_absolute": 0.01, "cell_bins": [10, 2001], "cell_flux": [1.0, flux - 1.0]}}


def test_descriptive_reduction_keeps_pairs_and_incomplete_state() -> None:
    receipt = {"schema": "source", "attempts": [_attempt("exact", flux=3.0, hps=30.0), _attempt("old", flux=3.1, hps=20.0), _attempt("recovered", flux=3.0, hps=40.0, complete=False)],
               "comparisons": [{"seed": 17, "status": "WITHIN_PRESPECIFIED_TOLERANCE", "raw_differences": [{"metric": "global_flux", "signed": 1e-13}]}]}
    result = reducer.reduce_receipt(receipt)
    assert result["per_lane"]["old"]["completed_count"] == 1
    assert result["per_lane"]["recovered"]["incomplete_count"] == 1
    old = result["per_seed_pairs"][0]["lanes"]["old"]
    assert old["active_hps_ratio_lane_over_exact"] == 20.0 / 30.0
    assert old["cell_tally_differences_against_exact"][1]["signed"] == pytest.approx(0.1)
    assert result["per_lane"]["old"]["median_initialization_runtime_seconds"] == 0.1
    assert result["per_lane"]["old"]["median_histories_per_transport_second"] == 64.0
    assert result["per_seed_pairs"][0]["recovered_over_old_transport_runtime_ratio"] is None
    assert result["source_comparison_raw_differences"][0]["raw_differences"][0]["signed"] == 1e-13
    assert "not production-throughput" in result["timing_boundary"]


def test_recovered_over_old_transport_ratio_is_descriptive() -> None:
    receipt = {"attempts": [_attempt("exact", flux=3.0, hps=30.0), _attempt("old", flux=3.0, hps=20.0), _attempt("recovered", flux=3.0, hps=40.0)]}
    result = reducer.reduce_receipt(receipt)
    assert result["per_seed_pairs"][0]["recovered_over_old_transport_runtime_ratio"] == 1.0
