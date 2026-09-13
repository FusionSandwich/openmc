"""Small independent arithmetic controls for the offline exact root oracle."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import unittest

_path = Path(__file__).resolve().parents[2] / "qualification/swept_exact_oracle.py"
_spec = importlib.util.spec_from_file_location("swept_exact_oracle", _path)
oracle = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oracle)


class ExactOracleTests(unittest.TestCase):
    def test_endpoint_and_double_roots(self):
        p = oracle.mul([F(0), F(1)], [F(-1), F(1)])
        p = oracle.mul(p, oracle.mul([F(-1, 3), F(1)], [F(-1, 3), F(1)]))
        roots = oracle.isolate(p)
        self.assertEqual(len(roots), 3)
        for expected, interval in zip([F(0), F(1, 3), F(1)], roots):
            self.assertLessEqual(interval[0], expected)
            self.assertGreaterEqual(interval[1], expected)

    def test_close_distinct_roots(self):
        lo, hi = F(1, 2), F(1, 2)+F(1, 10**20)
        roots = oracle.isolate(oracle.mul([-lo, F(1)], [-hi, F(1)]), bits=100)
        self.assertEqual(len(roots), 2)
        self.assertLess(roots[0][1], roots[1][0])

    def test_irrational_root(self):
        roots = oracle.isolate([F(-1, 2), F(0), F(1)])
        self.assertEqual(len(roots), 1)
        self.assertLessEqual(roots[0][0]**2, F(1, 2))
        self.assertGreaterEqual(roots[0][1]**2, F(1, 2))

    def test_no_real_root(self):
        self.assertEqual(oracle.isolate([F(1), F(0), F(1)]), [])

    def test_degenerate_cylinder_crossing(self):
        coil = [[[F(0), F(1)], [F(0)], [F(0)]]]
        nearest, _, _ = oracle.exact_query(coil, F(1), [F(1, 2), 2, 0], [0, -1, 0])
        self.assertLessEqual(nearest[0], F(1))
        self.assertGreaterEqual(nearest[1], F(1))

    def test_degenerate_cylinder_exact_tangent(self):
        coil = [[[F(0), F(1)], [F(0)], [F(0)]]]
        nearest, roots, _ = oracle.exact_query(coil, F(1), [F(1, 2), 1, -2], [0, 0, 1])
        self.assertLessEqual(nearest[0], F(2))
        self.assertGreaterEqual(nearest[1], F(2))
        self.assertEqual(roots[0][3], "exact_degenerate_tangent")

    def test_generic_endpoint_crossing(self):
        coil = [[[F(0), F(1)], [F(0)], [F(0)]]]
        nearest, _, _ = oracle.exact_query(coil, F(1), [0, 2, 0], [1, -1, 0])
        self.assertLessEqual(nearest[0]**2, F(2))
        self.assertGreaterEqual(nearest[1]**2, F(2))

    def test_parallel_no_boundary_crossing(self):
        coil = [[[F(0), F(1)], [F(0)], [F(0)]]]
        nearest, _, _ = oracle.exact_query(coil, F(1), [2, F(1, 2), 0], [-1, 0, 0])
        self.assertIsNone(nearest)


if __name__ == "__main__":
    unittest.main()
