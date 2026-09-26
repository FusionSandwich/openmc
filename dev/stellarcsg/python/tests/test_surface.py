from __future__ import annotations

import numpy as np
import pytest

from stellarcsg import (
    PeriodicRadialSurfaceData,
    compile_normal_build,
    compile_radial_build,
)
from stellarcsg.spline import (
    sample_periodic_bicubic,
    sample_periodic_cubic,
    samples_to_periodic_coefficients,
)


def test_periodic_coefficient_transform_interpolates_knots() -> None:
    angle = 2.0 * np.pi * np.arange(16) / 16
    samples = 5.0 + 0.2 * np.cos(angle) - 0.1 * np.sin(3.0 * angle)
    coefficients = samples_to_periodic_coefficients(samples)
    reconstructed, derivative = sample_periodic_cubic(coefficients, angle)
    np.testing.assert_allclose(reconstructed, samples, rtol=0.0, atol=2.0e-14)
    h = 1.0e-6
    plus, _ = sample_periodic_cubic(coefficients, angle + h)
    minus, _ = sample_periodic_cubic(coefficients, angle - h)
    finite_difference = (plus - minus) / (2.0 * h)
    np.testing.assert_allclose(derivative, finite_difference, rtol=0.0, atol=1.0e-8)


def test_bicubic_transform_interpolates_knots() -> None:
    theta = 2.0 * np.pi * np.arange(20) / 20
    psi = 2.0 * np.pi * np.arange(12) / 12
    samples = 1.0 + 0.1 * np.cos(2.0 * theta[:, None] - psi[None, :])
    coefficients = samples_to_periodic_coefficients(samples)
    t, p = np.meshgrid(theta, psi / 5.0, indexing="ij")
    value, _, _ = sample_periodic_bicubic(coefficients, t, p, 5)
    np.testing.assert_allclose(value, samples, rtol=0.0, atol=3.0e-14)


def test_analytic_torus_surface_and_periodicity() -> None:
    surface = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma",
        major_radius_cm=500.0,
        minor_radius_cm=100.0,
        n_field_periods=5,
        helical_amplitude_cm=8.0,
        n_theta=32,
        n_phi=24,
    )
    theta = np.linspace(0.0, 2.0 * np.pi, 57, endpoint=False)
    phi = np.linspace(0.0, 2.0 * np.pi / 5.0, 41, endpoint=False)
    t, p = np.meshgrid(theta, phi, indexing="ij")
    points = surface.position(t, p)
    np.testing.assert_allclose(surface.evaluate(points), 0.0, rtol=0.0, atol=2.0e-12)
    periodic_points = surface.position(t, p + 2.0 * np.pi / 5.0)
    rotated = points.copy()
    angle = 2.0 * np.pi / 5.0
    rotated[..., 0] = points[..., 0] * np.cos(angle) - points[..., 1] * np.sin(angle)
    rotated[..., 1] = points[..., 0] * np.sin(angle) + points[..., 1] * np.cos(angle)
    np.testing.assert_allclose(periodic_points, rotated, rtol=0.0, atol=5.0e-12)


def test_surface_grid_compiler_reparameterizes_geometric_theta() -> None:
    n_theta = 40
    n_phi = 16
    nfp = 4
    parameter = 2.0 * np.pi * np.arange(n_theta) / n_theta
    phi = 2.0 * np.pi * np.arange(n_phi) / (nfp * n_phi)
    q, p = np.meshgrid(parameter, phi, indexing="ij")
    theta_geo = q + 0.08 * np.sin(q)
    rho = 80.0 + 6.0 * np.cos(2.0 * theta_geo - nfp * p)
    axis_r = 400.0 + 2.0 * np.cos(nfp * phi)
    axis_z = 1.5 * np.sin(nfp * phi)
    R = axis_r[None, :] + rho * np.cos(theta_geo)
    Z = axis_z[None, :] + rho * np.sin(theta_geo)
    xyz = np.stack((R * np.cos(p), R * np.sin(p), Z), axis=-1)

    surface = PeriodicRadialSurfaceData.from_surface_grid(
        name="grid",
        xyz_cm=xyz,
        phi=phi,
        n_field_periods=nfp,
        axis_r_cm=axis_r,
        axis_z_cm=axis_z,
        n_theta_coefficients=48,
    )
    test_theta = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    test_phi = np.linspace(0.0, 2.0 * np.pi / nfp, 31, endpoint=False)
    t, p_test = np.meshgrid(test_theta, test_phi, indexing="ij")
    points = surface.position(t, p_test)
    np.testing.assert_allclose(surface.evaluate(points), 0.0, rtol=0.0, atol=3.0e-12)
    assert surface.source_metadata is not None
    assert surface.source_metadata["axis_inferred"] is False


def test_radial_build_is_strictly_nested() -> None:
    base = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma", major_radius_cm=500.0, minor_radius_cm=100.0
    )
    boundaries = compile_radial_build(
        base,
        [("first_wall", 2.0), ("blanket", 50.0), ("shield", 40.0)],
    )
    theta = np.linspace(0.0, 2.0 * np.pi, 48, endpoint=False)
    phi = np.linspace(0.0, 2.0 * np.pi, 48, endpoint=False)
    t, p = np.meshgrid(theta, phi, indexing="ij")
    radii = [surface.radius(t, p)[0] for surface in boundaries]
    np.testing.assert_allclose(radii[1] - radii[0], 2.0, atol=2.0e-13)
    np.testing.assert_allclose(radii[2] - radii[1], 50.0, atol=2.0e-13)
    np.testing.assert_allclose(radii[3] - radii[2], 40.0, atol=2.0e-13)
    assert len({surface.content_id for surface in boundaries}) == len(boundaries)


def test_nonpositive_thickness_rejected() -> None:
    base = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma", major_radius_cm=500.0, minor_radius_cm=100.0
    )
    with pytest.raises(ValueError):
        base.with_radial_thickness("bad", 0.0)


def test_physical_normal_build_for_exact_torus() -> None:
    base = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma",
        major_radius_cm=500.0,
        minor_radius_cm=100.0,
        n_theta=16,
        n_phi=12,
    )
    boundaries = compile_normal_build(
        base, [("first_wall", 2.0), ("blanket", 25.0)]
    )
    theta = np.linspace(0.0, 2.0 * np.pi, 37, endpoint=False)
    phi = np.linspace(0.0, 2.0 * np.pi, 29, endpoint=False)
    t, p = np.meshgrid(theta, phi, indexing="ij")
    base_radius = boundaries[0].radius(t, p)[0]
    first_wall_radius = boundaries[1].radius(t, p)[0]
    blanket_radius = boundaries[2].radius(t, p)[0]
    np.testing.assert_allclose(first_wall_radius - base_radius, 2.0, atol=2.0e-11)
    np.testing.assert_allclose(blanket_radius - first_wall_radius, 25.0, atol=2.0e-11)
    assert boundaries[1].source_metadata["kind"] == "physical_normal_offset"
