"""Synthetic controls; high-precision references are formed independently."""

from decimal import Decimal, localcontext
import math
import unittest

import numpy as np

from fourier_torus import (
    Disposition,
    IntervalKind,
    RayInterval,
    VmecBoundary,
    composition_interpretations,
    elliptical_torus_implicit,
    one_harmonic_radius,
    refine_ray_candidates,
    torus_ray_candidates,
)


def decimal_outer_root(x0: str, dx: str, radius: str, major: str) -> float:
    """Solve x(t)=major-radius in Decimal, without using the ray refiner."""
    with localcontext() as ctx:
        ctx.prec = 60
        return float((Decimal(major) - Decimal(radius) - Decimal(x0)) / Decimal(dx))


class FourierTorusTests(unittest.TestCase):
    def make_vmec(self) -> VmecBoundary:
        # xn=10 is already 2*nfp for nfp=5; never multiply by nfp again.
        return VmecBoundary(
            nfp=5,
            xm=np.array([0, 1, 1]),
            xn=np.array([0, 0, 10]),
            rmnc_m=np.array([3.0, 0.4, 0.07]),
            zmns_m=np.array([0.0, 0.4, -0.03]),
            rmns_m=np.array([0.02, -0.01, 0.015]),
            zmnc_m=np.array([0.01, 0.025, -0.012]),
        )

    def test_vmec_asymmetry_xn_convention_and_metres_to_cm(self) -> None:
        b = self.make_vmec()
        theta, phi = 0.37, 0.23
        phase = np.array([0.0, theta, theta - 10.0 * phi])
        expected_r_m = np.sum(b.rmnc_m * np.cos(phase) + b.rmns_m * np.sin(phase))
        expected_z_m = np.sum(b.zmns_m * np.sin(phase) + b.zmnc_m * np.cos(phase))
        p = b.position_cm(theta, phi)
        self.assertAlmostEqual(p[0], 100.0 * expected_r_m * math.cos(phi), places=12)
        self.assertAlmostEqual(p[1], 100.0 * expected_r_m * math.sin(phi), places=12)
        self.assertAlmostEqual(p[2], 100.0 * expected_z_m, places=12)
        # This point differs if xn is incorrectly multiplied by nfp again.
        wrong_phase = np.array([0.0, theta, theta - 50.0 * phi])
        wrong_r = np.sum(b.rmnc_m * np.cos(wrong_phase) + b.rmns_m * np.sin(wrong_phase))
        self.assertGreater(abs(expected_r_m - wrong_r), 1.0e-3)

    def test_vmec_field_period_seam(self) -> None:
        b = self.make_vmec()
        theta = np.linspace(0.0, 2.0 * math.pi, 19)
        p0 = b.position_cm(theta, np.zeros_like(theta))
        p1 = b.position_cm(theta, np.full_like(theta, 2.0 * math.pi / b.nfp))
        # Cartesian positions rotate with phi; R and Z Fourier components repeat.
        r0, z0 = b.rz_m(theta, 0.0)
        r1, z1 = b.rz_m(theta, 2.0 * math.pi / b.nfp)
        np.testing.assert_allclose(r0, r1, atol=2e-14)
        np.testing.assert_allclose(z0, z1, atol=2e-14)
        self.assertFalse(np.allclose(p0, p1))

    def test_exact_circular_and_elliptical_torus_controls(self) -> None:
        r0, a, b = 4.0, 1.0, 0.5
        self.assertAlmostEqual(elliptical_torus_implicit((r0 + a, 0, 0), r0, a, b), 0.0)
        self.assertAlmostEqual(elliptical_torus_implicit((r0, 0, b), r0, a, b), 0.0)
        self.assertAlmostEqual(elliptical_torus_implicit((r0, 0, 0), r0, a, a), -1.0)
        self.assertLess(elliptical_torus_implicit((r0 + 0.25, 0, 0.1), r0, a, b), 0.0)
        with self.assertRaises(ValueError):
            elliptical_torus_implicit((1, 0, 0), 2, 0, 1)

    def test_quartic_torus_candidates_match_decimal_radial_roots(self) -> None:
        # Independent Decimal line/surface solve gives x=R0-a and x=R0+a.
        first = decimal_outer_root("1", "1", "1", "5")
        second = decimal_outer_root("1", "1", "-1", "5")
        roots = torus_ray_candidates((1, 0, 0), (1, 0, 0), 5, 1, 0.5)
        self.assertEqual(len(roots), 2)
        self.assertAlmostEqual(roots[0], first, delta=1e-8)
        self.assertAlmostEqual(roots[1], second, delta=1e-8)
        self.assertEqual(torus_ray_candidates((1, 0, 0), (1, 0, 0), 5, 1, 0.5, 2.0), ())
        with self.assertRaises(ValueError):
            torus_ray_candidates((1, 0, 0), (2, 0, 0), 5, 1, 0.5)
        # A grazing root is useful as a candidate but remains unresolved by the
        # sign-changing refinement interface (tested separately below).
        tangent = torus_ray_candidates((-1, 6, 0), (1, 0, 0), 5, 1, 0.5)
        self.assertTrue(any(abs(t - 1.0) < 1e-5 for t in tangent))

    def test_torus_fit_residual_bound_contains_dense_synthetic_surface(self) -> None:
        boundary = self.make_vmec()
        fit, (br, bz, b3) = boundary.torus_fit_and_bound_m()
        self.assertGreaterEqual(br, 0.0)
        self.assertGreaterEqual(bz, 0.0)
        self.assertAlmostEqual(b3, math.hypot(br, bz))
        theta = np.linspace(0.0, 2.0 * math.pi, 47, endpoint=False)
        phi = np.linspace(0.0, 2.0 * math.pi / boundary.nfp, 31, endpoint=False)
        tt, pp = np.meshgrid(theta, phi, indexing="ij")
        r, z = boundary.rz_m(tt, pp)
        residual_r = r - (fit.r0_m + fit.minor_radius_m * np.cos(tt))
        residual_z = z - fit.minor_radius_m * np.sin(tt)
        self.assertLessEqual(float(np.max(np.abs(residual_r))), br + 1e-14)
        self.assertLessEqual(float(np.max(np.abs(residual_z))), bz + 1e-14)
        self.assertLessEqual(float(np.max(np.hypot(residual_r, residual_z))), b3 + 1e-14)

    def test_original_parametric_sum_reconstructs_one_harmonic_exactly(self) -> None:
        theta = np.linspace(0.0, 2.0 * math.pi, 37)
        phi = np.linspace(0.0, 2.0 * math.pi, 41)
        tt, pp = np.meshgrid(theta, phi, indexing="ij")
        major, base, eps, n = 5.0, 0.8, 0.12, 3
        radius = base + eps * np.cos(n * pp)
        r, z = one_harmonic_radius(tt, pp, major, base, eps, n)
        # A sum of the base torus and its Fourier displacement reconstructs it.
        np.testing.assert_allclose(r, major + base * np.cos(tt) + eps * np.cos(n * pp) * np.cos(tt))
        np.testing.assert_allclose(z, base * np.sin(tt) + eps * np.cos(n * pp) * np.sin(tt))
        self.assertTrue(np.all(radius > 0.0))
        self.assertEqual(set(composition_interpretations()), {
            "boolean_solids", "weighted_implicit_sum", "parametric_displacements", "nonlinear_coordinate_map"
        })
        self.assertIn("coupled surface solve", composition_interpretations()["parametric_displacements"])

    def test_decimal_reference_first_of_competing_roots(self) -> None:
        expected = decimal_outer_root("1", "1", "1", "5")  # first root x=R0-a, t=3
        second = decimal_outer_root("1", "1", "-1", "5")  # x=R0+a, t=5
        self.assertEqual(expected, 3.0)
        self.assertEqual(second, 5.0)
        f = lambda t: (1.0 + t - 5.0) ** 2 - 1.0
        windows = [
            RayInterval(0.0, 2.9, IntervalKind.CERTIFIED_EXCLUDED),
            RayInterval(2.9, 3.1, IntervalKind.CERTIFIED_SINGLE_ROOT),
            RayInterval(3.1, 4.9, IntervalKind.CERTIFIED_EXCLUDED),
            RayInterval(4.9, 5.1, IntervalKind.CERTIFIED_SINGLE_ROOT),
            RayInterval(5.1, 8.0, IntervalKind.CERTIFIED_EXCLUDED),
        ]
        result = refine_ray_candidates(windows, f, 8.0, distance_tolerance=1e-13)
        self.assertEqual(result.disposition, Disposition.HIT)
        self.assertAlmostEqual(result.distance, expected, delta=1e-12)
        # Without proof for the earlier candidate interval, the later root cannot win.
        windows[0] = RayInterval(0.0, 2.9, IntervalKind.CERTIFIED_EXCLUDED)
        windows[1] = RayInterval(2.9, 3.1, IntervalKind.UNKNOWN)
        self.assertEqual(refine_ray_candidates(windows, f, 8.0).disposition, Disposition.UNRESOLVED)

    def test_decimal_reference_thin_chord(self) -> None:
        with localcontext() as ctx:
            ctx.prec = 60
            y = Decimal("0.999999999")
            x = (Decimal(1) - y * y).sqrt()
            expected = float(Decimal(1) - x)  # x(t)=-1+t enters the unit circle here
        f = lambda t: (-1.0 + t) ** 2 + float(Decimal("0.999999999") ** 2) - 1.0
        hi = expected + 4e-5
        lo = expected - 4e-5
        windows = [RayInterval(0.0, lo, IntervalKind.CERTIFIED_EXCLUDED),
                   RayInterval(lo, hi, IntervalKind.CERTIFIED_SINGLE_ROOT),
                   RayInterval(hi, 2.0, IntervalKind.CERTIFIED_EXCLUDED)]
        result = refine_ray_candidates(windows, f, 2.0, distance_tolerance=1e-13)
        self.assertEqual(result.disposition, Disposition.HIT)
        self.assertAlmostEqual(result.distance, expected, delta=1e-11)

    def test_tangency_coincidence_and_seams_remain_unresolved(self) -> None:
        tangent = lambda t: (-1.0 + t) ** 2
        tangent_windows = [RayInterval(0.0, 0.9, IntervalKind.CERTIFIED_EXCLUDED),
                           RayInterval(0.9, 1.1, IntervalKind.CANDIDATE),
                           RayInterval(1.1, 2.0, IntervalKind.CERTIFIED_EXCLUDED)]
        self.assertEqual(refine_ray_candidates(tangent_windows, tangent, 2.0).disposition,
                         Disposition.UNRESOLVED)
        self.assertEqual(refine_ray_candidates(tangent_windows, tangent, 2.0, coincident=True).disposition,
                         Disposition.UNRESOLVED)
        # Sign changes alone do not isolate the earliest root within a window.
        three_roots = lambda t: (t - 0.1) * (t - 0.2) * (t - 0.8)
        multi_root_window = [RayInterval(0.0, 1.0, IntervalKind.CANDIDATE)]
        result = refine_ray_candidates(multi_root_window, three_roots, 1.0)
        self.assertEqual(result.disposition, Disposition.UNRESOLVED)
        self.assertIsNone(result.distance)
        gap = [RayInterval(0.0, 0.5, IntervalKind.CERTIFIED_EXCLUDED),
               RayInterval(0.6, 1.0, IntervalKind.CERTIFIED_EXCLUDED)]
        self.assertEqual(refine_ray_candidates(gap, tangent, 1.0).disposition, Disposition.UNRESOLVED)

    def test_no_hit_requires_complete_certified_coverage(self) -> None:
        windows = [RayInterval(0.0, 2.0, IntervalKind.CERTIFIED_EXCLUDED),
                   RayInterval(2.0, 7.0, IntervalKind.CERTIFIED_EXCLUDED)]
        self.assertEqual(refine_ray_candidates(windows, lambda t: 1.0, 7.0).disposition,
                         Disposition.NO_HIT)
        self.assertEqual(refine_ray_candidates(windows[:1], lambda t: 1.0, 7.0).disposition,
                         Disposition.UNRESOLVED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
