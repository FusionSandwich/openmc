"""Smooth swept-coil compiler with rotation-minimizing frames."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
from scipy.interpolate import CubicSpline

from .spline import sample_periodic_cubic, samples_to_periodic_coefficients


TWO_PI = 2.0 * np.pi


def read_makegrid_filaments(path: str | Path) -> tuple[int, list[np.ndarray]]:
    """Read MAKEGRID filament coordinates and return closed curves in cm."""
    periods = None
    coils: list[np.ndarray] = []
    current: list[list[float]] = []
    for raw_line in Path(path).read_text().splitlines():
        fields = raw_line.split()
        if not fields:
            continue
        if fields[0].lower() == "periods":
            periods = int(fields[1])
            continue
        if len(fields) < 4:
            continue
        try:
            x, y, z, current_value = map(float, fields[:4])
        except ValueError:
            continue
        if current_value == 0.0:
            if len(current) >= 4:
                curve = np.asarray(current, dtype=np.float64)
                if np.linalg.norm(curve[0] - curve[-1]) <= 1.0e-8:
                    curve = curve[:-1]
                coils.append(100.0 * curve)
            current = []
        else:
            current.append([x, y, z])
    if len(current) >= 4:
        curve = np.asarray(current, dtype=np.float64)
        if np.linalg.norm(curve[0] - curve[-1]) <= 1.0e-8:
            curve = curve[:-1]
        coils.append(100.0 * curve)
    if periods is None:
        raise ValueError("MAKEGRID coil file does not declare periods")
    if not coils:
        raise ValueError("MAKEGRID coil file contains no closed filament")
    return periods, coils


def _rotate(vector: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    return (
        vector * np.cos(angle)
        + np.cross(axis, vector) * np.sin(angle)
        + axis * np.dot(axis, vector) * (1.0 - np.cos(angle))
    )


def _signed_angle(a: np.ndarray, b: np.ndarray, axis: np.ndarray) -> float:
    return float(np.arctan2(np.dot(axis, np.cross(a, b)), np.dot(a, b)))


def _equal_arc_samples(points_cm: np.ndarray, count: int):
    points = np.asarray(points_cm, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] < 4:
        raise ValueError("closed centerline requires at least four 3-D points")
    closed = np.vstack((points, points[0]))
    segment = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    if np.min(segment) <= 0.0:
        raise ValueError("centerline contains duplicate consecutive points")
    arc = np.concatenate(([0.0], np.cumsum(segment)))
    length = float(arc[-1])
    spline = CubicSpline(arc, closed, axis=0, bc_type="periodic")
    sample_arc = length * np.arange(count) / count
    centerline = spline(sample_arc)
    derivative = spline(sample_arc, 1)
    tangent = derivative / np.linalg.norm(derivative, axis=1)[:, None]
    return centerline, tangent, length


def _rotation_minimizing_frame(tangent: np.ndarray):
    count = tangent.shape[0]
    trial = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(trial, tangent[0])) > 0.9:
        trial = np.array([1.0, 0.0, 0.0])
    normal = np.empty_like(tangent)
    normal[0] = trial - np.dot(trial, tangent[0]) * tangent[0]
    normal[0] /= np.linalg.norm(normal[0])

    def transport(value, start_tangent, end_tangent):
        cross = np.cross(start_tangent, end_tangent)
        sine = np.linalg.norm(cross)
        cosine = float(np.clip(np.dot(start_tangent, end_tangent), -1.0, 1.0))
        if sine <= 1.0e-14:
            return value.copy()
        return _rotate(value, cross / sine, float(np.arctan2(sine, cosine)))

    for index in range(1, count):
        normal[index] = transport(normal[index - 1], tangent[index - 1], tangent[index])
        normal[index] -= np.dot(normal[index], tangent[index]) * tangent[index]
        normal[index] /= np.linalg.norm(normal[index])
    closure_normal = transport(normal[-1], tangent[-1], tangent[0])
    residual_twist = _signed_angle(normal[0], closure_normal, tangent[0])
    for index in range(count):
        correction = -residual_twist * index / count
        normal[index] = _rotate(normal[index], tangent[index], correction)
    binormal = np.cross(tangent, normal)
    binormal /= np.linalg.norm(binormal, axis=1)[:, None]
    normal = np.cross(binormal, tangent)
    return normal, binormal, residual_twist


@dataclass(frozen=True)
class SweptSplineData:
    coil_id: int
    centerline_coefficients_cm: np.ndarray
    normal_coefficients: np.ndarray
    binormal_coefficients: np.ndarray
    major_radius_coefficients_cm: np.ndarray
    minor_radius_coefficients_cm: np.ndarray
    length_cm: float
    source_metadata: dict
    content_id: str

    @classmethod
    def from_centerline(
        cls,
        coil_id: int,
        points_cm: np.ndarray,
        *,
        major_radius_cm: float,
        minor_radius_cm: float | None = None,
        sample_count: int = 256,
        source_metadata: dict | None = None,
    ) -> "SweptSplineData":
        if major_radius_cm <= 0.0:
            raise ValueError("coil cross-section radius must be positive")
        minor_radius_cm = major_radius_cm if minor_radius_cm is None else minor_radius_cm
        if minor_radius_cm <= 0.0:
            raise ValueError("coil cross-section radius must be positive")
        centerline, tangent, length = _equal_arc_samples(points_cm, sample_count)
        normal, binormal, residual_twist = _rotation_minimizing_frame(tangent)
        centerline_coefficients = np.column_stack([
            samples_to_periodic_coefficients(centerline[:, axis]) for axis in range(3)
        ])
        normal_coefficients = np.column_stack([
            samples_to_periodic_coefficients(normal[:, axis]) for axis in range(3)
        ])
        binormal_coefficients = np.column_stack([
            samples_to_periodic_coefficients(binormal[:, axis]) for axis in range(3)
        ])
        major = np.full(sample_count, major_radius_cm)
        minor = np.full(sample_count, minor_radius_cm)
        metadata = dict(source_metadata or {})
        metadata.update({
            "frame": "rotation-minimizing",
            "frame_residual_twist_before_distribution_rad": residual_twist,
            "sample_count": sample_count,
        })
        payload = {
            "schema_version": [1, 0], "coil_id": coil_id, "units": "cm",
            "length_cm": length, "source_metadata": metadata,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode())
        for array in (centerline_coefficients, normal_coefficients,
                      binormal_coefficients, major, minor):
            digest.update(np.asarray(array, dtype="<f8", order="C").tobytes())
        return cls(
            coil_id=coil_id,
            centerline_coefficients_cm=centerline_coefficients,
            normal_coefficients=normal_coefficients,
            binormal_coefficients=binormal_coefficients,
            major_radius_coefficients_cm=major,
            minor_radius_coefficients_cm=minor,
            length_cm=length,
            source_metadata=metadata,
            content_id="sha256:" + digest.hexdigest(),
        )

    @property
    def sample_count(self):
        return self.centerline_coefficients_cm.shape[0]

    def canonical_metadata_json(self):
        return json.dumps({
            "schema_version": [1, 0],
            "coil_id": self.coil_id,
            "units": "cm",
            "length_cm": self.length_cm,
            "source_metadata": self.source_metadata,
        }, sort_keys=True, separators=(",", ":"))

    def frame(self, arc_coordinate: np.ndarray | float):
        angle = TWO_PI * np.asarray(arc_coordinate) / self.length_cm
        center = []
        tangent = []
        normal = []
        binormal = []
        for axis in range(3):
            value, derivative = sample_periodic_cubic(
                self.centerline_coefficients_cm[:, axis], angle
            )
            center.append(value)
            tangent.append(derivative)
            normal.append(sample_periodic_cubic(
                self.normal_coefficients[:, axis], angle
            )[0])
            binormal.append(sample_periodic_cubic(
                self.binormal_coefficients[:, axis], angle
            )[0])
        center = np.stack(center, axis=-1)
        tangent = np.stack(tangent, axis=-1)
        tangent /= np.linalg.norm(tangent, axis=-1)[..., None]
        normal = np.stack(normal, axis=-1)
        normal -= np.sum(normal * tangent, axis=-1)[..., None] * tangent
        normal /= np.linalg.norm(normal, axis=-1)[..., None]
        binormal = np.cross(tangent, normal)
        return center, tangent, normal, binormal


def write_swept_collection(path: str | Path, coils: list[SweptSplineData]):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(output, "w") as handle:
        handle.attrs["schema_name"] = "stellarcsg-swept-spline"
        handle.attrs["schema_version"] = np.array([1, 0], dtype=np.int32)
        for coil in coils:
            group = handle.create_group(f"coils/coil_{coil.coil_id:03d}")
            group.attrs["surface_type"] = "swept-elliptical-cubic"
            group.attrs["units"] = "cm"
            group.attrs["content_id"] = coil.content_id
            group.attrs["coil_id"] = coil.coil_id
            group.attrs["length_cm"] = coil.length_cm
            group.attrs["canonical_metadata_json"] = coil.canonical_metadata_json()
            group.attrs["source_metadata_json"] = json.dumps(
                coil.source_metadata, sort_keys=True, separators=(",", ":")
            )
            group["centerline_coefficients"] = coil.centerline_coefficients_cm
            group["normal_coefficients"] = coil.normal_coefficients
            group["binormal_coefficients"] = coil.binormal_coefficients
            group["major_radius_coefficients"] = coil.major_radius_coefficients_cm
            group["minor_radius_coefficients"] = coil.minor_radius_coefficients_cm
