"""Independent bounded exact-factor and scheduler challenges; no source writes."""
from fractions import Fraction as F
from pathlib import Path
import json
import random
import sys

from quartic_oracle import isolate, square_free, sturm, variations

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'query_combinations_20261009'))
from candidate_scheduler import Box, Query, Resolution, Scheduler


def multiply(left, right):
    result = [F(0)] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            result[i + j] += a * b
    return result


def factors(roots, scale=F(1)):
    result = [scale]
    for root in roots:
        result = multiply(result, [-root, F(1)])
    return result


def check_known(roots, a, b, width=F(1, 2**20), budget=1024, scale=F(1)):
    p = factors(roots, scale)
    result = isolate(p, a, b, width, budget)
    known = sorted({x for x in roots if a <= x <= b})
    assert result.subdivisions <= budget
    assert result.disposition == ('UNRESOLVED' if result.unresolved else 'COMPLETE')
    assert all(a <= w.lower <= w.upper <= b for w in result.roots + result.unresolved)
    covered = []
    for window in result.roots:
        hits = [x for x in known if window.lower <= x <= window.upper]
        assert len(hits) == 1, (roots, a, b, window, hits)
        covered += hits
        assert window.lower == window.upper or window.upper - window.lower <= width
    assert len(set(covered)) == len(covered), ('duplicate root', roots, result)
    assert all(x in covered or any(w.lower <= x <= w.upper for w in result.unresolved) for x in known)
    if result.disposition == 'COMPLETE':
        assert covered == known, (roots, a, b, result)
    # Factorization gives the exact independent open-interval root count.
    sequence = sturm(square_free(tuple(p)))
    cuts = sorted(set([a, b, F(0)] + roots + [(a+b)/2]))
    counts = 0
    for left, right in zip(cuts, cuts[1:]):
        actual = variations(sequence, left, 1) - variations(sequence, right, -1)
        expected = len({x for x in roots if left < x < right})
        assert actual == expected, ('one-sided count', roots, left, right, actual, expected)
        counts += 1
    return result, counts


def adapter(coefficients, budget=1024):
    def solve(candidate):
        isolated = isolate(coefficients[candidate.identity], candidate.entry, candidate.exit, budget=budget)
        if isolated.disposition != 'COMPLETE':
            return Resolution('UNRESOLVED')
        if not isolated.roots:
            return Resolution('NO_HIT')
        first = isolated.roots[0]
        if first.lower != first.upper:
            return Resolution('UNRESOLVED')
        return Resolution('HIT', first.lower, candidate.identity)
    return solve


