import unittest

import numpy as np

from direct_algebraic import (
    DirectFourier,
    IncumbentBicubic,
    LocalQuartic,
    field_jet,
    normal,
    poly_gradient,
    position,
    query_candidates,
)
from patch_methods import MONOMIALS, polynomial_design


class DirectAlgebraicControls(unittest.TestCase):
    def test_stored_modes_and_sine(self):
        f = DirectFourier()
        t, p = 0.31, 0.24
        r, rt, rp = f.radius(t, p)
        self.assertAlmostEqual(
            r, 0.8 + 0.12 * np.cos(2 * t - 3 * p) + 0.025 * np.sin(t + 6 * p)
        )
        self.assertAlmostEqual(
            rt, -0.24 * np.sin(2 * t - 3 * p) + 0.025 * np.cos(t + 6 * p)
        )
        self.assertAlmostEqual(
            rp, 0.36 * np.sin(2 * t - 3 * p) + 0.15 * np.cos(t + 6 * p)
        )
        self.assertGreater(0.8 - 0.12 - 0.025, 0)

    def test_gradient_and_outward_normal(self):
        f = DirectFourier()
        x = position(f, 0.37, 0.28)
        value, grad = field_jet(f, x)
        self.assertLess(abs(value), 1e-14)
        h = 1e-6
        fd = np.array(
            [
                (
                    field_jet(f, x + h * np.eye(3)[i])[0]
                    - field_jet(f, x - h * np.eye(3)[i])[0]
                )
                / (2 * h)
                for i in range(3)
            ]
        )
        np.testing.assert_allclose(grad, fd, atol=1e-9)
        n = normal(f, x)
        self.assertGreater(field_jet(f, x + 1e-4 * n)[0], 0)
        self.assertLess(field_jet(f, x - 1e-4 * n)[0], 0)

    def test_incumbent_knots_and_periodicity(self):
        f = DirectFourier()
        s = IncumbentBicubic(f, 16, 24)
        t, p = np.meshgrid(
            2 * np.pi * np.arange(16) / 16,
            2 * np.pi * np.arange(24) / 72,
            indexing="ij",
        )
        np.testing.assert_allclose(s.radius(t, p)[0], f.radius(t, p)[0], atol=1e-14)
        for a, b in zip(
            s.radius(0.3, 0.2), s.radius(0.3 + 2 * np.pi, 0.2 + 2 * np.pi / 3)
        ):
            self.assertAlmostEqual(float(a), float(b), places=13)

    def test_radial_first_candidate(self):
        f = DirectFourier()
        t, p = 0.4, 0.2
        axis = np.array([5 * np.cos(p), 5 * np.sin(p), 0.0])
        u = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), np.sin(t)])
        result = query_candidates(f, axis + 2 * u, -u, ceiling=1.9)
        self.assertEqual(result["disposition"], "UNRESOLVED")
        self.assertAlmostEqual(
            result["candidate_distance_m"], 2 - f.radius(t, p)[0], places=10
        )

    def test_even_tangent_stationary_candidate(self):
        f = DirectFourier(circular=True)
        t, p = 0.3, 0.2
        tangent = np.array([-np.sin(t) * np.cos(p), -np.sin(t) * np.sin(p), np.cos(t)])
        origin = position(f, t, p) - 1.234 * tangent
        result = query_candidates(f, origin, tangent, ceiling=2, samples=33)
        self.assertEqual(result["disposition"], "UNRESOLVED")
        self.assertTrue(any(abs(x - 1.234) < 1e-7 for x in result["candidates_m"]))

    def test_unknown_miss_and_singularity(self):
        f = DirectFourier()
        result = query_candidates(f, [10.0, 0.0, 3.0], [0.0, 0.0, 1.0], ceiling=2)
        self.assertEqual(result["disposition"], "UNRESOLVED")
        self.assertIsNone(result["candidate_distance_m"])
        result = query_candidates(f, [5.0, 0.0, 0.0], [0.0, 0.0, 1.0], ceiling=2)
        self.assertEqual(result["disposition"], "UNRESOLVED")
        self.assertIsNotNone(result["unsupported"])

    def test_later_singularity_retains_earlier_candidate(self):
        result = query_candidates(
            DirectFourier(),
            [-3.0094878834899514, -0.21100891237204633, -0.2592682852393893],
            [-0.989133558888223, -0.06935266215780803, 0.12963414261969464],
        )
        self.assertEqual(result["disposition"], "UNRESOLVED")
        self.assertAlmostEqual(
            result["candidate_distance_m"], 1.3329172119706623, places=10
        )
        self.assertIsNotNone(result["unsupported"])
        self.assertTrue(result["unsupported_intervals"])

    def test_full_quartic_ray_and_gradient(self):
        rng = np.random.default_rng(52)
        c = rng.normal(size=35)
        self.assertEqual(len(MONOMIALS), 35)
        patch = LocalQuartic(
            np.array([1.0, 2.0, 3.0]), np.eye(3), 0.7, c, 35, 1.0, 0, 0, 1, 1
        )
        o = np.array([1.2, 1.9, 3.1])
        d = np.array([0.2, 0.3, 0.4])
        coefficients = patch.ray_polynomial(o, d)
        self.assertEqual(len(coefficients), 5)
        for t in [0.0, 0.1, 0.7]:
            q = (o + t * d - patch.center) / patch.scale
            self.assertAlmostEqual(
                (polynomial_design(q[None, :]) @ c).item(),
                np.polynomial.polynomial.polyval(t, coefficients),
                places=12,
            )
        q = np.array([0.3, 0.2, -0.1])
        h = 1e-6
        fd = np.array(
            [
                (
                    (
                        polynomial_design((q + h * np.eye(3)[i])[None, :])
                        - polynomial_design((q - h * np.eye(3)[i])[None, :])
                    )
                    @ c
                ).item()
                / (2 * h)
                for i in range(3)
            ]
        )
        np.testing.assert_allclose(poly_gradient(c, q)[0], fd, atol=1e-9)

    def test_local_fit_nonzero_offset_and_trim(self):
        f = DirectFourier()
        patch = LocalQuartic.fit(f, 0.5, 0.2, 0.15, 0.08)
        self.assertGreater(np.linalg.norm(patch.coefficients), 0.1)
        for offset in [-0.02, 0.02]:
            n = normal(f, patch.center)
            val = (
                polynomial_design(
                    (
                        (patch.center + offset * patch.scale * n - patch.center)
                        @ patch.frame
                        / patch.scale
                    )[None, :]
                )
                @ patch.coefficients
            ).item()
            self.assertGreater(val * offset, 0)
        n = normal(f, patch.center)
        o = patch.center + 0.05 * n
        roots = patch.trimmed_ray_candidates(o, -n, ceiling=0.1)
        self.assertEqual(roots["disposition"], "UNRESOLVED")
        self.assertTrue(roots["candidates_m"])
        outside = position(f, patch.theta + 1.0, patch.phi)
        roots = patch.trimmed_ray_candidates(
            outside + 0.05 * normal(f, outside), -normal(f, outside), ceiling=0.1
        )
        self.assertEqual(roots["candidates_m"], [])


if __name__ == "__main__":
    unittest.main()
