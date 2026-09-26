"""Independent Fraction/Bernstein enclosures of the prepared coil centerline."""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path

import h5py


def product(a, b):
    m, n = len(a) - 1, len(b) - 1
    return [sum((a[i] * b[k - i] *
                 F(math.comb(m, i) * math.comb(n, k - i), math.comb(m + n, k))
                 for i in range(max(0, k - n), min(m, k) + 1)), F(0))
            for k in range(m + n + 1)]


def split(a):
    work, left, right = list(a), [a[0]], [a[-1]]
    while len(work) > 1:
        work = [(x + y) / 2 for x, y in zip(work, work[1:])]
        left.append(work[0])
        right.append(work[-1])
    return left, list(reversed(right))


def tiles(a, depth):
    result = [a]
    for _ in range(depth):
        result = [child for item in result for child in split(item)]
    return result


def square_norm(x, y):
    return [a + b for a, b in zip(product(x, x), product(y, y))]


def cross(x, y, dx, dy):
    return [a - b for a, b in zip(product(x, dy), product(y, dx))]


def root_bounds(value):
    # Two directed binary64 steps cover conversion and correctly rounded sqrt.
    q = float(value)
    lo = math.sqrt(max(0., math.nextafter(q, -math.inf)))
    hi = math.sqrt(math.nextafter(q, math.inf))
    return math.nextafter(lo, -math.inf), math.nextafter(hi, math.inf)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("coil", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with h5py.File(args.coil) as h:
        g = h["coils/coil_000"]
        controls = [[F(float(v)) for v in row]
                    for row in g["centerline_coefficients"][...]]
        if any(p[2] != 0 for p in controls):
            raise ValueError("nonplanar fixture")
        if any(float(v) != 5. for name in ("major_radius_coefficients",
                                          "minor_radius_coefficients")
               for v in g[name][...]):
            raise ValueError("unexpected section")
    n, seams = len(controls), []
    radial_min, radial_max = None, None
    speed_min, accel_max = None, None
    length_lo, length_hi = 0., 0.
    positive_angle, positive_curvature, homotopy = True, True, True
    for s in range(n):
        pp = [controls[(s + i - 1) % n] for i in range(4)]
        axes = [[(pp[0][a] + 4 * pp[1][a] + pp[2][a]) / 6,
                 (2 * pp[1][a] + pp[2][a]) / 3,
                 (pp[1][a] + 2 * pp[2][a]) / 3,
                 (pp[1][a] + 4 * pp[2][a] + pp[3][a]) / 6]
                for a in range(2)]
        x, y = axes
        seams.append((x[0], y[0]))
        dx, dy = [[3 * (v[i + 1] - v[i]) for i in range(3)] for v in axes]
        ddx, ddy = [[2 * (v[i + 1] - v[i]) for i in range(2)] for v in (dx, dy)]
        positive_angle &= min(cross(x, y, dx, dy)) > 0
        positive_curvature &= min(cross(dx, dy, ddx, ddy)) > 0
        vx, vy = x[0] + x[-1], y[0] + y[-1]
        homotopy &= all(a * vx + b * vy > 0 for a, b in zip(x, y))
        sq = square_norm(x, y)
        for tile in tiles(sq, 6):
            low, high = min(tile), max(tile)
            radial_min = low if radial_min is None else min(radial_min, low)
            radial_max = high if radial_max is None else max(radial_max, high)
        speed = square_norm(dx, dy)
        speed_min = min(speed) if speed_min is None else min(speed_min, min(speed))
        accel = square_norm(ddx, ddy)
        accel_max = max(accel) if accel_max is None else max(accel_max, max(accel))
        for tile in tiles(speed, 6):
            low, high = root_bounds(min(tile))[0], root_bounds(max(tile))[1]
            length_lo = math.nextafter(length_lo + low / 64, -math.inf)
            length_hi = math.nextafter(length_hi + high / 64, math.inf)
    winding = 0
    for a, b in zip(seams, seams[1:] + seams[:1]):
        orient = a[0] * b[1] - a[1] * b[0]
        if a[1] <= 0 < b[1] and orient > 0:
            winding += 1
        if b[1] <= 0 < a[1] and orient < 0:
            winding -= 1
    low, high = root_bounds(radial_min)[0], root_bounds(radial_max)[1]
    curvature_upper = math.nextafter(root_bounds(accel_max)[1] /
                                    math.nextafter(float(speed_min), -math.inf),
                                    math.inf)
    if not (homotopy and winding == 1 and positive_angle and positive_curvature
            and speed_min > 0 and curvature_upper * 5 < 1):
        raise ValueError("convex regular one-turn ring obligations failed")
    result = dict(
        schema="stellarcsg.exact-proxy-centerline-enclosure/v1",
        coil_sha256=hashlib.sha256(args.coil.read_bytes()).hexdigest(),
        method="Original binary64 controls as Fractions; exact cardinal Bezier conversion, Bernstein products and six dyadic subdivisions",
        radial_squared_bounds_exact=[str(radial_min), str(radial_max)],
        radial_bounds_cm=[low, high],
        max_radial_deviation_from_R100_cm=max(100 - low, high - 100),
        angular_derivative_positive=positive_angle,
        signed_curvature_positive=positive_curvature,
        span_chord_homotopy_in_origin_free_halfplane=homotopy,
        exact_seam_polygon_winding=winding,
        curvature_upper_per_cm=curvature_upper,
        length_bounds_cm=[length_lo, length_hi],
        tube_volume_bounds_cm3=[
            math.nextafter(float(F(math.nextafter(math.pi, -math.inf)) * 25 * F(length_lo)), -math.inf),
            math.nextafter(float(F(math.nextafter(math.pi, math.inf)) * 25 * F(length_hi)), math.inf)],
        volume_assumption="Convex simple planar C2 curve, tube radius below minimum curvature radius: embedded tube has volume pi*r^2*length; independent reviewer must accept the reach argument before physical atom-count use",
        claim_boundary="Centerline geometric enclosure, not transport/tally equivalence. Prepared fixture only.")
    with args.output.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
