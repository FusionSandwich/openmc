"""Controls for the new attempts; old prototype tests remain unchanged."""

from decimal import Decimal, localcontext
import math
import unittest

import numpy as np

from patch_methods import (
    HybridRadius, SplineRadius, SharedIndex, TorusPatch, compile_torus_sum,
    fit_fourier_patch, fourier_jet, polynomial_design, polynomial_ray, profile_field, profile_normal,
    query_diagnostic, surface_frame, synthetic_boundary, torus_polynomial,
)


class PatchControls(unittest.TestCase):
    def test_fourier_jet_matches_independent_analytic_surface(self):
        theta, phi = 0.41, 0.17
        a = 0.8 + 0.12 * math.cos(3 * phi)
        da = -0.36 * math.sin(3 * phi)
        jet = fourier_jet(synthetic_boundary(), theta, phi)
        p = np.array([(5 + a * math.cos(theta)) * math.cos(phi),
                      (5 + a * math.cos(theta)) * math.sin(phi), a * math.sin(theta)])
        np.testing.assert_allclose(jet[0], p, atol=1e-14)
        np.testing.assert_allclose(surface_frame(jet)[1], profile_normal(theta, phi, a, da), atol=1e-13)

    def test_osculating_torus_exact_outer_and_inner_controls(self):
        boundary = synthetic_boundary(0)
        for theta in (0.0, math.pi):
            patch = TorusPatch.osculating(fourier_jet(boundary, theta, 0.0))
            self.assertAlmostEqual(patch.major, 5.0, places=12)
            self.assertAlmostEqual(patch.minor, 0.8, places=12)
            for dt, dp in ((0, 0), (0.04, 0.07), (-0.06, -0.03)):
                jet = fourier_jet(boundary, theta + dt, dp)
                p, normal, error = patch.project(jet[0])
                np.testing.assert_allclose(p, jet[0], atol=1e-13)
                np.testing.assert_allclose(normal, surface_frame(jet)[1], atol=1e-13)
                self.assertAlmostEqual(float(error), 0.0, places=12)
        with self.assertRaises(ValueError):
            TorusPatch.osculating(fourier_jet(boundary, math.pi / 2, 0))

    def test_trimmed_patch_rejects_other_side_of_torus(self):
        patch = TorusPatch.osculating(fourier_jet(synthetic_boundary(0), 0, 0))
        points = [fourier_jet(synthetic_boundary(0), t, p)[0]
                  for t in (-0.1, 0.1) for p in (-0.1, 0.1)]
        patch.set_sampled_trims(points)
        roots = patch.ray_candidates(np.array([0.1, 0, 0]), np.array([1, 0, 0]), 10)
        # Full torus roots are 4.1 and 5.7 from this origin. Only the outer
        # equator root belongs to the selected beta~0 patch.
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0], 5.7, delta=1e-8)

    def test_exact_fourier_dispatch_recovers_nonequatorial_torus(self):
        boundary = synthetic_boundary(0)
        patch = fit_fourier_patch(boundary, 0.7, 0.21)
        for theta, phi in ((0.7, 0.21), (0.8, 0.3), (0.5, 0.1)):
            p = fourier_jet(boundary, theta, phi)[0]
            np.testing.assert_allclose(patch.project(p)[0], p, atol=1e-13)

    def test_compiled_quartic_matches_independent_torus_equations(self):
        centers = [np.zeros(3), np.array([0.2, -0.1, 0.3])]
        axes = [np.array([0, 0, 1]), np.array([0, 1, 0])]
        polynomials = [torus_polynomial(c, a, 5, 0.8) for c, a in zip(centers, axes)]
        weights = [0.75, -0.2]
        compiled = compile_torus_sum(polynomials, weights)
        points = np.array([[2, 0.3, 0.1], [5.8, 0, 0], [-1, -2, 0.4]])
        expected = []
        for p in points:
            total = 0.0
            for w, c, a in zip(weights, centers, axes):
                q = p - c
                q2 = q @ q
                transverse = q2 - (q @ a)**2
                total += w * ((q2 + 25 - 0.64)**2 - 100 * transverse)
            expected.append(total)
        np.testing.assert_allclose(polynomial_design(points) @ compiled, expected, atol=1e-10)
        self.assertTrue(all(sum(e) <= 4 for p in polynomials for e in p))

    def test_compiled_ray_radial_decimal_roots(self):
        coefficients = compile_torus_sum([torus_polynomial((0, 0, 0), (0, 1, 0), 5, 0.8)], [1])
        ray = polynomial_ray(coefficients, (1, 0, 0), (1, 0, 0))
        roots = sorted(float(r.real) for r in np.polynomial.polynomial.polyroots(ray)
                       if abs(r.imag) < 1e-8 and r.real > 0)
        with localcontext() as ctx:
            ctx.prec = 60
            first = float(Decimal(5) - Decimal('0.8') - Decimal(1))
            second = float(Decimal(5) + Decimal('0.8') - Decimal(1))
        np.testing.assert_allclose(roots, [first, second], atol=1e-8)

    def test_hybrid_c1_joins_periodic_seam_and_consistent_field(self):
        hybrid = HybridRadius(12, 0.3)
        for patch in hybrid.patches():
            for phi in (patch.lo, patch.hi):
                a0, d0 = hybrid.value_derivative(phi - 1e-9)
                a1, d1 = hybrid.value_derivative(phi + 1e-9)
                self.assertAlmostEqual(float(a0), float(a1), delta=1e-8)
                self.assertAlmostEqual(float(d0), float(d1), delta=1e-7)
                np.testing.assert_allclose(profile_normal(0.4, phi - 1e-9, a0, d0),
                                           profile_normal(0.4, phi + 1e-9, a1, d1), atol=1e-7)
        np.testing.assert_allclose(hybrid.value_derivative(0), hybrid.value_derivative(2 * math.pi), atol=1e-14)
        for phi in np.linspace(0, 2 * math.pi, 21):
            a = float(hybrid.value_derivative(phi)[0])
            p = np.array([(5 + a) * math.cos(phi), (5 + a) * math.sin(phi), 0])
            self.assertAlmostEqual(profile_field(p, hybrid), 0.0, delta=1e-12)
            self.assertLess(profile_field(np.array([5 * math.cos(phi), 5 * math.sin(phi), 0]), hybrid), 0)

    def test_hybrid_bound_and_join_does_not_correct_plateau_error(self):
        for fraction in (0.1, 0.3, 0.6):
            hybrid = HybridRadius(12, fraction)
            phi = np.linspace(0, 2 * math.pi, 2001)
            exact = 0.8 + 0.12 * np.cos(3 * phi)
            error = np.max(np.abs(hybrid.value_derivative(phi)[0] - exact))
            self.assertLessEqual(error, hybrid.positional_error_bound() + 1e-14)
            self.assertGreater(error, 1e-4)

    def test_exact_torus_recovered_by_hybrid_and_spline(self):
        for profile in (HybridRadius(12, 0.3, 0), SplineRadius(12, 0)):
            value, derivative = profile.value_derivative(np.linspace(0, 2 * math.pi, 31))
            np.testing.assert_allclose(value, 0.8, atol=1e-14)
            np.testing.assert_allclose(derivative, 0, atol=1e-14)

    def test_shared_index_finds_spline_candidate_without_certifying_hit(self):
        hybrid = HybridRadius(12, 0.3)
        index = SharedIndex(hybrid.patches())
        phi = hybrid.width / 2  # transition center
        direction = np.array([math.cos(phi), math.sin(phi), 0])
        result = query_diagnostic(hybrid, index, 0.1 * direction, direction)
        a = float(hybrid.value_derivative(phi)[0])
        self.assertAlmostEqual(result['candidate_distance'], 5 - a - 0.1, delta=1e-8)
        self.assertGreater(result['counters']['spline_candidates'], 0)
        self.assertEqual(result['disposition'], 'UNRESOLVED')
        # Bounding misses stay diagnostic, rather than becoming an unreviewed
        # proof of NO_HIT in this experiment.
        miss = query_diagnostic(hybrid, index, np.array([0, 0, 3]), np.array([0, 0, 1]))
        self.assertIsNone(miss['candidate_distance'])
        self.assertEqual(miss['disposition'], 'UNRESOLVED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
