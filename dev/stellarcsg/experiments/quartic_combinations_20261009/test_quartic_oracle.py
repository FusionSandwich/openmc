from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

from quartic_oracle import isolate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                       'query_combinations_20261009'))
from candidate_scheduler import Box, Query, Resolution, Scheduler


def polynomial(roots):
    p = [F(1)]
    for root in roots:
        q = [F(0)] * (len(p) + 1)
        for i, coefficient in enumerate(p):
            q[i] -= coefficient * root
            q[i + 1] += coefficient
        p = q
    return p


class QuarticControls(unittest.TestCase):
    def assert_roots(self, expected, lower=0, upper=4):
        result = isolate(polynomial(expected), lower, upper)
        distinct = sorted(set(x for x in expected if lower <= x <= upper))
        self.assertEqual(result.disposition, 'COMPLETE')
        self.assertEqual(len(result.roots), len(distinct))
        for root, window in zip(distinct, result.roots):
            self.assertLessEqual(window.lower, root)
            self.assertGreaterEqual(window.upper, root)
        return result

    def test_even_contacts_and_endpoints(self):
        self.assert_roots([F(0), F(1), F(1), F(4)])

    def test_close_roots_and_multiplicity(self):
        self.assert_roots([F(1), F(1) + F(1, 2**48), F(3), F(3)])

    def test_odd_degree_and_outside_roots(self):
        self.assert_roots([F(-2), F(1, 3), F(5)])

    def test_irrational_and_complex_roots(self):
        # (t^2 - 2)(t^2 + 1) has exactly two real roots.
        result = isolate([-2, 0, -1, 0, 1], -2, 2)
        self.assertEqual(result.disposition, 'COMPLETE')
        self.assertEqual(len(result.roots), 2)
        for window in result.roots:
            a, b = window.lower, window.upper
            self.assertLess((a*a - 2) * (b*b - 2), 0)
            self.assertLessEqual(b - a, F(1, 2**32))

    def test_no_real_root(self):
        self.assertEqual(isolate([1, 0, 1], -10, 10).roots, ())
        self.assertEqual(isolate([1], 0, 1).disposition, 'COMPLETE')

    def test_zero_interval(self):
        self.assertEqual(len(isolate([-1, 1], 1, 1).roots), 1)
        self.assertEqual(isolate([-1, 1], 2, 2).roots, ())

    def test_budget_and_zero_polynomial_keep_unknown(self):
        result = isolate([2, -3, 1], 1, 4, budget=0)
        self.assertEqual(result.disposition, 'UNRESOLVED')
        self.assertEqual(result.roots[0].lower, 1)
        self.assertTrue(result.unresolved)
        self.assertEqual(isolate([0, 0], 0, 1).disposition, 'UNRESOLVED')

    def test_invalid_inputs(self):
        for coefficients in ([float('nan')], [float('inf')], [True], [0]*5+[1]):
            with self.assertRaises(ValueError):
                isolate(coefficients, 0, 1)
        for kwargs in ({'lower': 2, 'upper': 1}, {'width': 0}, {'budget': True},
                       {'budget': -1}, {'upper': float('inf')}):
            arguments = dict(lower=0, upper=1)
            arguments.update(kwargs)
            with self.assertRaises(ValueError):
                isolate([1, 1], **arguments)

    def test_generated_rational_bank(self):
        # Independently known factorizations, including repeated contacts.
        import random
        rng = random.Random(8031)
        for _ in range(160):
            roots = [F(rng.randrange(-24, 41), 8)
                     for _ in range(rng.randrange(1, 5))]
            self.assert_roots(roots)

    def test_scheduler_combines_closed_ceiling_cache_and_grazing(self):
        boxes = [Box('tangent', (1, -1, -1), (1, 1, 1)),
                 Box('tie', (1, -1, -1), (1, 1, 1)),
                 Box('later', (2, -1, -1), (4, 1, 1))]
        scheduler = Scheduler(boxes, cache_entries=2)
        polynomials = {'tangent': [1, -2, 1], 'tie': [-1, 1],
                       'later': [-3, 1]}

        def solve(candidate):
            result = isolate(polynomials[candidate.identity],
                             candidate.entry, candidate.exit)
            if result.disposition != 'COMPLETE':
                return Resolution('UNRESOLVED')
            if not result.roots:
                return Resolution('NO_HIT')
            first = result.roots[0]
            if first.lower != first.upper:
                return Resolution('UNRESOLVED')
            return Resolution('HIT', first.lower, candidate.identity)

        query = Query((0, 0, 0), (1, 0, 0), ceiling=1)
        for _ in range(2):
            resolution, contacts, work = scheduler.resolve(query, solve)
            self.assertEqual(resolution.disposition, 'HIT')
            self.assertEqual(resolution.parameter, 1)
            self.assertEqual(set(contacts), {'tangent', 'tie'})
        self.assertTrue(work['cache_hit'])


if __name__ == '__main__':
    unittest.main()
