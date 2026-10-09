"""Finite adversarial tests using independent trimmed-plane root witnesses."""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import random
import unittest

from candidate_scheduler import Box, Candidate, Query, Resolution, Scheduler


def plane_box(identity, x, y0=-1, y1=1):
    return Box(identity, (x, y0, -1), (x, y1, 1))


def plane_oracle(boxes, query):
    """Direct plane equation and finite face membership, without a slab test."""
    hits = []
    for box in boxes:
        if query.direction[0] == 0:
            continue
        root = (box.lower[0] - query.origin[0]) / query.direction[0]
        point = tuple(query.origin[i] + root * query.direction[i] for i in range(3))
        if root >= 0 and (query.ceiling is None or root <= query.ceiling):
            if box.lower[1] <= point[1] <= box.upper[1] and box.lower[2] <= point[2] <= box.upper[2]:
                hits.append((root, box.identity))
    if not hits:
        return Resolution('NO_HIT' if query.ceiling is None else 'NO_HIT_BEFORE_CEILING'), ()
    first = min(root for root, _ in hits)
    return Resolution('HIT', first), tuple(sorted(identity for root, identity in hits if root == first))


def exact_plane_solver(boxes, query):
    by_identity = {box.identity: box for box in boxes}

    def solve(candidate):
        box = by_identity[candidate.identity]
        if query.direction[0] == 0:
            return Resolution('UNRESOLVED')
        root = (box.lower[0] - query.origin[0]) / query.direction[0]
        point = tuple(query.origin[i] + root * query.direction[i] for i in range(3))
        in_face = box.lower[1] <= point[1] <= box.upper[1] and box.lower[2] <= point[2] <= box.upper[2]
        if candidate.entry <= root <= candidate.exit and in_face:
            return Resolution('HIT', root)
        return Resolution('NO_HIT')
    return solve


