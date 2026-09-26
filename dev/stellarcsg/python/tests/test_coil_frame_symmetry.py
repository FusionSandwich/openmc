"""A near-vertical coil tangent must preserve the elliptical frame on rotation."""

import numpy as np

from stellarcsg.coil import SweptSplineData


def test_vertical_tangent_90_degree_frame_equivariance():
    angle = np.linspace(0.0, 2.0 * np.pi, 128, endpoint=False)
    points = np.column_stack((500.0 + 50.0 * np.cos(angle),
                              np.zeros_like(angle), 50.0 * np.sin(angle)))
    rotation = np.array([[0.0, -1.0, 0.0],
                         [1.0, 0.0, 0.0],
                         [0.0, 0.0, 1.0]])
    left = SweptSplineData.from_centerline(
        1, points, major_radius_cm=10.0, minor_radius_cm=8.0)
    right = SweptSplineData.from_centerline(
        2, points @ rotation.T, major_radius_cm=10.0, minor_radius_cm=8.0)
    for name in ("centerline_coefficients_cm", "normal_coefficients",
                 "binormal_coefficients"):
        assert np.max(np.linalg.norm(
            getattr(left, name) @ rotation.T - getattr(right, name), axis=1
        )) < 1.0e-8
    np.testing.assert_array_equal(left.major_radius_coefficients_cm,
                                  right.major_radius_coefficients_cm)
    np.testing.assert_array_equal(left.minor_radius_coefficients_cm,
                                  right.minor_radius_coefficients_cm)
