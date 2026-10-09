"""Small, dependency-light Fourier/torus geometry research prototype.

This is not an OpenMC surface implementation. Its ray API reports HIT only
when supplied intervals cover the queried ray and all earlier intervals are
certified excluded. Uncovered or even-multiplicity cases stay UNRESOLVED.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Callable, Iterable, Sequence

import numpy as np


class Disposition(str, Enum):
    HIT = "HIT"
    NO_HIT = "NO_HIT"
    UNRESOLVED = "UNRESOLVED"


class IntervalKind(str, Enum):
    CERTIFIED_EXCLUDED = "CERTIFIED_EXCLUDED"
    CANDIDATE = "CANDIDATE"
    CERTIFIED_SINGLE_ROOT = "CERTIFIED_SINGLE_ROOT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RayInterval:
    lower: float
    upper: float
    kind: IntervalKind


@dataclass(frozen=True)
class RayResult:
    disposition: Disposition
    distance: float | None = None
    reason: str = ""


@dataclass(frozen=True)
class VmecBoundary:
    """Boundary Fourier coefficients from the last radial VMEC surface.

    ``xn`` is used exactly as stored in wout (it already includes nfp).
    Stored lengths are metres; ``position_cm`` returns centimetres. Missing
    asymmetric coefficient arrays mean zero, as in stellarator-symmetric wout.
    """

    nfp: int
    xm: np.ndarray
    xn: np.ndarray
    rmnc_m: np.ndarray
    zmns_m: np.ndarray
    rmns_m: np.ndarray | None = None
    zmnc_m: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.nfp <= 0:
            raise ValueError("nfp must be positive")
        arrays = (self.xm, self.xn, self.rmnc_m, self.zmns_m)
        nmode = np.asarray(self.xm).size
        if nmode == 0 or any(np.asarray(a).shape != (nmode,) for a in arrays):
            raise ValueError("VMEC coefficient arrays must be nonempty and equal length")
        for optional in (self.rmns_m, self.zmnc_m):
            if optional is not None and np.asarray(optional).shape != (nmode,):
                raise ValueError("asymmetric coefficient arrays must match xm")
        for name in ("xm", "xn", "rmnc_m", "zmns_m", "rmns_m", "zmnc_m"):
            value = getattr(self, name)
            if value is not None:
                array = np.asarray(value, dtype=np.float64).copy()
                if not np.all(np.isfinite(array)):
                    raise ValueError(f"{name} contains non-finite values")
                array.setflags(write=False)
                object.__setattr__(self, name, array)

    @classmethod
    def from_wout(cls, path: str) -> "VmecBoundary":
        """Read wout arrays using the already-installed scipy NetCDF reader."""
        from scipy.io import netcdf_file

        with netcdf_file(path, "r", mmap=False) as handle:
            variables = handle.variables

            def required(name: str) -> np.ndarray:
                return np.array(variables[name].data, dtype=np.float64, copy=True)

            def optional(name: str) -> np.ndarray | None:
                return required(name)[-1] if name in variables else None

            return cls(
                nfp=int(np.asarray(variables["nfp"].data).item()),
                xm=required("xm"),
                xn=required("xn"),
                rmnc_m=required("rmnc")[-1],
                zmns_m=required("zmns")[-1],
                rmns_m=optional("rmns"),
                zmnc_m=optional("zmnc"),
            )

    def rz_m(self, theta: np.ndarray | float, phi: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
        theta_a, phi_a = np.broadcast_arrays(np.asarray(theta, dtype=float), np.asarray(phi, dtype=float))
        phase = theta_a[..., None] * self.xm - phi_a[..., None] * self.xn
        r = np.sum(self.rmnc_m * np.cos(phase), axis=-1)
        z = np.sum(self.zmns_m * np.sin(phase), axis=-1)
        if self.rmns_m is not None:
            r = r + np.sum(self.rmns_m * np.sin(phase), axis=-1)
        if self.zmnc_m is not None:
            z = z + np.sum(self.zmnc_m * np.cos(phase), axis=-1)
        return r, z

    def position_cm(self, theta: np.ndarray | float, phi: np.ndarray | float) -> np.ndarray:
        theta_a, phi_a = np.broadcast_arrays(np.asarray(theta, dtype=float), np.asarray(phi, dtype=float))
        r_m, z_m = self.rz_m(theta_a, phi_a)
        return 100.0 * np.stack((r_m * np.cos(phi_a), r_m * np.sin(phi_a), z_m), axis=-1)

    def torus_fit_and_bound_m(self) -> tuple["TorusFit", tuple[float, float, float]]:
        """Fit a circular torus and return coefficient-sum coordinate bounds.

        The R and Z bounds are uniform over all angles by the triangle
        inequality. The third bound is sqrt(BR**2 + BZ**2), hence a positional
        bound at matching (theta, phi). This does not bound signed distance,
        normals, or ray-intersection error.
        """
        mode00 = np.flatnonzero((self.xm == 0) & (self.xn == 0))
        mode10 = np.flatnonzero((self.xm == 1) & (self.xn == 0))
        if len(mode00) != 1 or len(mode10) != 1:
            raise ValueError("torus fit requires unique (m,n)=(0,0) and (1,0) modes")
        i00, i10 = int(mode00[0]), int(mode10[0])
        r0 = float(self.rmnc_m[i00])
        a_r = float(self.rmnc_m[i10])
        a_z = float(self.zmns_m[i10])
        a = 0.5 * (a_r + a_z)
        if not (r0 > a > 0.0):
            raise ValueError("fitted torus must have R0 > a > 0")
        fit = TorusFit(r0_m=r0, minor_radius_m=a)
        r_cos = np.zeros_like(self.rmnc_m)
        r_sin = np.zeros_like(self.rmnc_m)
        z_sin = np.zeros_like(self.zmns_m)
        z_cos = np.zeros_like(self.zmns_m)
        r_cos[i00] = r0
        r_cos[i10] = a
        z_sin[i10] = a
        br = float(np.sum(np.abs(self.rmnc_m - r_cos)))
        bz = float(np.sum(np.abs(self.zmns_m - z_sin)))
        if self.rmns_m is not None:
            br += float(np.sum(np.abs(self.rmns_m - r_sin)))
        if self.zmnc_m is not None:
            bz += float(np.sum(np.abs(self.zmnc_m - z_cos)))
        return fit, (br, bz, math.hypot(br, bz))


@dataclass(frozen=True)
class TorusFit:
    r0_m: float
    minor_radius_m: float


def elliptical_torus_implicit(point: Sequence[float], r0: float, a: float, b: float) -> float:
    """Dimensionless implicit F for a torus with elliptical tube section."""
    x, y, z = map(float, point)
    if r0 <= 0 or a <= 0 or b <= 0:
        raise ValueError("torus radii must be positive")
    radial = math.hypot(x, y)
    return ((radial - r0) / a) ** 2 + (z / b) ** 2 - 1.0


def torus_ray_candidates(origin: Sequence[float], direction: Sequence[float],
                         r0: float, a: float, b: float,
                         max_distance: float = math.inf) -> tuple[float, ...]:
    """Return real quartic roots as torus candidates, never as a certificate.

    Squaring the elliptical-torus equation yields a quartic in ray distance.
    Real roots are filtered against the unsquared surface equation. Floating
    polynomial roots can still lose a grazing/double root; callers must keep
    their fallback or report UNRESOLVED rather than treating an empty tuple as
    a proof of NO_HIT.
    """
    o = np.asarray(origin, dtype=np.float64)
    d = np.asarray(direction, dtype=np.float64)
    if o.shape != (3,) or d.shape != (3,) or not np.all(np.isfinite(o)) or not np.all(np.isfinite(d)):
        raise ValueError("origin and direction must be finite 3-vectors")
    direction_norm = float(np.linalg.norm(d))
    if direction_norm == 0.0 or r0 <= 0.0 or a <= 0.0 or b <= 0.0:
        raise ValueError("direction and torus radii must be nonzero and positive")
    if not math.isclose(direction_norm, 1.0, rel_tol=1.0e-12, abs_tol=1.0e-12):
        raise ValueError("direction must be unit length so t is physical ray distance")
    if max_distance < 0.0:
        raise ValueError("max_distance must be nonnegative")
    # Ascending polynomial coefficients for x(t)^2 + y(t)^2 and z(t)^2.
    q = np.polynomial.polynomial.polyadd(
        np.polynomial.polynomial.polymul((o[0], d[0]), (o[0], d[0])),
        np.polynomial.polynomial.polymul((o[1], d[1]), (o[1], d[1])),
    )
    z2 = np.polynomial.polynomial.polymul((o[2], d[2]), (o[2], d[2]))
    aq = np.polynomial.polynomial.polyadd(
        b * b * q,
        np.polynomial.polynomial.polyadd(
            (b * b * (r0 * r0 - a * a),), a * a * z2
        ),
    )
    quartic = np.polynomial.polynomial.polysub(
        np.polynomial.polynomial.polymul(aq, aq), 4.0 * b**4 * r0**2 * q
    )
    nonzero = np.flatnonzero(np.abs(quartic) > np.finfo(float).tiny)
    if len(nonzero) == 0:
        return ()
    roots = np.polynomial.polynomial.polyroots(quartic[: nonzero[-1] + 1])
    candidates: list[float] = []
    for root in roots:
        t = float(root.real)
        if abs(float(root.imag)) > 2.0e-7 * max(1.0, abs(t)):
            continue
        if t < -1.0e-10 or t > max_distance + 1.0e-10:
            continue
        t = max(0.0, t)
        point = o + t * d
        radial2 = point[0] ** 2 + point[1] ** 2
        # The unsquared equation requires its isolated square-root term >= 0.
        lhs = b * b * (radial2 + r0 * r0 - a * a) + a * a * point[2] ** 2
        if lhs < -1.0e-8 * max(1.0, abs(lhs)):
            continue
        if abs(elliptical_torus_implicit(point, r0, a, b)) <= 2.0e-6:
            candidates.append(t)
    candidates.sort()
    unique: list[float] = []
    for t in candidates:
        if not unique or abs(t - unique[-1]) > 1.0e-7 * max(1.0, abs(t)):
            unique.append(t)
    return tuple(unique)


def _bisect_sign_change(function: Callable[[float], float], lo: float, hi: float,
                        distance_tolerance: float, max_iterations: int) -> float | None:
    flo, fhi = function(lo), function(hi)
    if not (math.isfinite(flo) and math.isfinite(fhi)):
        return None
    if flo == 0.0:
        return lo
    if fhi == 0.0:
        return hi
    if flo * fhi > 0.0:
        return None
    for _ in range(max_iterations):
        mid = lo + (hi - lo) * 0.5
        fm = function(mid)
        if not math.isfinite(fm):
            return None
        if fm == 0.0 or hi - lo <= distance_tolerance:
            return mid
        if (flo < 0.0) == (fm < 0.0):
            lo, flo = mid, fm
        else:
            hi, fhi = mid, fm
    return None


def refine_ray_candidates(
    intervals: Iterable[RayInterval],
    boundary_function: Callable[[float], float],
    max_distance: float,
    *,
    coincident: bool = False,
    distance_tolerance: float = 1.0e-12,
    max_iterations: int = 256,
) -> RayResult:
    """Refine candidate windows without upgrading missing coverage to a miss.

    Windows must exactly cover [0, max_distance] without gaps or overlaps.
    ``CERTIFIED_EXCLUDED`` and ``CERTIFIED_SINGLE_ROOT`` are proof labels that
    must come from a sound external isolator. A mere ``CANDIDATE`` is never
    enough to report HIT, even when its endpoints change sign: multiple roots
    in that window can make bisection converge to a later crossing. A
    certified single-root interval must bracket a sign-changing root.
    Tangencies, coincidences, invalid evaluations, unknown windows and gaps
    return UNRESOLVED. This function does not create the required certificates.
    """
    if coincident:
        return RayResult(Disposition.UNRESOLVED, reason="coincident-start ownership is not specified")
    if not (math.isfinite(max_distance) and max_distance >= 0.0 and distance_tolerance > 0.0):
        raise ValueError("max_distance and distance_tolerance must be finite and positive")
    windows = sorted(intervals, key=lambda item: (item.lower, item.upper))
    if not windows:
        return RayResult(Disposition.UNRESOLVED, reason="no coverage intervals")
    cursor = 0.0
    eps = max(1e-14, 4.0 * math.ulp(max(1.0, max_distance)))
    for window in windows:
        if (not math.isfinite(window.lower) or not math.isfinite(window.upper)
                or window.lower < 0.0 or window.upper < window.lower):
            return RayResult(Disposition.UNRESOLVED, reason="invalid interval")
        if abs(window.lower - cursor) > eps:
            return RayResult(Disposition.UNRESOLVED, reason="interval coverage has a gap or overlap")
        if window.upper > max_distance + eps:
            return RayResult(Disposition.UNRESOLVED, reason="interval exceeds query ceiling")
        if window.kind is IntervalKind.UNKNOWN:
            return RayResult(Disposition.UNRESOLVED, reason="earliest possible interval is unknown")
        if window.kind is IntervalKind.CANDIDATE:
            return RayResult(Disposition.UNRESOLVED,
                             reason="candidate lacks a certified single-root interval")
        if window.kind is IntervalKind.CERTIFIED_SINGLE_ROOT:
            root = _bisect_sign_change(boundary_function, window.lower, window.upper,
                                       distance_tolerance, max_iterations)
            if root is None:
                return RayResult(Disposition.UNRESOLVED,
                                 reason="certified interval lacks a finite sign-changing root bracket")
            return RayResult(Disposition.HIT, root, "all earlier windows were certified excluded")
        cursor = window.upper
    if abs(cursor - max_distance) > eps:
        return RayResult(Disposition.UNRESOLVED, reason="query ceiling is not covered")
    return RayResult(Disposition.NO_HIT, reason="entire ray interval was certified excluded")


def one_harmonic_radius(theta: np.ndarray | float, phi: np.ndarray | float,
                        major_radius: float, base_radius: float,
                        amplitude: float, mode: int) -> tuple[np.ndarray, np.ndarray]:
    """Exact parametric-sum interpretation: a torus plus one radial mode."""
    theta_a, phi_a = np.broadcast_arrays(np.asarray(theta, dtype=float), np.asarray(phi, dtype=float))
    radius = base_radius + amplitude * np.cos(mode * phi_a)
    return major_radius + radius * np.cos(theta_a), radius * np.sin(theta_a)


def composition_interpretations() -> dict[str, str]:
    """Explicit, distinct readings of the original torus-composition idea."""
    return {
        "boolean_solids": "Union/intersection of solid torus primitives; exact only for the resulting Boolean solid, with seams and duplicates to resolve.",
        "weighted_implicit_sum": "Set sum_i w_i F_i(x)=0; generally changes the surface and may raise ray-root degree beyond a quartic.",
        "parametric_displacements": "Sum Fourier displacement fields on a parameterized torus; can reconstruct modes exactly, but ray intersection remains a coupled surface solve.",
        "nonlinear_coordinate_map": "Map a reference torus through a nonlinear transform; physical straight rays generally become curved transformed paths.",
    }

