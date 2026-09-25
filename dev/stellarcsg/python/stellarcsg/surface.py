"""Generic periodic radial stellarator surface compiler and evaluator."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from typing import Iterable, Mapping

import numpy as np

from .spline import (
    sample_periodic_bicubic,
    sample_periodic_cubic,
    samples_to_periodic_coefficients,
)

_TWO_PI = 2.0 * np.pi


def _as_f64(name: str, values: np.ndarray | Iterable[float], ndim: int) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != ndim:
        raise ValueError(f"{name} must be {ndim}-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return np.ascontiguousarray(array)


@dataclass(frozen=True)
class PeriodicRadialSurfaceData:
    """Frozen coefficient representation shared with the C++ reference kernel."""

    name: str
    n_field_periods: int
    axis_r_coefficients: np.ndarray
    axis_z_coefficients: np.ndarray
    radius_coefficients: np.ndarray
    units: str = "cm"
    characteristic_length: float | None = None
    coordinate_singularity_tolerance: float = 1.0e-12
    source_metadata: Mapping[str, object] | None = None
    content_id: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("surface name cannot be empty")
        if self.n_field_periods <= 0:
            raise ValueError("n_field_periods must be positive")
        if self.units != "cm":
            raise ValueError("frozen transport geometry must use centimetres")
        axis_r = _as_f64("axis_r_coefficients", self.axis_r_coefficients, 1)
        axis_z = _as_f64("axis_z_coefficients", self.axis_z_coefficients, 1)
        radius = _as_f64("radius_coefficients", self.radius_coefficients, 2)
        if axis_r.size < 4 or axis_r.shape != axis_z.shape:
            raise ValueError("axis coefficient arrays must have equal length >= 4")
        if min(radius.shape) < 4:
            raise ValueError("radius coefficient dimensions must both be >= 4")
        if np.any(radius <= 0.0):
            raise ValueError("radius coefficients must be positive")
        characteristic = self.characteristic_length
        if characteristic is None:
            characteristic = float(np.max(np.abs(axis_r)) + np.max(radius))
        if not np.isfinite(characteristic) or characteristic <= 0.0:
            raise ValueError("characteristic_length must be finite and positive")
        if (
            not np.isfinite(self.coordinate_singularity_tolerance)
            or self.coordinate_singularity_tolerance <= 0.0
        ):
            raise ValueError("coordinate_singularity_tolerance must be positive")
        object.__setattr__(self, "axis_r_coefficients", axis_r)
        object.__setattr__(self, "axis_z_coefficients", axis_z)
        object.__setattr__(self, "radius_coefficients", radius)
        object.__setattr__(self, "characteristic_length", characteristic)
        if self.content_id is None:
            object.__setattr__(self, "content_id", self.compute_content_id())

    @classmethod
    def analytic_torus(
        cls,
        *,
        name: str,
        major_radius_cm: float,
        minor_radius_cm: float,
        n_field_periods: int = 1,
        n_axis: int = 8,
        n_theta: int = 12,
        n_phi: int = 8,
        helical_amplitude_cm: float = 0.0,
        poloidal_mode: int = 2,
        toroidal_mode: int = 1,
    ) -> "PeriodicRadialSurfaceData":
        if major_radius_cm <= 0.0 or minor_radius_cm <= 0.0:
            raise ValueError("major and minor radii must be positive")
        theta = _TWO_PI * np.arange(n_theta) / n_theta
        psi = _TWO_PI * np.arange(n_phi) / n_phi
        sampled_radius = minor_radius_cm + helical_amplitude_cm * np.cos(
            poloidal_mode * theta[:, None] - toroidal_mode * psi[None, :]
        )
        if np.any(sampled_radius <= 0.0):
            raise ValueError("helical perturbation produces nonpositive radius")
        return cls(
            name=name,
            n_field_periods=n_field_periods,
            axis_r_coefficients=np.full(n_axis, major_radius_cm),
            axis_z_coefficients=np.zeros(n_axis),
            radius_coefficients=samples_to_periodic_coefficients(sampled_radius),
            source_metadata={
                "kind": "analytic_torus",
                "major_radius_cm": major_radius_cm,
                "minor_radius_cm": minor_radius_cm,
                "helical_amplitude_cm": helical_amplitude_cm,
                "poloidal_mode": poloidal_mode,
                "toroidal_mode": toroidal_mode,
            },
        )

    @classmethod
    def from_surface_grid(
        cls,
        *,
        name: str,
        xyz_cm: np.ndarray,
        phi: np.ndarray,
        n_field_periods: int,
        axis_r_cm: np.ndarray | None = None,
        axis_z_cm: np.ndarray | None = None,
        n_theta_coefficients: int | None = None,
        source_metadata: Mapping[str, object] | None = None,
    ) -> "PeriodicRadialSurfaceData":
        """Compile a periodic sampled surface without CAD.

        ``xyz_cm`` has shape ``(n_input_theta, n_phi, 3)``. The input poloidal
        parameter need not equal geometric polar angle: every toroidal slice is
        reparameterized onto a uniform geometric-theta grid before fitting.
        ``phi`` must cover one field period without duplicating its endpoint.
        """
        xyz = _as_f64("xyz_cm", xyz_cm, 3)
        phi_array = _as_f64("phi", phi, 1)
        if xyz.shape[2] != 3 or xyz.shape[1] != phi_array.size:
            raise ValueError("xyz_cm must have shape (n_theta, len(phi), 3)")
        if xyz.shape[0] < 4 or xyz.shape[1] < 4:
            raise ValueError("surface grid requires at least four samples per angle")
        if n_field_periods <= 0:
            raise ValueError("n_field_periods must be positive")
        expected_span = _TWO_PI / n_field_periods
        reduced = np.mod(phi_array - phi_array[0], expected_span)
        order_phi = np.argsort(reduced)
        if not np.all(order_phi == np.arange(order_phi.size)):
            xyz = xyz[:, order_phi, :]
            reduced = reduced[order_phi]
        if np.any(np.diff(reduced) <= 0.0):
            raise ValueError("phi samples must be unique over one field period")
        uniform_phi = expected_span * np.arange(phi_array.size) / phi_array.size
        if not np.allclose(reduced, uniform_phi, rtol=0.0, atol=1.0e-10):
            raise ValueError(
                "first compiler version requires a uniform phi grid over one field period"
            )

        R = np.hypot(xyz[..., 0], xyz[..., 1])
        Z = xyz[..., 2]
        if axis_r_cm is None:
            next_r = np.roll(R, -1, axis=0)
            next_z = np.roll(Z, -1, axis=0)
            polygon_cross = R * next_z - next_r * Z
            twice_area = np.sum(polygon_cross, axis=0)
            if np.any(np.abs(twice_area) <= 1.0e-14):
                raise ValueError("surface slice has a degenerate poloidal polygon")
            axis_r = np.sum((R + next_r) * polygon_cross, axis=0) / (
                3.0 * twice_area
            )
        else:
            axis_r = _as_f64("axis_r_cm", axis_r_cm, 1)
        if axis_z_cm is None:
            if axis_r_cm is None:
                axis_z = np.sum((Z + next_z) * polygon_cross, axis=0) / (
                    3.0 * twice_area
                )
            else:
                axis_z = np.mean(Z, axis=0)
        else:
            axis_z = _as_f64("axis_z_cm", axis_z_cm, 1)
        if axis_r.shape != (phi_array.size,) or axis_z.shape != (phi_array.size,):
            raise ValueError("axis arrays must have one value per phi sample")

        n_theta = n_theta_coefficients or xyz.shape[0]
        if n_theta < 4:
            raise ValueError("n_theta_coefficients must be >= 4")
        theta_uniform = _TWO_PI * np.arange(n_theta) / n_theta
        sampled_radius = np.empty((n_theta, phi_array.size), dtype=np.float64)
        star_margins = []
        for j in range(phi_array.size):
            q_r = R[:, j] - axis_r[j]
            q_z = Z[:, j] - axis_z[j]
            theta_geo = np.mod(np.arctan2(q_z, q_r), _TWO_PI)
            rho = np.hypot(q_r, q_z)
            theta_unwrapped = np.unwrap(np.arctan2(q_z, q_r))
            if np.any(np.diff(theta_unwrapped) <= 1.0e-12):
                raise ValueError(
                    f"surface slice {j} has a geometric-theta fold"
                )
            order = np.argsort(theta_geo)
            theta_sorted = theta_geo[order]
            rho_sorted = rho[order]
            gaps = np.diff(np.concatenate((theta_sorted, [theta_sorted[0] + _TWO_PI])))
            if np.any(gaps <= 1.0e-12):
                raise ValueError(
                    f"surface slice {j} is not single-valued in geometric theta"
                )
            star_margins.append(float(np.min(gaps)))
            # The VMEC parameter can cluster strongly in geometric angle. A
            # periodic cubic interpolant avoids the O(h^2) chord error of a
            # piecewise-linear remap without changing the transport chart.
            from scipy.interpolate import CubicSpline

            theta_periodic = np.concatenate(
                (theta_sorted, [theta_sorted[0] + _TWO_PI])
            )
            rho_periodic = np.concatenate((rho_sorted, [rho_sorted[0]]))
            remap = CubicSpline(theta_periodic, rho_periodic, bc_type="periodic")
            query = np.mod(theta_uniform - theta_sorted[0], _TWO_PI) + theta_sorted[0]
            sampled_radius[:, j] = remap(query)
        if np.any(sampled_radius <= 0.0):
            raise ValueError("surface radius is not positive after reparameterization")

        metadata = dict(source_metadata or {})
        metadata.update(
            {
                "kind": "surface_grid",
                "input_shape": list(xyz.shape),
                "minimum_geometric_theta_gap_rad": min(star_margins),
                "axis_inferred": axis_r_cm is None or axis_z_cm is None,
                "axis_inference": "polygon_area_centroid"
                if axis_r_cm is None and axis_z_cm is None
                else "provided_or_mixed",
            }
        )
        return cls(
            name=name,
            n_field_periods=n_field_periods,
            axis_r_coefficients=samples_to_periodic_coefficients(axis_r),
            axis_z_coefficients=samples_to_periodic_coefficients(axis_z),
            radius_coefficients=samples_to_periodic_coefficients(sampled_radius),
            source_metadata=metadata,
        )

    @property
    def n_theta(self) -> int:
        return int(self.radius_coefficients.shape[0])

    @property
    def n_phi(self) -> int:
        return int(self.radius_coefficients.shape[1])

    def compute_content_id(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.canonical_metadata_json().encode())
        for array in (
            self.axis_r_coefficients,
            self.axis_z_coefficients,
            self.radius_coefficients,
        ):
            digest.update(np.asarray(array, dtype="<f8", order="C").tobytes())
        return "sha256:" + digest.hexdigest()

    def canonical_metadata_json(self) -> str:
        """Return the exact canonical metadata bytes covered by content_id."""
        metadata = {
            "schema_version": [1, 0],
            "name": self.name,
            "n_field_periods": self.n_field_periods,
            "units": self.units,
            "characteristic_length": self.characteristic_length,
            "coordinate_singularity_tolerance": self.coordinate_singularity_tolerance,
            "source_metadata": dict(self.source_metadata or {}),
        }
        return json.dumps(metadata, sort_keys=True, separators=(",", ":"))

    def axis(self, phi: np.ndarray | float) -> tuple[np.ndarray, ...]:
        r, dr = sample_periodic_cubic(
            self.axis_r_coefficients, phi, self.n_field_periods
        )
        z, dz = sample_periodic_cubic(
            self.axis_z_coefficients, phi, self.n_field_periods
        )
        return r, z, dr, dz

    def radius(
        self, theta: np.ndarray | float, phi: np.ndarray | float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return sample_periodic_bicubic(
            self.radius_coefficients, theta, phi, self.n_field_periods
        )

    def position(
        self, theta: np.ndarray | float, phi: np.ndarray | float
    ) -> np.ndarray:
        theta_array, phi_array = np.broadcast_arrays(
            np.asarray(theta, dtype=np.float64), np.asarray(phi, dtype=np.float64)
        )
        axis_r, axis_z, _, _ = self.axis(phi_array)
        radius, _, _ = self.radius(theta_array, phi_array)
        R = axis_r + radius * np.cos(theta_array)
        Z = axis_z + radius * np.sin(theta_array)
        return np.stack((R * np.cos(phi_array), R * np.sin(phi_array), Z), axis=-1)

    def evaluate(self, points: np.ndarray) -> np.ndarray:
        point = np.asarray(points, dtype=np.float64)
        if point.shape[-1] != 3:
            raise ValueError("points must have final dimension 3")
        R = np.hypot(point[..., 0], point[..., 1])
        phi = np.mod(np.arctan2(point[..., 1], point[..., 0]), _TWO_PI)
        axis_r, axis_z, _, _ = self.axis(phi)
        q_r = R - axis_r
        q_z = point[..., 2] - axis_z
        rho = np.hypot(q_r, q_z)
        theta = np.arctan2(q_z, q_r)
        surface_radius, _, _ = self.radius(theta, phi)
        return rho - surface_radius

    def with_radial_thickness(
        self,
        name: str,
        thickness_cm: float | np.ndarray,
        *,
        source_metadata: Mapping[str, object] | None = None,
    ) -> "PeriodicRadialSurfaceData":
        if np.isscalar(thickness_cm):
            value = float(thickness_cm)
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError("constant thickness must be finite and positive")
            delta = np.full_like(self.radius_coefficients, value)
        else:
            samples = _as_f64("thickness_cm", thickness_cm, 2)
            if samples.shape != self.radius_coefficients.shape:
                raise ValueError(
                    "sampled thickness must match the surface coefficient grid shape"
                )
            if np.any(samples <= 0.0):
                raise ValueError("sampled thickness must be positive")
            delta = samples_to_periodic_coefficients(samples)
            dense_theta = _TWO_PI * np.arange(self.n_theta * 4) / (self.n_theta * 4)
            dense_phi = (
                _TWO_PI
                * np.arange(self.n_phi * 4)
                / (self.n_field_periods * self.n_phi * 4)
            )
            t, p = np.meshgrid(dense_theta, dense_phi, indexing="ij")
            sampled_delta, _, _ = sample_periodic_bicubic(
                delta, t, p, self.n_field_periods
            )
            if np.min(sampled_delta) <= 0.0:
                raise ValueError(
                    "interpolating the thickness field produces nonpositive thickness"
                )
        metadata = {
            "kind": "radial_offset",
            "parent_content_id": self.content_id,
            **dict(source_metadata or {}),
        }
        return replace(
            self,
            name=name,
            radius_coefficients=self.radius_coefficients + delta,
            source_metadata=metadata,
            content_id=None,
        )


def compile_radial_build(
    base: PeriodicRadialSurfaceData,
    layers: Iterable[tuple[str, float | np.ndarray]],
) -> list[PeriodicRadialSurfaceData]:
    """Return the base and cumulative outward radial boundaries."""
    boundaries = [base]
    current = base
    for name, thickness in layers:
        current = current.with_radial_thickness(name, thickness)
        boundaries.append(current)
    return boundaries


def compile_normal_build(
    base: PeriodicRadialSurfaceData,
    layers: Iterable[tuple[str, float | np.ndarray]],
    *,
    sample_factor: int = 2,
) -> list[PeriodicRadialSurfaceData]:
    """Compile cumulative layers displaced along each physical boundary normal.

    Every displaced point cloud is remapped to the stable geometric-poloidal
    transport chart and refitted. A layer is rejected if that remapping folds,
    crosses its parent, reaches cylindrical ``R=0``, or develops a degenerate
    surface Jacobian.
    """
    if sample_factor < 1:
        raise ValueError("sample_factor must be positive")
    boundaries = [base]
    current = base
    for name, thickness in layers:
        n_theta = current.n_theta * sample_factor
        n_phi = current.n_phi * sample_factor
        theta = _TWO_PI * np.arange(n_theta) / n_theta
        phi = _TWO_PI * np.arange(n_phi) / (current.n_field_periods * n_phi)
        t, p = np.meshgrid(theta, phi, indexing="ij")
        radius, radius_theta, radius_phi = current.radius(t, p)
        axis_r, axis_z, axis_r_phi, axis_z_phi = current.axis(p)
        cos_t = np.cos(t)
        sin_t = np.sin(t)
        cos_p = np.cos(p)
        sin_p = np.sin(p)
        major_r = axis_r + radius * cos_t
        height = axis_z + radius * sin_t
        r_theta = radius_theta * cos_t - radius * sin_t
        z_theta = radius_theta * sin_t + radius * cos_t
        r_phi = axis_r_phi + radius_phi * cos_t
        z_phi = axis_z_phi + radius_phi * sin_t
        dtheta = np.stack(
            (r_theta * cos_p, r_theta * sin_p, z_theta), axis=-1
        )
        dphi = np.stack(
            (
                r_phi * cos_p - major_r * sin_p,
                r_phi * sin_p + major_r * cos_p,
                z_phi,
            ),
            axis=-1,
        )
        outward = np.cross(dphi, dtheta)
        jacobian = np.linalg.norm(outward, axis=-1)
        jacobian_tolerance = 1.0e-12 * current.characteristic_length**2
        if np.min(jacobian) <= jacobian_tolerance:
            raise ValueError("REJECT_THETA_FOLD: surface Jacobian is degenerate")
        outward /= jacobian[..., None]

        if np.isscalar(thickness):
            thickness_grid = np.full((n_theta, n_phi), float(thickness))
        else:
            thickness_samples = _as_f64("thickness_cm", thickness, 2)
            if thickness_samples.shape != (
                current.n_theta,
                current.n_phi,
            ):
                raise ValueError(
                    "sampled normal thickness must match the current coefficient grid"
                )
            thickness_coefficients = samples_to_periodic_coefficients(
                thickness_samples
            )
            thickness_grid, _, _ = sample_periodic_bicubic(
                thickness_coefficients, t, p, current.n_field_periods
            )
        if not np.all(np.isfinite(thickness_grid)) or np.min(thickness_grid) <= 0.0:
            raise ValueError("normal thickness must remain finite and positive")

        points = np.stack(
            (major_r * cos_p, major_r * sin_p, height), axis=-1
        )
        displaced = points + thickness_grid[..., None] * outward
        displaced_r = np.hypot(displaced[..., 0], displaced[..., 1])
        if np.min(displaced_r) <= 1.0e-10 * current.characteristic_length:
            raise ValueError("REJECT_R_ZERO_BOUND: displaced layer approaches R=0")
        next_surface = PeriodicRadialSurfaceData.from_surface_grid(
            name=name,
            xyz_cm=displaced,
            phi=phi,
            n_field_periods=current.n_field_periods,
            axis_r_cm=current.axis(phi)[0],
            axis_z_cm=current.axis(phi)[1],
            n_theta_coefficients=n_theta,
            source_metadata={
                "kind": "physical_normal_offset",
                "parent_content_id": current.content_id,
                "minimum_requested_thickness_cm": float(np.min(thickness_grid)),
                "maximum_requested_thickness_cm": float(np.max(thickness_grid)),
            },
        )
        parent_radius = current.radius(t, p)[0]
        child_radius = next_surface.radius(t, p)[0]
        minimum_radial_separation = float(np.min(child_radius - parent_radius))
        if minimum_radial_separation <= 0.0:
            raise ValueError("REJECT_THETA_FOLD: normal layer intersects its parent")
        metadata = dict(next_surface.source_metadata or {})
        metadata["kind"] = "physical_normal_offset"
        metadata["minimum_remapped_radial_separation_cm"] = minimum_radial_separation
        next_surface = replace(
            next_surface, source_metadata=metadata, content_id=None
        )
        boundaries.append(next_surface)
        current = next_surface
    return boundaries
