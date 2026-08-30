"""CAD-free swept-coil geometry and coil-local tally meshes.

The first production-oriented magnet kernel uses a union of capsules around a
closed polyline.  This representation has an exact signed-distance function for
point classification and analytic ray/capsule intersections.  A bounding-volume
hierarchy (BVH) limits ray tests to nearby centerline segments.  It is a bounded
circular-cross-section prototype: rectangular and multilayer winding-pack
surfaces remain a later extension.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np

_EPS = np.finfo(np.float64).eps


def _as_points(points: np.ndarray) -> np.ndarray:
    value = np.asarray(points, dtype=np.float64)
    if value.ndim != 2 or value.shape[1] != 3 or value.shape[0] < 4:
        raise ValueError("closed centerline must have shape (n>=4, 3)")
    if not np.all(np.isfinite(value)):
        raise ValueError("centerline points must be finite")
    if np.linalg.norm(value[0] - value[-1]) <= 1.0e-12:
        value = value[:-1]
    if value.shape[0] < 4:
        raise ValueError("centerline has too few unique points")
    lengths = np.linalg.norm(np.roll(value, -1, axis=0) - value, axis=1)
    if np.any(lengths <= 1.0e-12):
        raise ValueError("centerline contains duplicate adjacent points")
    return np.ascontiguousarray(value)


def _normalize(vector: np.ndarray) -> np.ndarray:
    magnitude = np.linalg.norm(vector)
    if not np.isfinite(magnitude) or magnitude <= 0.0:
        raise ValueError("cannot normalize a zero or non-finite vector")
    return vector / magnitude


def _ray_aabb(origin: np.ndarray, direction: np.ndarray,
              lower: np.ndarray, upper: np.ndarray) -> tuple[float, float] | None:
    enter = 0.0
    leave = np.inf
    for axis in range(3):
        if abs(direction[axis]) <= 64.0 * _EPS:
            if origin[axis] < lower[axis] or origin[axis] > upper[axis]:
                return None
            continue
        inv = 1.0 / direction[axis]
        t0 = (lower[axis] - origin[axis]) * inv
        t1 = (upper[axis] - origin[axis]) * inv
        if t0 > t1:
            t0, t1 = t1, t0
        enter = max(enter, t0)
        leave = min(leave, t1)
        if leave < enter:
            return None
    return enter, leave


def _point_segment_distance(point: np.ndarray, start: np.ndarray,
                            delta: np.ndarray, length2: float) -> tuple[float, np.ndarray]:
    parameter = float(np.dot(point - start, delta) / length2)
    parameter = min(1.0, max(0.0, parameter))
    closest = start + parameter * delta
    return float(np.linalg.norm(point - closest)), closest


def _quadratic_roots(a: float, b: float, c: float,
                     tolerance: float = 1.0e-14) -> list[float]:
    if abs(a) <= tolerance:
        if abs(b) <= tolerance:
            return []
        return [-c / b]
    discriminant = b * b - 4.0 * a * c
    scale = max(b * b, abs(4.0 * a * c), 1.0)
    if discriminant < -tolerance * scale:
        return []
    discriminant = max(0.0, discriminant)
    root = np.sqrt(discriminant)
    # Numerically stable quadratic evaluation.
    q = -0.5 * (b + np.copysign(root, b))
    if q == 0.0:
        return [-b / (2.0 * a)]
    roots = [q / a, c / q]
    roots.sort()
    return roots


def _capsule_boundary_roots(origin: np.ndarray, direction: np.ndarray,
                            start: np.ndarray, end: np.ndarray,
                            radius: float) -> list[float]:
    delta = end - start
    length = float(np.linalg.norm(delta))
    axis = delta / length
    offset = origin - start
    axial_origin = float(np.dot(offset, axis))
    axial_direction = float(np.dot(direction, axis))
    transverse_origin = offset - axial_origin * axis
    transverse_direction = direction - axial_direction * axis
    roots: list[float] = []

    a = float(np.dot(transverse_direction, transverse_direction))
    b = 2.0 * float(np.dot(transverse_origin, transverse_direction))
    c = float(np.dot(transverse_origin, transverse_origin) - radius * radius)
    for root in _quadratic_roots(a, b, c):
        axial = axial_origin + root * axial_direction
        if -1.0e-10 * max(1.0, length) <= axial <= length + 1.0e-10 * max(1.0, length):
            roots.append(root)

    for center in (start, end):
        sphere_offset = origin - center
        b = 2.0 * float(np.dot(sphere_offset, direction))
        c = float(np.dot(sphere_offset, sphere_offset) - radius * radius)
        roots.extend(_quadratic_roots(1.0, b, c))

    accepted: list[float] = []
    length2 = length * length
    residual_tolerance = 2.0e-9 * max(1.0, radius)
    for root in roots:
        if root < -1.0e-11 or not np.isfinite(root):
            continue
        distance, _ = _point_segment_distance(
            origin + max(0.0, root) * direction, start, delta, length2)
        if abs(distance - radius) <= residual_tolerance:
            accepted.append(max(0.0, float(root)))
    accepted.sort()
    unique: list[float] = []
    for root in accepted:
        if not unique or abs(root - unique[-1]) > 1.0e-9 * max(1.0, abs(root)):
            unique.append(root)
    return unique


def _capsule_intervals(origin: np.ndarray, direction: np.ndarray,
                       start: np.ndarray, end: np.ndarray,
                       radius: float) -> tuple[list[tuple[float, float]], list[float]]:
    lower = np.minimum(start, end) - radius
    upper = np.maximum(start, end) + radius
    ray_bounds = _ray_aabb(origin, direction, lower, upper)
    if ray_bounds is None:
        return [], []
    enter, leave = ray_bounds
    if not np.isfinite(leave) or leave < 0.0:
        return [], []
    enter = max(0.0, enter)
    roots = [r for r in _capsule_boundary_roots(
        origin, direction, start, end, radius) if enter - 1.0e-9 <= r <= leave + 1.0e-9]
    breakpoints = [enter] + roots + [leave]
    breakpoints.sort()
    deduped = [breakpoints[0]]
    for value in breakpoints[1:]:
        if abs(value - deduped[-1]) > 1.0e-10 * max(1.0, abs(value)):
            deduped.append(value)
    delta = end - start
    length2 = float(np.dot(delta, delta))
    intervals: list[tuple[float, float]] = []
    tolerance = 2.0e-10 * max(1.0, radius)
    for left, right in zip(deduped[:-1], deduped[1:]):
        if right < left:
            continue
        midpoint = left + 0.5 * (right - left)
        distance, _ = _point_segment_distance(
            origin + midpoint * direction, start, delta, length2)
        if distance <= radius + tolerance:
            intervals.append((left, right))
    # Preserve isolated tangent roots as zero-width contacts.
    tangents = []
    for root in roots:
        before = max(enter, root - 1.0e-7 * max(1.0, radius))
        after = min(leave, root + 1.0e-7 * max(1.0, radius))
        d0, _ = _point_segment_distance(origin + before * direction, start, delta, length2)
        d1, _ = _point_segment_distance(origin + after * direction, start, delta, length2)
        if d0 >= radius - tolerance and d1 >= radius - tolerance:
            tangents.append(root)
    return intervals, tangents


@dataclass
class _BVHNode:
    lower: np.ndarray
    upper: np.ndarray
    indices: np.ndarray | None = None
    left: "_BVHNode | None" = None
    right: "_BVHNode | None" = None


@dataclass
class CapsuleTube:
    """Union of equal-radius capsules around a closed polyline."""

    centerline_cm: np.ndarray
    radius_cm: float
    leaf_size: int = 8
    _starts: np.ndarray = field(init=False, repr=False)
    _ends: np.ndarray = field(init=False, repr=False)
    _deltas: np.ndarray = field(init=False, repr=False)
    _length2: np.ndarray = field(init=False, repr=False)
    _lower: np.ndarray = field(init=False, repr=False)
    _upper: np.ndarray = field(init=False, repr=False)
    _root: _BVHNode = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.centerline_cm = _as_points(self.centerline_cm)
        self.radius_cm = float(self.radius_cm)
        if not np.isfinite(self.radius_cm) or self.radius_cm <= 0.0:
            raise ValueError("radius_cm must be finite and positive")
        if self.leaf_size < 1:
            raise ValueError("leaf_size must be positive")
        self._starts = self.centerline_cm
        self._ends = np.roll(self.centerline_cm, -1, axis=0)
        self._deltas = self._ends - self._starts
        self._length2 = np.einsum("ij,ij->i", self._deltas, self._deltas)
        self._lower = np.minimum(self._starts, self._ends) - self.radius_cm
        self._upper = np.maximum(self._starts, self._ends) + self.radius_cm
        self._root = self._build(np.arange(self._starts.shape[0], dtype=np.int64))

    @property
    def n_segments(self) -> int:
        return int(self._starts.shape[0])

    @property
    def bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        return self._root.lower.copy(), self._root.upper.copy()

    def _build(self, indices: np.ndarray) -> _BVHNode:
        lower = np.min(self._lower[indices], axis=0)
        upper = np.max(self._upper[indices], axis=0)
        if indices.size <= self.leaf_size:
            return _BVHNode(lower, upper, indices=indices.copy())
        centroids = 0.5 * (self._lower[indices] + self._upper[indices])
        axis = int(np.argmax(np.ptp(centroids, axis=0)))
        ordered = indices[np.argsort(centroids[:, axis], kind="stable")]
        midpoint = ordered.size // 2
        return _BVHNode(lower, upper,
                        left=self._build(ordered[:midpoint]),
                        right=self._build(ordered[midpoint:]))

    def ray_candidates(self, origin: np.ndarray, direction: np.ndarray) -> np.ndarray:
        origin = np.asarray(origin, dtype=np.float64)
        direction = _normalize(np.asarray(direction, dtype=np.float64))
        candidates: list[int] = []
        stack = [self._root]
        while stack:
            node = stack.pop()
            if _ray_aabb(origin, direction, node.lower, node.upper) is None:
                continue
            if node.indices is not None:
                candidates.extend(int(v) for v in node.indices)
            else:
                assert node.left is not None and node.right is not None
                stack.append(node.right)
                stack.append(node.left)
        return np.asarray(sorted(set(candidates)), dtype=np.int64)

    def _closest(self, point: np.ndarray) -> tuple[float, np.ndarray, int]:
        point = np.asarray(point, dtype=np.float64)
        if point.shape != (3,):
            raise ValueError("point must have shape (3,)")
        best_distance = np.inf
        best_closest = np.zeros(3)
        best_index = -1
        # Point queries use lower-bound distance to prune the same BVH.
        stack = [self._root]
        while stack:
            node = stack.pop()
            delta = np.maximum(np.maximum(node.lower - point, 0.0), point - node.upper)
            if np.linalg.norm(delta) > best_distance:
                continue
            if node.indices is not None:
                for index in node.indices:
                    distance, closest = _point_segment_distance(
                        point, self._starts[index], self._deltas[index],
                        float(self._length2[index]))
                    if distance < best_distance:
                        best_distance = distance
                        best_closest = closest
                        best_index = int(index)
            else:
                assert node.left is not None and node.right is not None
                stack.append(node.right)
                stack.append(node.left)
        return best_distance, best_closest, best_index

    def evaluate(self, points: np.ndarray) -> np.ndarray:
        values = np.asarray(points, dtype=np.float64)
        if values.shape[-1] != 3:
            raise ValueError("points must have final dimension 3")
        flat = values.reshape(-1, 3)
        result = np.asarray([self._closest(point)[0] - self.radius_cm
                             for point in flat], dtype=np.float64)
        return result.reshape(values.shape[:-1])

    def normal(self, point: np.ndarray) -> np.ndarray:
        point = np.asarray(point, dtype=np.float64)
        _, closest, index = self._closest(point)
        vector = point - closest
        magnitude = np.linalg.norm(vector)
        if magnitude <= 1.0e-12:
            tangent = _normalize(self._deltas[index])
            seed = np.asarray([0.0, 0.0, 1.0])
            if abs(float(np.dot(seed, tangent))) > 0.9:
                seed = np.asarray([1.0, 0.0, 0.0])
            return _normalize(np.cross(tangent, seed))
        return vector / magnitude

    def _distance_from_indices(self, origin: np.ndarray, direction: np.ndarray,
                               indices: Iterable[int], coincident: bool) -> float:
        intervals: list[tuple[float, float]] = []
        tangents: list[float] = []
        for index in indices:
            segment_intervals, segment_tangents = _capsule_intervals(
                origin, direction, self._starts[index], self._ends[index],
                self.radius_cm)
            intervals.extend(segment_intervals)
            tangents.extend(segment_tangents)
        if not intervals and not tangents:
            return np.inf
        intervals.sort()
        merged: list[list[float]] = []
        merge_tolerance = 2.0e-9 * max(1.0, self.radius_cm)
        for left, right in intervals:
            if not merged or left > merged[-1][1] + merge_tolerance:
                merged.append([left, right])
            else:
                merged[-1][1] = max(merged[-1][1], right)
        push = 1.0e-9 * max(1.0, self.radius_cm)
        inside = bool(self.evaluate(origin) < 0.0)
        if inside or coincident:
            for left, right in merged:
                if left <= push <= right + merge_tolerance or left <= 0.0 <= right:
                    if right > push:
                        return float(right)
        entries = [left for left, right in merged if right > push and left > push]
        entries.extend(root for root in tangents if root > push)
        return float(min(entries)) if entries else np.inf

    def distance(self, origin: np.ndarray, direction: np.ndarray,
                 coincident: bool = False) -> float:
        origin = np.asarray(origin, dtype=np.float64)
        direction = _normalize(np.asarray(direction, dtype=np.float64))
        if origin.shape != (3,):
            raise ValueError("origin must have shape (3,)")
        candidates = self.ray_candidates(origin, direction)
        return self._distance_from_indices(origin, direction, candidates, coincident)

    def distance_bruteforce(self, origin: np.ndarray, direction: np.ndarray,
                            coincident: bool = False) -> float:
        origin = np.asarray(origin, dtype=np.float64)
        direction = _normalize(np.asarray(direction, dtype=np.float64))
        return self._distance_from_indices(
            origin, direction, range(self.n_segments), coincident)


def resample_closed_centerline(centerline_cm: np.ndarray,
                               n_stations: int) -> np.ndarray:
    points = _as_points(centerline_cm)
    if n_stations < 8:
        raise ValueError("n_stations must be at least 8")
    closed = np.vstack((points, points[0]))
    lengths = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    targets = np.arange(n_stations, dtype=np.float64) * cumulative[-1] / n_stations
    result = np.empty((n_stations, 3), dtype=np.float64)
    segment = 0
    for index, target in enumerate(targets):
        while segment + 1 < lengths.size and cumulative[segment + 1] <= target:
            segment += 1
        fraction = (target - cumulative[segment]) / lengths[segment]
        result[index] = closed[segment] + fraction * (closed[segment + 1] - closed[segment])
    return result


def rotation_minimizing_frames(centerline_cm: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    points = _as_points(centerline_cm)
    tangents = np.asarray([_normalize(np.roll(points, -1, axis=0)[i]
                                     - np.roll(points, 1, axis=0)[i])
                           for i in range(points.shape[0])])
    seed = np.asarray([0.0, 0.0, 1.0])
    if abs(float(np.dot(seed, tangents[0]))) > 0.9:
        seed = np.asarray([1.0, 0.0, 0.0])
    normals = np.empty_like(points)
    normals[0] = _normalize(seed - np.dot(seed, tangents[0]) * tangents[0])
    for i in range(1, points.shape[0]):
        previous_tangent = tangents[i - 1]
        tangent = tangents[i]
        axis = np.cross(previous_tangent, tangent)
        sine = np.linalg.norm(axis)
        cosine = float(np.clip(np.dot(previous_tangent, tangent), -1.0, 1.0))
        value = normals[i - 1]
        if sine > 1.0e-13:
            axis /= sine
            angle = np.arctan2(sine, cosine)
            value = (value * np.cos(angle) + np.cross(axis, value) * np.sin(angle)
                     + axis * np.dot(axis, value) * (1.0 - np.cos(angle)))
        value -= np.dot(value, tangent) * tangent
        normals[i] = _normalize(value)

    # Compute closure mismatch and spread a compensating twist along the loop.
    t0 = tangents[-1]
    t1 = tangents[0]
    axis = np.cross(t0, t1)
    sine = np.linalg.norm(axis)
    closure = normals[-1]
    if sine > 1.0e-13:
        axis /= sine
        angle = np.arctan2(sine, float(np.clip(np.dot(t0, t1), -1.0, 1.0)))
        closure = (closure * np.cos(angle) + np.cross(axis, closure) * np.sin(angle)
                   + axis * np.dot(axis, closure) * (1.0 - np.cos(angle)))
    closure -= np.dot(closure, t1) * t1
    closure = _normalize(closure)
    delta = np.arctan2(float(np.dot(t1, np.cross(closure, normals[0]))),
                       float(np.dot(closure, normals[0])))
    for i in range(points.shape[0]):
        angle = delta * i / points.shape[0]
        tangent = tangents[i]
        value = normals[i]
        normals[i] = (value * np.cos(angle) + np.cross(tangent, value) * np.sin(angle)
                      + tangent * np.dot(tangent, value) * (1.0 - np.cos(angle)))
        normals[i] = _normalize(normals[i])
    binormals = np.asarray([_normalize(np.cross(t, n)) for t, n in zip(tangents, normals)])
    return tangents, normals, binormals


@dataclass(frozen=True)
class CoilHexMesh:
    vertices_cm: np.ndarray
    connectivity: np.ndarray
    arc_index: np.ndarray
    u_index: np.ndarray
    v_index: np.ndarray
    centerline_cm: np.ndarray
    tangents: np.ndarray
    normals: np.ndarray
    binormals: np.ndarray
    radius_cm: float
    u_bins: int
    v_bins: int

    @property
    def n_elements(self) -> int:
        return int(self.connectivity.shape[0])

    def element_centroids_cm(self) -> np.ndarray:
        return np.mean(self.vertices_cm[self.connectivity], axis=1)

    def approximate_element_volumes_cm3(self) -> np.ndarray:
        p = self.vertices_cm[self.connectivity]
        tetrahedra = ((0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6),
                      (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6))
        volume = np.zeros(self.n_elements, dtype=np.float64)
        for a, b, c, d in tetrahedra:
            signed = np.einsum("ij,ij->i", p[:, b] - p[:, a],
                               np.cross(p[:, c] - p[:, a], p[:, d] - p[:, a])) / 6.0
            volume += np.abs(signed)
        return volume


def build_coil_local_mesh(centerline_cm: np.ndarray, radius_cm: float, *,
                          arc_bins: int = 96, u_bins: int = 8,
                          v_bins: int = 8) -> CoilHexMesh:
    """Build a disk-filling, coil-aligned hexahedral tally mesh.

    A smooth square-to-disk mapping avoids a singular polar centerline.  The
    mesh is logically indexed by arc length and two cross-section coordinates.
    """
    if arc_bins < 8 or u_bins < 2 or v_bins < 2:
        raise ValueError("arc_bins must be >=8 and cross-section bins >=2")
    radius = float(radius_cm)
    if not np.isfinite(radius) or radius <= 0.0:
        raise ValueError("radius_cm must be finite and positive")
    centerline = resample_closed_centerline(centerline_cm, arc_bins)
    tangents, normals, binormals = rotation_minimizing_frames(centerline)
    u = np.linspace(-1.0, 1.0, u_bins + 1)
    v = np.linspace(-1.0, 1.0, v_bins + 1)
    uu, vv = np.meshgrid(u, v, indexing="ij")
    # Fernandez-Guasti square-to-disk map.
    disk_u = uu * np.sqrt(np.maximum(0.0, 1.0 - 0.5 * vv * vv))
    disk_v = vv * np.sqrt(np.maximum(0.0, 1.0 - 0.5 * uu * uu))
    vertices = (centerline[:, None, None, :]
                + radius * disk_u[None, :, :, None] * normals[:, None, None, :]
                + radius * disk_v[None, :, :, None] * binormals[:, None, None, :])

    def vertex(i: int, j: int, k: int) -> int:
        return (i * (u_bins + 1) + j) * (v_bins + 1) + k

    connectivity = []
    arc_index = []
    u_index = []
    v_index = []
    for i in range(arc_bins):
        i1 = (i + 1) % arc_bins
        for j in range(u_bins):
            for k in range(v_bins):
                connectivity.append((
                    vertex(i, j, k), vertex(i, j + 1, k),
                    vertex(i, j + 1, k + 1), vertex(i, j, k + 1),
                    vertex(i1, j, k), vertex(i1, j + 1, k),
                    vertex(i1, j + 1, k + 1), vertex(i1, j, k + 1),
                ))
                arc_index.append(i)
                u_index.append(j)
                v_index.append(k)
    mesh = CoilHexMesh(
        vertices_cm=np.ascontiguousarray(vertices.reshape(-1, 3)),
        connectivity=np.asarray(connectivity, dtype=np.int64),
        arc_index=np.asarray(arc_index, dtype=np.int32),
        u_index=np.asarray(u_index, dtype=np.int32),
        v_index=np.asarray(v_index, dtype=np.int32),
        centerline_cm=centerline,
        tangents=tangents,
        normals=normals,
        binormals=binormals,
        radius_cm=radius,
        u_bins=u_bins,
        v_bins=v_bins,
    )
    volumes = mesh.approximate_element_volumes_cm3()
    if np.any(~np.isfinite(volumes)) or np.any(volumes <= 0.0):
        raise ValueError("coil-local mesh contains nonpositive-volume elements")
    return mesh


def write_coil_mesh_hdf5(path: str | Path, mesh: CoilHexMesh) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(target, "w") as h5:
        h5.attrs["filetype"] = "stellarcsg-coil-tally-mesh"
        h5.attrs["schema_major"] = 1
        h5.attrs["schema_minor"] = 0
        h5.attrs["units"] = "cm"
        h5.attrs["radius_cm"] = mesh.radius_cm
        h5.create_dataset("vertices_cm", data=mesh.vertices_cm)
        h5.create_dataset("connectivity", data=mesh.connectivity)
        h5.create_dataset("arc_index", data=mesh.arc_index)
        h5.create_dataset("u_index", data=mesh.u_index)
        h5.create_dataset("v_index", data=mesh.v_index)
        h5.create_dataset("centerline_cm", data=mesh.centerline_cm)
        h5.create_dataset("tangent", data=mesh.tangents)
        h5.create_dataset("normal", data=mesh.normals)
        h5.create_dataset("binormal", data=mesh.binormals)
        h5.create_dataset("element_volume_cm3", data=mesh.approximate_element_volumes_cm3())


def write_coil_mesh_vtk(path: str | Path, mesh: CoilHexMesh) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        stream.write("# vtk DataFile Version 3.0\nStellarCSG coil local mesh\nASCII\n")
        stream.write("DATASET UNSTRUCTURED_GRID\n")
        stream.write(f"POINTS {mesh.vertices_cm.shape[0]} double\n")
        np.savetxt(stream, mesh.vertices_cm, fmt="%.17g")
        stream.write(f"CELLS {mesh.n_elements} {mesh.n_elements * 9}\n")
        for cell in mesh.connectivity:
            stream.write("8 " + " ".join(str(int(v)) for v in cell) + "\n")
        stream.write(f"CELL_TYPES {mesh.n_elements}\n")
        stream.write(("12\n" * mesh.n_elements))
        stream.write(f"CELL_DATA {mesh.n_elements}\n")
        for name, values in (("arc_index", mesh.arc_index),
                             ("u_index", mesh.u_index),
                             ("v_index", mesh.v_index)):
            stream.write(f"SCALARS {name} int 1\nLOOKUP_TABLE default\n")
            np.savetxt(stream, values, fmt="%d")


def coil_mesh_summary(mesh: CoilHexMesh) -> dict[str, object]:
    volume = mesh.approximate_element_volumes_cm3()
    return {
        "schema_version": 1,
        "n_vertices": int(mesh.vertices_cm.shape[0]),
        "n_elements": mesh.n_elements,
        "arc_bins": int(mesh.centerline_cm.shape[0]),
        "u_bins": mesh.u_bins,
        "v_bins": mesh.v_bins,
        "radius_cm": mesh.radius_cm,
        "minimum_element_volume_cm3": float(np.min(volume)),
        "maximum_element_volume_cm3": float(np.max(volume)),
        "total_approximate_volume_cm3": float(np.sum(volume)),
    }


def write_coil_mesh_summary(path: str | Path, mesh: CoilHexMesh) -> None:
    Path(path).write_text(json.dumps(coil_mesh_summary(mesh), indent=2) + "\n")
