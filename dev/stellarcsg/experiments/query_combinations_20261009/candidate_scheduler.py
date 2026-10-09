"""Exact reference for composing BVH exclusion, ceilings and query reuse.

This is an experimental planner, not an OpenMC surface solver. Bounds must
enclose every admitted root-producing domain. Fraction arithmetic avoids
floating-point slab false negatives in the composition reference. Parameters
are physical lengths only when direction is unit length. No speed claim.
"""
from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import heapq
import math


def rational(value):
    """Treat finite binary floating-point inputs as their exact values."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError('Expected a finite real scalar')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Expected a finite real scalar')
    return Fraction(value)


def vector(values):
    result = tuple(rational(value) for value in values)
    if len(result) != 3:
        raise ValueError('Expected three coordinates')
    return result


@dataclass(frozen=True)
class Box:
    identity: str
    lower: tuple
    upper: tuple

    def __post_init__(self):
        if not isinstance(self.identity, str) or not self.identity:
            raise ValueError('A nonempty string identity is required')
        object.__setattr__(self, 'lower', vector(self.lower))
        object.__setattr__(self, 'upper', vector(self.upper))
        if any(a > b for a, b in zip(self.lower, self.upper)):
            raise ValueError('Reversed bound')


@dataclass(frozen=True)
class Query:
    origin: tuple
    direction: tuple
    ceiling: object = None
    coincident: bool = False

    def __post_init__(self):
        object.__setattr__(self, 'origin', vector(self.origin))
        object.__setattr__(self, 'direction', vector(self.direction))
        if not any(self.direction):
            raise ValueError('Zero direction')
        if not isinstance(self.coincident, bool):
            raise ValueError('Coincidence state must be Boolean')
        if self.ceiling is not None:
            object.__setattr__(self, 'ceiling', rational(self.ceiling))
            if self.ceiling < 0:
                raise ValueError('Negative ceiling')


@dataclass(frozen=True)
class Candidate:
    identity: str
    entry: Fraction
    exit: Fraction


@dataclass(frozen=True)
class Resolution:
    disposition: str
    parameter: object = None
    identity: str = None


@dataclass(frozen=True)
class Node:
    lower: tuple
    upper: tuple
    children: tuple = ()
    box: object = None


def interval(lower, upper, query):
    """Intersect a closed box with the closed ray segment, keeping ties."""
    entry, exit = Fraction(0), query.ceiling
    for lo, hi, position, direction in zip(lower, upper, query.origin, query.direction):
        if direction == 0:
            if not lo <= position <= hi:
                return None
            continue
        near, far = sorted(((lo - position) / direction, (hi - position) / direction))
        entry = max(entry, near)
        exit = far if exit is None else min(exit, far)
        if entry > exit:
            return None
    return entry, exit


def build_tree(boxes):
    lower = tuple(min(box.lower[i] for box in boxes) for i in range(3))
    upper = tuple(max(box.upper[i] for box in boxes) for i in range(3))
    if len(boxes) == 1:
        return Node(lower, upper, box=boxes[0])
    axis = max(range(3), key=lambda i: upper[i] - lower[i])
    ordered = sorted(boxes, key=lambda box: (box.lower[axis] + box.upper[axis], box.identity))
    middle = len(ordered) // 2
    return Node(lower, upper, children=(build_tree(ordered[:middle]), build_tree(ordered[middle:])))


class Scheduler:
    """Immutable geometry with a bounded, per-instance candidate cache.

    Cache entries contain only candidate intervals, never solver outcomes or
    ownership. Each instance is for one worker; shared-thread use is unsupported.
    A callback must solve its entire supplied interval with no earlier root
    omitted. Unknowns remain unknown; callback exceptions propagate.
    """

    def __init__(self, boxes, cache_entries=0):
        self._boxes = tuple(boxes)
        if not all(isinstance(box, Box) for box in self._boxes):
            raise ValueError('Expected immutable Box records')
        if len({box.identity for box in self._boxes}) != len(self._boxes):
            raise ValueError('Duplicate domain identity')
        if isinstance(cache_entries, bool) or not isinstance(cache_entries, int) or cache_entries < 0:
            raise ValueError('Invalid cache capacity')
        self._tree = build_tree(self._boxes) if self._boxes else None
        self._capacity = cache_entries
        self._cache = OrderedDict()
        self.geometry_digest = hashlib.sha256(repr(self._boxes).encode()).hexdigest()

    def plan(self, query, hierarchy=True):
        if not isinstance(query, Query) or not isinstance(hierarchy, bool):
            raise ValueError('Invalid query or mode')
        key = (self.geometry_digest, query, hierarchy)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key], {'cache_hit': True, 'box_tests': 0}
        candidates, tests = [], 0
        if hierarchy and self._tree:
            queue, serial = [], 0

            def enqueue(node):
                nonlocal tests, serial
                tests += 1
                bounds = interval(node.lower, node.upper, query)
                if bounds is not None:
                    serial += 1
                    heapq.heappush(queue, (bounds[0], serial, node, bounds))

            enqueue(self._tree)
            while queue:
                _, _, node, bounds = heapq.heappop(queue)
                if node.box is not None:
                    candidates.append(Candidate(node.box.identity, *bounds))
                else:
                    for child in node.children:
                        enqueue(child)
        else:
            for box in self._boxes:
                tests += 1
                bounds = interval(box.lower, box.upper, query)
                if bounds is not None:
                    candidates.append(Candidate(box.identity, *bounds))
        result = tuple(sorted(candidates, key=lambda candidate: (candidate.entry, candidate.identity)))
        if self._capacity:
            self._cache[key] = result
            if len(self._cache) > self._capacity:
                self._cache.popitem(last=False)
        return result, {'cache_hit': False, 'box_tests': tests}

    def resolve(self, query, solve, hierarchy=True):
        """Compose domain results without losing earlier unresolved intervals.

        This API returns a first-root candidate, not native ownership or normals.
        Equal-root domains remain in ``contacts`` for a separate event layer.
        ``NO_HIT_BEFORE_CEILING`` is never a global no-hit certificate.
        """
        candidates, work = self.plan(query, hierarchy)
        best, contacts, uncertain, calls = None, [], [], 0
        for candidate in candidates:
            if best is not None and candidate.entry > best:
                break
            right = candidate.exit if best is None else min(candidate.exit, best)
            clipped = Candidate(candidate.identity, candidate.entry, right)
            result = solve(clipped)
            calls += 1
            if not isinstance(result, Resolution) or result.disposition not in ('HIT', 'NO_HIT', 'UNRESOLVED'):
                raise ValueError('Invalid solver result')
            if result.identity not in (None, candidate.identity):
                raise ValueError('Solver returned wrong domain identity')
            if result.disposition != 'HIT':
                if result.parameter is not None:
                    raise ValueError('Non-hit result carries a root')
                if result.disposition == 'UNRESOLVED':
                    uncertain.append(candidate.entry)
                continue
            root = rational(result.parameter)
            if not clipped.entry <= root <= clipped.exit:
                raise ValueError('Root outside certified candidate interval')
            if best is None or root < best:
                best, contacts = root, [candidate.identity]
            elif root == best:
                contacts.append(candidate.identity)
        work = dict(work, solver_calls=calls, candidate_count=len(candidates))
        if any(best is None or entry <= best for entry in uncertain):
            return Resolution('UNRESOLVED'), tuple(sorted(contacts)), work
        if best is not None:
            return Resolution('HIT', best), tuple(sorted(contacts)), work
        status = 'NO_HIT' if query.ceiling is None else 'NO_HIT_BEFORE_CEILING'
        return Resolution(status), (), work