class CompositionTests(unittest.TestCase):
    def test_independent_trimmed_plane_bank(self):
        rng = random.Random(20261009)
        for _ in range(120):
            boxes = [plane_box(str(i), F(rng.randint(-15, 15), 7), F(rng.randint(-6, 0), 3), F(rng.randint(0, 6), 3)) for i in range(12)]
            query = Query((F(rng.randint(-10, 10), 7), F(rng.randint(-4, 4), 3), 0),
                          (rng.choice((-1, 1)), F(rng.randint(-2, 2), 3), 0),
                          rng.choice((None, F(0), F(1), F(5))))
            expected, contacts = plane_oracle(boxes, query)
            for hierarchy in (False, True):
                actual, actual_contacts, _ = Scheduler(boxes).resolve(query, exact_plane_solver(boxes, query), hierarchy)
                self.assertEqual((actual, actual_contacts), (expected, contacts))

    def test_tiny_positive_gap_retained(self):
        eps = F(1, 2**1074)
        boxes = [plane_box('left', 0), plane_box('right', eps)]
        candidates, _ = Scheduler(boxes).plan(Query((-eps, 0, 0), (1, 0, 0)))
        self.assertEqual([item.entry for item in candidates], [eps, 2 * eps])

    def test_ceiling_tie_keeps_contact(self):
        boxes = [plane_box('touch', 2)]
        query = Query((0, 0, 0), (1, 0, 0), 2)
        result, _, _ = Scheduler(boxes).resolve(query, exact_plane_solver(boxes, query))
        self.assertEqual(result, Resolution('HIT', F(2)))

    def test_corner_touch_is_retained(self):
        box = Box('corner', (1, 1, 1), (2, 2, 2))
        candidates, _ = Scheduler([box]).plan(Query((0, 0, 0), (1, 1, 1), 1))
        self.assertEqual(candidates, (Candidate('corner', F(1), F(1)),))

    def test_parallel_on_face_retained(self):
        candidates, _ = Scheduler([Box('flat', (0, 0, 0), (0, 2, 2))]).plan(Query((0, -1, 1), (0, 1, 0)))
        self.assertEqual(candidates[0].entry, 1)

    def test_parallel_outside_face_excluded(self):
        candidates, _ = Scheduler([plane_box('flat', 1)]).plan(Query((0, 0, 0), (0, 1, 0)))
        self.assertEqual(candidates, ())

    def test_negative_direction(self):
        boxes = [plane_box('near', 2), plane_box('far', -1)]
        query = Query((3, 0, 0), (-1, 0, 0))
        actual, _, _ = Scheduler(boxes).resolve(query, exact_plane_solver(boxes, query))
        self.assertEqual(actual.parameter, 1)

    def test_first_box_entry_is_not_first_root(self):
        boxes = [Box('broad', (0, -1, -1), (20, 1, 1)), Box('near', (1, -1, -1), (3, 1, 1))]
        def solve(candidate):
            root = F(10) if candidate.identity == 'broad' else F(2)
            return Resolution('HIT', root) if candidate.entry <= root <= candidate.exit else Resolution('NO_HIT')
        result, _, _ = Scheduler(boxes).resolve(Query((0, 0, 0), (1, 0, 0)), solve)
        self.assertEqual(result.parameter, 2)

    def test_earlier_unknown_blocks_later_hit(self):
        boxes = [plane_box('unknown', 1), plane_box('hit', 2)]
        result, _, _ = Scheduler(boxes).resolve(Query((0, 0, 0), (1, 0, 0)),
            lambda c: Resolution('UNRESOLVED') if c.identity == 'unknown' else Resolution('HIT', 2))
        self.assertEqual(result.disposition, 'UNRESOLVED')

    def test_later_unknown_can_be_pruned(self):
        boxes = [plane_box('hit', 1), plane_box('unknown', 2)]
        result, _, work = Scheduler(boxes).resolve(Query((0, 0, 0), (1, 0, 0)),
            lambda c: Resolution('HIT', 1) if c.identity == 'hit' else Resolution('UNRESOLVED'))
        self.assertEqual(result.disposition, 'HIT')
        self.assertEqual(work['solver_calls'], 1)

    def test_equal_contacts_preserved(self):
        boxes = [plane_box('a', 1), plane_box('b', 1)]
        query = Query((0, 0, 0), (1, 0, 0))
        result, contacts, _ = Scheduler(boxes).resolve(query, exact_plane_solver(boxes, query))
        self.assertEqual((result.parameter, contacts), (1, ('a', 'b')))

    def test_equal_unknown_blocks_ownership_claim(self):
        boxes = [plane_box('a', 1), plane_box('b', 1)]
        result, _, _ = Scheduler(boxes).resolve(Query((0, 0, 0), (1, 0, 0)),
            lambda c: Resolution('HIT', 1) if c.identity == 'a' else Resolution('UNRESOLVED'))
        self.assertEqual(result.disposition, 'UNRESOLVED')

    def test_collision_limited_miss_is_not_global_miss(self):
        boxes = [plane_box('later', 4)]
        limited = Query((0, 0, 0), (1, 0, 0), 2)
        result, _, _ = Scheduler(boxes).resolve(limited, exact_plane_solver(boxes, limited))
        self.assertEqual(result.disposition, 'NO_HIT_BEFORE_CEILING')

    def test_cache_keys_every_query_field(self):
        scheduler = Scheduler([plane_box('a', 1)], cache_entries=3)
        base = Query((0, 0, 0), (1, 0, 0), 2)
        scheduler.plan(base)
        self.assertTrue(scheduler.plan(base)[1]['cache_hit'])
        for changed in (Query((1, 0, 0), (1, 0, 0), 2), Query((0, 0, 0), (-1, 0, 0), 2),
                        Query((0, 0, 0), (1, 0, 0), 0), Query((0, 0, 0), (1, 0, 0), 2, True)):
            self.assertFalse(scheduler.plan(changed)[1]['cache_hit'])

    def test_cache_eviction_is_bounded(self):
        scheduler = Scheduler([], cache_entries=1)
        first, second = Query((0, 0, 0), (1, 0, 0)), Query((1, 0, 0), (1, 0, 0))
        scheduler.plan(first)
        scheduler.plan(second)
        self.assertFalse(scheduler.plan(first)[1]['cache_hit'])

    def test_new_geometry_has_new_identity(self):
        self.assertNotEqual(Scheduler([plane_box('a', 1)]).geometry_digest, Scheduler([plane_box('a', 2)]).geometry_digest)

    def test_malformed_queries_rejected(self):
        for direction in ((0, 0, 0), (float('nan'), 0, 0), (float('inf'), 0, 0), (True, 0, 0)):
            with self.assertRaises(ValueError):
                Query((0, 0, 0), direction)
        with self.assertRaises(ValueError):
            Query((0, 0, 0), (1, 0, 0), -1)

    def test_bad_boxes_rejected(self):
        with self.assertRaises(ValueError):
            Box('a', (2, 0, 0), (1, 1, 1))
        with self.assertRaises(ValueError):
            Scheduler([plane_box('a', 1), plane_box('a', 2)])

    def test_corrupted_solver_results_rejected(self):
        scheduler = Scheduler([plane_box('a', 1)])
        query = Query((0, 0, 0), (1, 0, 0))
        for corruption in (Resolution('HIT', 2), Resolution('NO_HIT', 1),
                           Resolution('HIT', 1, 'wrong'), Resolution('UNKNOWN')):
            with self.assertRaises(ValueError):
                scheduler.resolve(query, lambda candidate: corruption)

    def test_solver_exceptions_remain_visible(self):
        def fail(candidate):
            raise RuntimeError('solver failure')
        with self.assertRaises(RuntimeError):
            Scheduler([plane_box('a', 1)]).resolve(Query((0, 0, 0), (1, 0, 0)), fail)


def ablation():
    boxes = [plane_box('near', 2)] + [plane_box('far' + str(i), 20 + i, 100 + i, 101 + i) for i in range(128)]
    records = []
    for hierarchy in (False, True):
        for ceiling in (None, 1, 3):
            for capacity in (0, 4):
                scheduler = Scheduler(boxes, capacity)
                query = Query((0, 0, 0), (1, 0, 0), ceiling)
                actual, contacts, work = scheduler.resolve(query, exact_plane_solver(boxes, query), hierarchy)
                expected, expected_contacts = plane_oracle(boxes, query)
                if (actual, contacts) != (expected, expected_contacts):
                    raise AssertionError('Ablation changed root semantics')
                repeated = scheduler.plan(query, hierarchy)[1]
                records.append({'hierarchy': hierarchy, 'ceiling': ceiling, 'cache_entries': capacity,
                                'disposition': actual.disposition, 'work': work, 'repeat_plan': repeated})
    return records


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CompositionTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    root = Path(__file__).resolve().parent
    receipt = {'status': 'FINITE_REFERENCE_TESTS_PASS' if result.wasSuccessful() else 'FAIL',
               'tests': result.testsRun, 'independent_plane_bank_queries': 120,
               'ablation': ablation() if result.wasSuccessful() else [],
               'scope': 'Exact candidate composition reference only; no native geometry, physics or speed acceptance',
               'source_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                 for name in ('candidate_scheduler.py', 'test_candidate_scheduler.py')}}
    (root / 'results.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
