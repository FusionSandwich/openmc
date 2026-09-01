#!/usr/bin/env python3
"""Plot the frozen paired exact-torus OpenMC benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    before = data["prechange"]
    after = data["postchange"]
    groups = [
        ("Pre-change", before["builtin_torus_raw_histories_per_s"],
         before["periodic_exact_torus_raw_histories_per_s"]),
        ("Native fast path", after["builtin_torus"]["raw_histories_per_s"],
         after["periodic_exact_torus"]["raw_histories_per_s"]),
    ]

    fig, ax = plt.subplots(figsize=(9.2, 5.6), constrained_layout=True)
    x = np.arange(len(groups), dtype=float)
    width = 0.34
    colors = ("#334e68", "#00a6a6")
    for offset, index, label, color in (
        (-width / 2, 1, "Built-in ZTorus", colors[0]),
        (width / 2, 2, "Periodic exact torus", colors[1]),
    ):
        medians = [float(np.median(group[index])) for group in groups]
        lows = [median - min(group[index]) for median, group in zip(medians, groups)]
        highs = [max(group[index]) - median for median, group in zip(medians, groups)]
        bars = ax.bar(x + offset, medians, width, label=label, color=color,
                      yerr=np.array([lows, highs]), capsize=5, alpha=0.94)
        for bar, value in zip(bars, medians):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 18000,
                    f"{value / 1000:.0f}k", ha="center", va="bottom",
                    fontsize=10, fontweight="bold")

    ax.annotate("44.83% of built-in", xy=(0, 350821), xytext=(0, 235000),
                ha="center", arrowprops={"arrowstyle": "->", "color": "#555"})
    ax.annotate("97.42% of built-in\n2.08× faster", xy=(1.17, 730255),
                xytext=(1.17, 560000), ha="center",
                arrowprops={"arrowstyle": "->", "color": "#555"})
    ax.axhline(0.95 * 749597, color="#e07a1f", linestyle="--", linewidth=1.4,
               label="95% stretch gate (paired post-change)")
    ax.set_xticks(x, [group[0] for group in groups])
    ax.set_ylabel("OpenMC calculation rate (histories/s)")
    ax.set_title("Exact periodic torus reaches built-in ZTorus performance class")
    ax.set_ylim(0, 900000)
    ax.grid(axis="y", alpha=0.22)
    ax.legend(loc="lower center", ncol=3, frameon=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)


if __name__ == "__main__":
    main()
