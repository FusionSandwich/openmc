"""Retain exact, shaped-axisymmetric, and helical fidelity cases."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from stellarcsg import PeriodicRadialSurfaceData, write_surface_collection


TWO_PI = 2.0 * np.pi


def source_points(axis_r, radius, theta, phi):
    major = axis_r + radius * np.cos(theta)
    return np.stack(
        (major * np.cos(phi), major * np.sin(phi), radius * np.sin(theta)),
        axis=-1,
    )


def metrics(name, surface, reference_radius, reference_dtheta, reference_dphi):
    theta = TWO_PI * np.arange(769) / 769
    phi = TWO_PI * np.arange(257) / (surface.n_field_periods * 257)
    t, p = np.meshgrid(theta, phi, indexing="ij")
    expected_radius = reference_radius(t, p)
    actual_radius, actual_dtheta, actual_dphi = surface.radius(t, p)
    error = np.abs(actual_radius - expected_radius)
    expected_dt = reference_dtheta(t, p)
    expected_dp = reference_dphi(t, p)
    def geometry(radius, radius_theta, radius_phi):
        ct, st, cp, sp = np.cos(t), np.sin(t), np.cos(p), np.sin(p)
        major = 500.0 + radius * ct
        major_theta = radius_theta * ct - radius * st
        height_theta = radius_theta * st + radius * ct
        major_phi = radius_phi * ct
        height_phi = radius_phi * st
        position = np.stack((major * cp, major * sp, radius * st), axis=-1)
        dtheta = np.stack(
            (major_theta * cp, major_theta * sp, height_theta), axis=-1
        )
        dphi = np.stack(
            (
                major_phi * cp - major * sp,
                major_phi * sp + major * cp,
                height_phi,
            ), axis=-1
        )
        area_vector = np.cross(dphi, dtheta)
        return position, area_vector

    expected_position, expected_area_vector = geometry(
        expected_radius, expected_dt, expected_dp
    )
    actual_position, actual_area_vector = geometry(
        actual_radius, actual_dtheta, actual_dphi
    )
    expected_normal = expected_area_vector.copy()
    actual_normal = actual_area_vector.copy()
    expected_normal /= np.linalg.norm(expected_normal, axis=-1)[..., None]
    actual_normal /= np.linalg.norm(actual_normal, axis=-1)[..., None]
    angles = np.degrees(np.arccos(np.clip(
        np.sum(expected_normal * actual_normal, axis=-1), -1.0, 1.0
    )))
    classification = "PASS_SINGLE_CHART" if np.max(error) <= 0.01 else "FIT_TOLERANCE_NOT_MET"
    integration_weight = (
        TWO_PI / theta.size * TWO_PI / (surface.n_field_periods * phi.size)
        * surface.n_field_periods
    )
    expected_area = float(np.sum(np.linalg.norm(expected_area_vector, axis=-1))
                          * integration_weight)
    actual_area = float(np.sum(np.linalg.norm(actual_area_vector, axis=-1))
                        * integration_weight)
    expected_volume = float(abs(np.sum(expected_position * expected_area_vector))
                            / 3.0 * integration_weight)
    actual_volume = float(abs(np.sum(actual_position * actual_area_vector))
                          / 3.0 * integration_weight)
    return {
        "case": name,
        "classification": classification,
        "independent_points": error.size,
        "maximum_cartesian_error_cm": float(np.max(error)),
        "rms_cartesian_error_cm": float(np.sqrt(np.mean(error**2))),
        "p95_cartesian_error_cm": float(np.percentile(error, 95.0)),
        "approximate_hausdorff_error_cm": float(np.max(error)),
        "maximum_normal_angle_deg": float(np.max(angles)),
        "rms_normal_angle_deg": float(np.sqrt(np.mean(angles**2))),
        "surface_area_relative_error": (actual_area - expected_area) / expected_area,
        "volume_relative_error": (actual_volume - expected_volume) / expected_volume,
        "minimum_radius_cm": float(np.min(actual_radius)),
        "content_id": surface.content_id,
    }


def main():
    torus = PeriodicRadialSurfaceData.analytic_torus(
        name="exact_torus", major_radius_cm=500.0, minor_radius_cm=100.0,
        n_axis=8, n_theta=16, n_phi=12
    )
    torus_metrics = metrics(
        "exact_circular_torus", torus,
        lambda t, p: np.full_like(t, 100.0),
        lambda t, p: np.zeros_like(t),
        lambda t, p: np.zeros_like(t),
    )

    theta_fit = TWO_PI * np.arange(256) / 256
    phi_fit = TWO_PI * np.arange(64) / 64
    t_fit, p_fit = np.meshgrid(theta_fit, phi_fit, indexing="ij")
    miller_radius = lambda t, p: (
        105.0 + 17.0 * np.cos(t) - 7.0 * np.cos(2.0 * t)
        + 3.0 * np.sin(3.0 * t)
    )
    miller_dtheta = lambda t, p: (
        -17.0 * np.sin(t) + 14.0 * np.sin(2.0 * t)
        + 9.0 * np.cos(3.0 * t)
    )
    miller = PeriodicRadialSurfaceData.from_surface_grid(
        name="miller_like",
        xyz_cm=source_points(500.0, miller_radius(t_fit, p_fit), t_fit, p_fit),
        phi=phi_fit,
        n_field_periods=1,
        axis_r_cm=np.full(phi_fit.size, 500.0),
        axis_z_cm=np.zeros(phi_fit.size),
        n_theta_coefficients=256,
        source_metadata={"kind": "analytic_shaped_axisymmetric"},
    )
    miller_metrics = metrics(
        "shaped_axisymmetric_miller_like", miller, miller_radius,
        miller_dtheta, lambda t, p: np.zeros_like(t)
    )

    nfp = 5
    helical_radius = lambda t, p: (
        100.0 + 8.0 * np.cos(2.0 * t - nfp * p)
        + 3.0 * np.cos(3.0 * t + 2.0 * nfp * p)
    )
    helical_dtheta = lambda t, p: (
        -16.0 * np.sin(2.0 * t - nfp * p)
        - 9.0 * np.sin(3.0 * t + 2.0 * nfp * p)
    )
    helical_dphi = lambda t, p: (
        8.0 * nfp * np.sin(2.0 * t - nfp * p)
        - 6.0 * nfp * np.sin(3.0 * t + 2.0 * nfp * p)
    )
    phi_helical = TWO_PI * np.arange(128) / (nfp * 128)
    th, ph = np.meshgrid(theta_fit, phi_helical, indexing="ij")
    helical = PeriodicRadialSurfaceData.from_surface_grid(
        name="synthetic_helical",
        xyz_cm=source_points(500.0, helical_radius(th, ph), th, ph),
        phi=phi_helical,
        n_field_periods=nfp,
        axis_r_cm=np.full(phi_helical.size, 500.0),
        axis_z_cm=np.zeros(phi_helical.size),
        n_theta_coefficients=256,
        source_metadata={"kind": "analytic_multi_harmonic_helical"},
    )
    helical_metrics = metrics(
        "synthetic_multi_harmonic_helical", helical, helical_radius,
        helical_dtheta, helical_dphi
    )

    output_h5 = Path("dev/stellarcsg/qualified/analytic_periodic_surfaces.h5")
    write_surface_collection(output_h5, [torus, miller, helical], overwrite_file=True)
    reports = [torus_metrics, miller_metrics, helical_metrics]
    report_path = Path("dev/stellarcsg/reports/ANALYTIC_GEOMETRY_FIDELITY.json")
    report_path.write_text(json.dumps({"schema_version": 1, "cases": reports}, indent=2) + "\n")
    csv_path = Path("dev/stellarcsg/reports/GEOMETRY_FIDELITY.csv")
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(reports[0]))
        writer.writeheader()
        writer.writerows(reports)
    print(json.dumps({"cases": reports}, indent=2))
    return 0 if all(item["classification"] == "PASS_SINGLE_CHART" for item in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
