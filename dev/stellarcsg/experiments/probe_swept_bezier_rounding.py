"""Look for finite stored-power Horner values outside the current span hull.

This is a scalar diagnostic for the build_spans() bound, not a root proof.
"""

import json
import math
import random


MATRIX = (
    (1.0 / 6.0, 4.0 / 6.0, 1.0 / 6.0, 0.0),
    (-0.5, 0.0, 0.5, 0.0),
    (0.5, -1.0, 0.5, 0.0),
    (-1.0 / 6.0, 0.5, -0.5, 1.0 / 6.0),
)


def compiled_power(controls):
    result = []
    for row in MATRIX:
        value = 0.0
        for multiplier, control in zip(row, controls):
            value += multiplier * control
        result.append(value)
    return result


def bezier_hull(power):
    return (
        power[0],
        power[0] + power[1] / 3.0,
        power[0] + 2.0 * power[1] / 3.0 + power[2] / 3.0,
        power[0] + power[1] + power[2] + power[3],
    )


def horner(power, u):
    return ((power[3] * u + power[2]) * u + power[1]) * u + power[0]


def main():
    rng = random.Random(0x57E11A)
    scales = (1.0e12, 1.0e14, 1.0e16, 1.0e18)
    us = (math.nextafter(0.0, 1.0),
          math.nextafter(1.0, 0.0),
          *(index / 64.0 for index in range(1, 64)))
    for scale in scales:
        for trial in range(20000):
            controls = [
                rng.uniform(-1.0, 1.0) * scale for _ in range(4)
            ]
            power = compiled_power(controls)
            hull = bezier_hull(power)
            upper = max(hull) + 0.25 + 1.0e-12
            lower = min(hull) - 0.25 - 1.0e-12
            for u in us:
                value = horner(power, u)
                if not math.isfinite(value):
                    continue
                if value < lower or value > upper:
                    print(json.dumps({
                        "scale": scale,
                        "trial": trial,
                        "controls": controls,
                        "power": power,
                        "hull": hull,
                        "u": u,
                        "value": value,
                        "box_lower": lower,
                        "box_upper": upper,
                        "underbound": max(lower - value, value - upper),
                    }, indent=2))
                    return
    print(json.dumps({"state": "no_witness_in_bounded_search"}))


if __name__ == "__main__":
    main()
