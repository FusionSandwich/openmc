from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[2] / "benchmarks" / "common_accuracy.py"
SPEC = importlib.util.spec_from_file_location("common_accuracy", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_identical_finite_surface_is_exact():
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    normals = np.tile([0.0, 0.0, 1.0], (3, 1))
    result = MODULE.finite_surface_metrics(points, points.copy(), normals, normals.copy())
    assert result == {
        "hausdorff_two_sided_cm": 0.0,
        "surface_distance_rms_cm": 0.0,
        "surface_distance_p95_cm": 0.0,
        "normal_angle_max_deg": 0.0,
    }


def test_two_sided_metric_detects_unmatched_extent():
    authoritative = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    candidate = np.array([[0.0, 0.0, 0.0]])
    result = MODULE.finite_surface_metrics(authoritative, candidate)
    assert result["hausdorff_two_sided_cm"] == 10.0


def test_root_metrics_distinguish_wrong_missed_and_false():
    authoritative = np.array([1.0, 2.0, np.inf, 4.0])
    candidate = np.array([1.0, 2.2, 3.0, np.inf])
    result = MODULE.root_metrics(authoritative, candidate, tolerance_cm=0.1)
    assert result["wrong_roots"] == 1
    assert result["missed_roots"] == 1
    assert result["false_hits"] == 1
    assert np.isclose(result["root_distance_max_cm"], 0.2)
