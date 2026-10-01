"""Independent solid-angle check of the frozen P00 point/component fixture.

This checks represented facets at fixture points; it is not a CAD or
near-boundary certificate.  Requires the retained local fixture and manifest.
"""

from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "dev/stellarcsg/reports/local-cont-20260925/p00-accepted-facet-fixture.txt"
MANIFEST = ROOT / "dev/stellarcsg/reports/p00-per-case-20261001/candidate-manifest.txt"


def read_fixture():
    groups = defaultdict(list)
    with FIXTURE.open() as source:
        count = int(next(source))
        for _ in range(count):
            fields = next(source).split()
            groups[int(fields[0])].append([float(value) for value in fields[1:]])
        point_count = int(next(source))
        points = []
        for _ in range(point_count):
            fields = next(source).split()
            points.append([float(value) for value in fields[2:]])
    assert count == 3348 and point_count == 108 and len(groups) == 18
    return {key: np.asarray(value).reshape(-1, 3, 3)
            for key, value in groups.items()}, np.asarray(points)


def winding(triangles, point):
    vectors = triangles - point
    lengths = np.linalg.norm(vectors, axis=2)
    assert np.all(lengths > 0), "fixture point coincides with a facet vertex"
    unit = vectors / lengths[:, :, None]
    a, b, c = unit[:, 0], unit[:, 1], unit[:, 2]
    numerator = np.einsum("ij,ij->i", a, np.cross(b, c))
    denominator = (1 + np.einsum("ij,ij->i", a, b)
                   + np.einsum("ij,ij->i", b, c)
                   + np.einsum("ij,ij->i", c, a))
    return np.sum(2 * np.arctan2(numerator, denominator)) / (4 * np.pi)


def main():
    groups, points = read_fixture()
    expected = {}
    for line in MANIFEST.read_text().splitlines():
        component, point_index, side = line.split()
        expected[int(component), int(point_index)] = side
    assert len(expected) == 1944
    minimum_separation = float("inf")
    maximum_integer_residual = 0.0
    counts = {"I": 0, "O": 0}
    for component, triangles in groups.items():
        for point_index, point in enumerate(points):
            value = abs(winding(triangles, point))
            side = "I" if value > 0.5 else "O"
            assert side == expected[component, point_index], (
                component, point_index, value, side,
                expected[component, point_index])
            minimum_separation = min(minimum_separation, abs(value - 0.5))
            maximum_integer_residual = max(
                maximum_integer_residual, abs(value - round(value)))
            counts[side] += 1
    assert minimum_separation > 0.49, minimum_separation
    assert maximum_integer_residual < 1e-10, maximum_integer_residual
    print(f"independent solid-angle oracle: {counts}, "
          f"minimum threshold separation {minimum_separation:.12g}, "
          f"maximum integer residual {maximum_integer_residual:.12g}")


if __name__ == "__main__":
    main()
