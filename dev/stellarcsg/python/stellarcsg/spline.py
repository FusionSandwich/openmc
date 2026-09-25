"""Periodic cardinal cubic B-spline utilities used by the reference compiler."""

from __future__ import annotations

import numpy as np

_TWO_PI = 2.0 * np.pi


def _basis(u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return cardinal cubic basis values and derivatives for ``u in [0, 1)``."""
    u = np.asarray(u, dtype=np.float64)
    u2 = u * u
    u3 = u2 * u
    one_minus = 1.0 - u
    values = np.stack(
        (
            one_minus**3 / 6.0,
            (3.0 * u3 - 6.0 * u2 + 4.0) / 6.0,
            (-3.0 * u3 + 3.0 * u2 + 3.0 * u + 1.0) / 6.0,
            u3 / 6.0,
        ),
        axis=-1,
    )
    derivatives = np.stack(
        (
            -0.5 * one_minus**2,
            1.5 * u2 - 2.0 * u,
            -1.5 * u2 + u + 0.5,
            0.5 * u2,
        ),
        axis=-1,
    )
    return values, derivatives


def samples_to_periodic_coefficients(samples: np.ndarray) -> np.ndarray:
    """Convert values sampled on a uniform periodic knot grid to B-spline coefficients.

    The transform is exact up to floating-point roundoff for the uniform
    cardinal cubic basis used by both the Python and C++ kernels. It operates
    independently over every array axis.
    """
    values = np.asarray(samples, dtype=np.float64)
    if values.ndim not in (1, 2):
        raise ValueError("samples must be one- or two-dimensional")
    if any(size < 4 for size in values.shape):
        raise ValueError("each periodic dimension requires at least four samples")
    if not np.all(np.isfinite(values)):
        raise ValueError("samples must be finite")

    transformed = np.fft.fftn(values)
    denominator: np.ndarray | float = 1.0
    for axis, size in enumerate(values.shape):
        frequency = np.arange(size, dtype=np.float64)
        eigenvalue = (4.0 + 2.0 * np.cos(_TWO_PI * frequency / size)) / 6.0
        shape = [1] * values.ndim
        shape[axis] = size
        denominator = denominator * eigenvalue.reshape(shape)
    coefficients = np.fft.ifftn(transformed / denominator).real
    return np.asarray(coefficients, dtype=np.float64)


def sample_periodic_cubic(
    coefficients: np.ndarray,
    angle: np.ndarray | float,
    periodic_multiplier: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample a one-dimensional periodic cubic spline and physical derivative."""
    coeff = np.asarray(coefficients, dtype=np.float64)
    if coeff.ndim != 1 or coeff.size < 4:
        raise ValueError("coefficients must be a one-dimensional array of length >= 4")
    if periodic_multiplier <= 0:
        raise ValueError("periodic_multiplier must be positive")
    angle_array = np.asarray(angle, dtype=np.float64)
    reduced = np.mod(periodic_multiplier * angle_array, _TWO_PI)
    coordinate = reduced * coeff.size / _TWO_PI
    cell = np.floor(coordinate).astype(np.int64)
    u = coordinate - cell
    basis, derivative = _basis(u)
    result = np.zeros_like(angle_array, dtype=np.float64)
    result_derivative = np.zeros_like(angle_array, dtype=np.float64)
    scale = coeff.size * periodic_multiplier / _TWO_PI
    for offset in range(4):
        control = coeff[(cell + offset - 1) % coeff.size]
        result += control * basis[..., offset]
        result_derivative += control * derivative[..., offset] * scale
    return result, result_derivative


def sample_periodic_bicubic(
    coefficients: np.ndarray,
    theta: np.ndarray | float,
    phi: np.ndarray | float,
    n_field_periods: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample a theta/reduced-phi periodic bicubic spline and derivatives."""
    coeff = np.asarray(coefficients, dtype=np.float64)
    if coeff.ndim != 2 or min(coeff.shape) < 4:
        raise ValueError("coefficients must have shape (n_theta, n_phi), both >= 4")
    if n_field_periods <= 0:
        raise ValueError("n_field_periods must be positive")

    theta_array, phi_array = np.broadcast_arrays(
        np.asarray(theta, dtype=np.float64), np.asarray(phi, dtype=np.float64)
    )
    theta_coordinate = np.mod(theta_array, _TWO_PI) * coeff.shape[0] / _TWO_PI
    phi_coordinate = (
        np.mod(n_field_periods * phi_array, _TWO_PI) * coeff.shape[1] / _TWO_PI
    )
    theta_cell = np.floor(theta_coordinate).astype(np.int64)
    phi_cell = np.floor(phi_coordinate).astype(np.int64)
    u = theta_coordinate - theta_cell
    v = phi_coordinate - phi_cell
    theta_basis, theta_derivative = _basis(u)
    phi_basis, phi_derivative = _basis(v)
    value = np.zeros_like(theta_array, dtype=np.float64)
    dtheta = np.zeros_like(theta_array, dtype=np.float64)
    dphi = np.zeros_like(theta_array, dtype=np.float64)
    theta_scale = coeff.shape[0] / _TWO_PI
    phi_scale = coeff.shape[1] * n_field_periods / _TWO_PI
    for a in range(4):
        for b in range(4):
            control = coeff[
                (theta_cell + a - 1) % coeff.shape[0],
                (phi_cell + b - 1) % coeff.shape[1],
            ]
            value += control * theta_basis[..., a] * phi_basis[..., b]
            dtheta += (
                control
                * theta_derivative[..., a]
                * theta_scale
                * phi_basis[..., b]
            )
            dphi += (
                control
                * theta_basis[..., a]
                * phi_derivative[..., b]
                * phi_scale
            )
    return value, dtheta, dphi
