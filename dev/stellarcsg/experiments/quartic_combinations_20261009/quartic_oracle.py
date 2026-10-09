"""Exact finite-interval oracle for a represented rational polynomial.

Coefficients are ascending, degree at most four. Finite float inputs mean
their exact binary values, not uncertain physical coefficients. Square-free
Sturm counts retain even contacts. This reference certifies distinct polynomial
roots only: neither VMEC fidelity, trim ownership, nor physical boundary events.
"""
from dataclasses import dataclass
from fractions import Fraction
import math


def rational(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError('Expected finite rational-compatible scalar')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Expected finite scalar')
    return Fraction(value)


def trim(p):
    p = tuple(p)
    while p and p[-1] == 0:
        p = p[:-1]
    return p


def evaluate(p, x):
    value = Fraction(0)
    for coefficient in reversed(p):
        value = value * x + coefficient
    return value


def derivative(p):
    return trim(tuple(i * p[i] for i in range(1, len(p))))


def divide(p, q):
    if not q:
        raise ZeroDivisionError('Zero polynomial')
    remainder = list(p)
    quotient = [Fraction(0)] * max(0, len(p) - len(q) + 1)
    while remainder and len(remainder) >= len(q):
        k = len(remainder) - len(q)
        factor = remainder[-1] / q[-1]
        quotient[k] = factor
        for i, coefficient in enumerate(q):
            remainder[i + k] -= factor * coefficient
        remainder = list(trim(remainder))
    return trim(quotient), trim(remainder)


def square_free(p):
    a, b = p, derivative(p)
    while b:
        a, b = b, divide(a, b)[1]
    gcd = tuple(c / a[-1] for c in a)
    return divide(p, gcd)[0]


def sturm(p):
    sequence = [p, derivative(p)]
    while sequence[-1]:
        remainder = divide(sequence[-2], sequence[-1])[1]
        if not remainder:
            break
        sequence.append(tuple(-c for c in remainder))
    return tuple(q for q in sequence if q)


def side_sign(p, x, side):
    """Sign immediately to either side, including at a sequence zero."""
    order = 0
    while p:
        value = evaluate(p, x)
        if value:
            return (1 if value > 0 else -1) * (side ** order)
        p = derivative(p)
        order += 1
    return 0


def variations(sequence, x, side):
    signs = [side_sign(p, x, side) for p in sequence]
    signs = [s for s in signs if s]
    return sum(a != b for a, b in zip(signs, signs[1:]))


@dataclass(frozen=True)
class RootInterval:
    lower: Fraction
    upper: Fraction


@dataclass(frozen=True)
class Isolation:
    disposition: str
    roots: tuple
    unresolved: tuple
    subdivisions: int
    reason: str = ''


def isolate(coefficients, lower, upper, width=Fraction(1, 2**32), budget=1024):
    """Isolate all distinct roots on [lower, upper], or retain unknown windows.

    COMPLETE means every distinct root is represented exactly once by a point
    or a closed interval containing one root. Multiplicities are not returned.
    Budget exhaustion never establishes a miss or a complete first event.
    """
    p = trim(tuple(rational(c) for c in coefficients))
    lower, upper, width = map(rational, (lower, upper, width))
    if lower > upper or width <= 0:
        raise ValueError('Reversed interval or nonpositive width')
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError('Expected nonnegative integer subdivision budget')
    if len(p) > 5:
        raise ValueError('Degree exceeds four')
    if not p:
        return Isolation('UNRESOLVED', (), (RootInterval(lower, upper),), 0,
                         'Identically zero polynomial')
    if len(p) == 1:
        return Isolation('COMPLETE', (), (), 0)
    p = square_free(p)
    sequence = sturm(p)
    roots = [RootInterval(x, x) for x in sorted({lower, upper})
             if evaluate(p, x) == 0]
    pending = [(lower, upper)] if lower < upper else []
    unresolved = []
    subdivisions = 0
    while pending:
        a, b = pending.pop()
        count = variations(sequence, a, 1) - variations(sequence, b, -1)
        if count == 0:
            continue
        if count == 1 and b - a <= width and evaluate(p, a) and evaluate(p, b):
            roots.append(RootInterval(a, b))
            continue
        if subdivisions == budget:
            unresolved.append(RootInterval(a, b))
            continue
        midpoint = (a + b) / 2
        subdivisions += 1
        if evaluate(p, midpoint) == 0:
            roots.append(RootInterval(midpoint, midpoint))
        pending.extend([(midpoint, b), (a, midpoint)])
    return Isolation('UNRESOLVED' if unresolved else 'COMPLETE',
                     tuple(sorted(roots, key=lambda r: r.lower)),
                     tuple(sorted(unresolved, key=lambda r: r.lower)),
                     subdivisions, 'Subdivision budget' if unresolved else '')
