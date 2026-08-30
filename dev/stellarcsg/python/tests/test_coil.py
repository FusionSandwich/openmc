from __future__ import annotations

from pathlib import Path
import time

import h5py
import numpy as np

from stellarcsg.coil import (
    CapsuleTube,
    build_coil_local_mesh,
    resample_closed_centerline,
    rotation_minimizing_frames,
    write_coil_mesh_hdf5,
    write_coil_mesh_vtk,
)


def circular_centerline(radius: float, count: int = 192) -> np.ndarray:
    phi = 2.0 * np.pi * np.arange(count) / count
    return np.stack((radius * np.cos(phi), radius * np.sin(phi),
                     np.zeros_like(phi)), axis=-1)


def nonplanar_centerline(count: int = 256) -> np.ndarray:
    phi = 2.0 * np.pi * np.arange(count) / count
    radius = 25.0 + 3.0 * np.cos(3.0 * phi)
    return np.stack((radius * np.cos(phi), radius * np.sin(phi),
                     4.0 * np.sin(2.0 * phi)), axis=-1)


def test_capsule_tube_point_classification_and_normal() -> None:
    tube = CapsuleTube(circular_centerline(10.0), 1.0)
    assert tube.evaluate(np.asarray([11.0, 0.0, 0.0])) <= 2.0e-3
    assert tube.evaluate(np.asarray([10.0, 0.0, 0.0])) < 0.0
    assert tube.evaluate(np.asarray([14.0, 0.0, 0.0])) > 0.0
    normal = tube.normal(np.asarray([11.0, 0.0, 0.0]))
    np.testing.assert_allclose(normal, [1.0, 0.0, 0.0], atol=3.0e-3)


def test_capsule_bvh_matches_bruteforce_rays() -> None:
    tube = CapsuleTube(nonplanar_centerline(), 1.2, leaf_size=6)
    rng = np.random.default_rng(91573)
    candidate_counts = []
    for _ in range(600):
        origin = rng.uniform([-35.0, -35.0, -10.0], [35.0, 35.0, 10.0])
        direction = rng.normal(size=3)
        fast = tube.distance(origin, direction)
        reference = tube.distance_bruteforce(origin, direction)
        assert np.isfinite(fast) == np.isfinite(reference)
        if np.isfinite(fast):
            np.testing.assert_allclose(fast, reference, rtol=0.0, atol=3.0e-8)
        candidate_counts.append(tube.ray_candidates(origin, direction).size)
    assert np.mean(candidate_counts) < 0.45 * tube.n_segments


def test_inside_ray_returns_union_exit() -> None:
    tube = CapsuleTube(circular_centerline(10.0), 1.0)
    origin = np.asarray([10.0, 0.0, 0.0])
    assert tube.evaluate(origin) < 0.0
    distance = tube.distance(origin, [1.0, 0.0, 0.0])
    np.testing.assert_allclose(distance, 1.0, atol=2.0e-3)


def test_rotation_minimizing_frame_is_periodic() -> None:
    centerline = resample_closed_centerline(nonplanar_centerline(), 160)
    tangent, normal, binormal = rotation_minimizing_frames(centerline)
    np.testing.assert_allclose(np.linalg.norm(tangent, axis=1), 1.0, atol=2.0e-12)
    np.testing.assert_allclose(np.linalg.norm(normal, axis=1), 1.0, atol=2.0e-12)
    np.testing.assert_allclose(np.linalg.norm(binormal, axis=1), 1.0, atol=2.0e-12)
    assert np.max(np.abs(np.einsum("ij,ij->i", tangent, normal))) < 2.0e-12
    # No seam flip; the final and initial normal frames remain locally aligned.
    assert float(np.dot(normal[-1], normal[0])) > 0.95


def test_coil_local_mesh_and_export(tmp_path: Path) -> None:
    centerline = circular_centerline(10.0)
    mesh = build_coil_local_mesh(centerline, 1.0, arc_bins=64, u_bins=6, v_bins=6)
    assert mesh.n_elements == 64 * 6 * 6
    assert np.min(mesh.approximate_element_volumes_cm3()) > 0.0
    tube = CapsuleTube(mesh.centerline_cm, 1.0)
    assert np.max(tube.evaluate(mesh.element_centroids_cm())) < 1.0e-8
    h5_path = tmp_path / "coil_mesh.h5"
    vtk_path = tmp_path / "coil_mesh.vtk"
    write_coil_mesh_hdf5(h5_path, mesh)
    write_coil_mesh_vtk(vtk_path, mesh)
    with h5py.File(h5_path, "r") as h5:
        assert h5.attrs["filetype"] == "stellarcsg-coil-tally-mesh"
        assert h5["connectivity"].shape == (mesh.n_elements, 8)
    assert "CELL_TYPES" in vtk_path.read_text()


def test_bvh_is_faster_than_bruteforce_smoke() -> None:
    tube = CapsuleTube(nonplanar_centerline(768), 0.8, leaf_size=8)
    rng = np.random.default_rng(13579)
    origins = rng.uniform([-35.0, -35.0, -12.0], [35.0, 35.0, 12.0], size=(120, 3))
    directions = rng.normal(size=(120, 3))
    start = time.perf_counter()
    fast = [tube.distance(o, d) for o, d in zip(origins, directions)]
    fast_seconds = time.perf_counter() - start
    start = time.perf_counter()
    reference = [tube.distance_bruteforce(o, d) for o, d in zip(origins, directions)]
    reference_seconds = time.perf_counter() - start
    np.testing.assert_allclose(fast, reference, rtol=0.0, atol=3.0e-8)
    assert fast_seconds < reference_seconds