def main():
    rng = random.Random(903191)
    bank_cases = 0
    count_checks = 0
    for _ in range(360):
        roots = [F(rng.randint(-30, 30), rng.choice([3, 7, 11, 17])) for _ in range(rng.randint(1, 4))]
        if len(roots) >= 2 and rng.randrange(3) == 0:
            roots[-1] = roots[0]
        ends = sorted(rng.sample(roots + [F(-3), F(0), F(3)], 2))
        result, count = check_known(roots, *ends, scale=rng.choice([F(-13, 7), F(1), F(27, 11)]))
        assert result.disposition == 'COMPLETE'
        bank_cases += 1
        count_checks += count

    for exponent in [48, 80, 200]:
        roots = [F(1, 3), F(1, 3) + F(1, 2**exponent), F(1, 3) + F(2, 2**exponent), F(2)]
        result, count = check_known(roots, F(0), F(3), width=F(1, 2**24))
        assert result.disposition == 'COMPLETE'
        bank_cases += 1
        count_checks += count
    for multiplicity in range(1, 5):
        for a, b in [(F(1), F(1)), (F(1), F(2)), (F(0), F(1)), (F(0), F(2))]:
            _, count = check_known([F(1)] * multiplicity, a, b, budget=0, width=F(1, 2**20))
            bank_cases += 1
            count_checks += count
    for budget in [0, 1, 2, 5, 10, 32]:
        _, count = check_known([F(1, 3), F(2, 3), F(5, 3), F(2)], F(0), F(3), budget=budget)
        bank_cases += 1
        count_checks += count
    tiny = F(1, 2**1074)
    result, count = check_known([F(1), F(1) + tiny], F(0), F(2), budget=64)
    assert result.disposition == 'UNRESOLVED'
    bank_cases += 1
    count_checks += count

    # Even irrational roots survive square-free reduction despite no sign change
    # in the original squared polynomial. Verify brackets against unsquared factors.
    repeated = isolate([4, 0, -4, 0, 1], -2, 2)
    assert repeated.disposition == 'COMPLETE' and len(repeated.roots) == 2
    for w in repeated.roots:
        assert w.lower != w.upper and (w.lower*w.lower-2)*(w.upper*w.upper-2) < 0
    four = isolate([6, 0, -5, 0, 1], -2, 2)
    assert four.disposition == 'COMPLETE' and len(four.roots) == 4
    for w, square in zip(four.roots, [3, 2, 2, 3]):
        assert (w.lower*w.lower-square)*(w.upper*w.upper-square) < 0
    assert isolate([1, 0, 2, 0, 1], -10, 10).roots == ()
    assert isolate([0], 0, 0, budget=0).disposition == 'UNRESOLVED'
    coarse = isolate([-2, 0, 1], 0, 2, width=2, budget=0)
    assert coarse.disposition == 'COMPLETE' and coarse.roots[0].lower != coarse.roots[0].upper

    # The exact represented float is retained, including at a closed endpoint.
    binary = F(0.1)
    assert isolate([-0.1, 1.0], binary, binary).roots[0].lower == binary
    assert isolate([-0.1, 1.0], F(1, 10), F(1, 10)).roots == ()

    composition_checks = 0
    for hierarchy in [False, True]:
        for cache_entries in [0, 2]:
            scheduler = Scheduler([Box('irrational', (0,-1,-1),(2,1,1)), Box('known', (2,-1,-1),(2,1,1))], cache_entries)
            query = Query((0,0,0),(1,0,0),2)
            for _ in range(2):
                answer, contacts, work = scheduler.resolve(query, adapter({'irrational':[-2,0,1], 'known':[-2,1]}), hierarchy)
                assert answer.disposition == 'UNRESOLVED' and answer.parameter is None
                composition_checks += 1
            # Equal unknown zero polynomial cannot certify the contact group.
            equal = Scheduler([Box('known',(1,-1,-1),(1,1,1)), Box('zero',(1,-1,-1),(1,1,1))],cache_entries)
            answer,_,_=equal.resolve(query,adapter({'known':[-1,1],'zero':[0]}),hierarchy)
            assert answer.disposition == 'UNRESOLVED'
            composition_checks += 1
            # Partial isolation includes a known upper endpoint but unknown earlier root.
            partial = Scheduler([Box('partial',(0,-1,-1),(3,1,1)),Box('known',(2,-1,-1),(2,1,1))],cache_entries)
            answer,_,_=partial.resolve(Query((0,0,0),(1,0,0),3),adapter({'partial':factors([F(1,3),F(3)]),'known':[-2,1]},budget=0),hierarchy)
            assert answer.disposition == 'UNRESOLVED'
            composition_checks += 1
            # Closed ceiling excludes all later irrational roots using exact root count.
            answer,contacts,_=scheduler.resolve(Query((0,0,0),(1,0,0),1),adapter({'irrational':[-2,0,1],'known':[-2,1]}),hierarchy)
            assert answer.disposition == 'NO_HIT_BEFORE_CEILING' and contacts == ()
            composition_checks += 1
    print(json.dumps({'status':'PASS','known_factor_cases':bank_cases,'one_sided_count_checks':count_checks,'irrational_repeated_four_root_no_real_cases':3,'composition_checks':composition_checks,'represented_binary_endpoint':'PASS','coarse_isolation_not_scalar_hit':'PASS','budget_unknowns':'PASS'}))


if __name__ == '__main__':
    main()
