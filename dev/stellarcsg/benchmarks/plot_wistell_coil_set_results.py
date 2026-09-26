"""Render retained WISTELL-D complete-coil-set geometry and speed figures."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO = Path(__file__).resolve().parents[3]
RAW = REPO / "dev/stellarcsg/benchmarks/raw"
OUTPUT = REPO / "dev/stellarcsg/plots/performance_redesign"
MAGNETS = Path(
    r"C:\HTS_transport\plots\stellarcsg_multiconfig_20260831\wistell_d\magnets"
)
sys.path.insert(0, str(REPO / "dev/stellarcsg/python"))
from stellarcsg.spline import sample_periodic_cubic


COLORS = {
    "csg": "#d95f02",
    "coarse": "#1b9e77",
    "fine": "#2c7fb8",
    "embree": "#7b3294",
    "context": "#b5bdc8",
    "ink": "#172033",
}


def frame(group, angle):
    center = []
    tangent = []
    normal = []
    for axis in range(3):
        value, derivative = sample_periodic_cubic(
            np.asarray(group["centerline_coefficients"])[:, axis], angle
        )
        center.append(value)
        tangent.append(derivative)
        normal.append(sample_periodic_cubic(
            np.asarray(group["normal_coefficients"])[:, axis], angle
        )[0])
    center = np.stack(center, axis=-1)
    tangent = np.stack(tangent, axis=-1)
    tangent /= np.linalg.norm(tangent, axis=-1)[..., None]
    normal = np.stack(normal, axis=-1)
    normal -= np.sum(normal * tangent, axis=-1)[..., None] * tangent
    normal /= np.linalg.norm(normal, axis=-1)[..., None]
    return center, normal, np.cross(tangent, normal)


def tube(group, axial_count, cross_count, axial_fraction=1.0):
    axial = 2.0 * np.pi * axial_fraction * np.arange(axial_count + 1) / axial_count
    cross = 2.0 * np.pi * np.arange(cross_count + 1) / cross_count
    center, normal, binormal = frame(group, axial)
    return center[:, None, :] + (
        np.cos(cross)[None, :, None] * normal[:, None, :]
        + np.sin(cross)[None, :, None] * binormal[:, None, :]
    )


def equal_3d(axis, points, pad=0.05):
    low = np.min(points, axis=0)
    high = np.max(points, axis=0)
    center = 0.5 * (low + high)
    radius = 0.5 * np.max(high - low) * (1.0 + pad)
    axis.set_xlim(center[0] - radius, center[0] + radius)
    axis.set_ylim(center[1] - radius, center[1] + radius)
    axis.set_zlim(center[2] - radius, center[2] + radius)
    axis.set_box_aspect((1, 1, 1))
    axis.set_proj_type("ortho")
    axis.set_axis_off()


def geometry_plot():
    receipt = json.loads((MAGNETS / "compile_receipt.json").read_text())
    selected = int(receipt["native_csg"]["representative_nonplanar_coil_id"])
    with h5py.File(MAGNETS / "swept_coils_1cm.h5", "r") as handle:
        groups = [handle["coils"][name] for name in sorted(handle["coils"])]
        angle = 2.0 * np.pi * np.arange(256) / 256
        curves = [frame(group, angle)[0] for group in groups]
        bounds = np.concatenate(curves)
        representative = handle["coils"][f"coil_{selected:03d}"]
        retained_fine_bins = 6
        local_fraction = retained_fine_bins / 512.0
        smooth = tube(representative, 160, 64, local_fraction)
        faceted = tube(representative, retained_fine_bins, 48, local_fraction)

        figure = plt.figure(figsize=(16, 9), constrained_layout=True)
        figure.suptitle(
            f"WISTELL-D complete magnet set · 48 coils · representative coil {selected}",
            fontsize=17,
            weight="bold",
            color=COLORS["ink"],
        )
        columns = (
            ("Native swept CSG", COLORS["csg"]),
            ("Direct DAGMC fine mesh", COLORS["fine"]),
            ("Double Down / Embree\nsame fine triangles", COLORS["embree"]),
        )
        for column, (title, color) in enumerate(columns):
            axis = figure.add_subplot(2, 3, column + 1, projection="3d")
            for index, curve in enumerate(curves, start=1):
                axis.plot(
                    curve[:, 0], curve[:, 1], curve[:, 2],
                    color=color if index == selected else COLORS["context"],
                    lw=1.6 if index == selected else 0.42,
                    alpha=1.0 if index == selected else 0.42,
                )
            axis.set_title(title, fontsize=12, weight="bold")
            axis.view_init(elev=24, azim=35)
            equal_3d(axis, bounds)

            detail = figure.add_subplot(2, 3, column + 4, projection="3d")
            xyz = smooth if column == 0 else faceted
            detail.plot_surface(
                xyz[:, :, 0], xyz[:, :, 1], xyz[:, :, 2],
                color=color,
                edgecolor="none" if column == 0 else "white",
                linewidth=0.0 if column == 0 else 0.14,
                antialiased=True,
                shade=column == 0,
                alpha=0.96,
            )
            detail.set_title(
                "Authoritative spline surface"
                if column == 0 else "512 × 48 retained facets",
                fontsize=10,
            )
            detail.view_init(elev=18, azim=52)
            equal_3d(detail, xyz.reshape(-1, 3), pad=0.08)

    figure.text(
        0.5, 0.008,
        "Source: coils.wistell-d SHA-256 774836…159b · standardized 1 cm circular tube. "
        "Embree/Double Down uses the same mesh geometry, but its runtime was unavailable and was not benchmarked.",
        ha="center", fontsize=9,
    )
    path = OUTPUT / "wistell_coil_set_geometry_comparison.png"
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return path


def scaling_plot(scaling):
    rows = scaling["results"]
    counts = np.array([row["coil_count"] for row in rows])
    nanoseconds = np.array([row["distance_ns_per_call"] for row in rows])
    candidates = np.array([row["candidate_coils_per_call"] for row in rows])
    spans = np.array([row["candidate_spans_per_call"] for row in rows])
    figure, axis = plt.subplots(figsize=(11.5, 7.2))
    figure.subplots_adjust(bottom=0.17, top=0.9, left=0.09, right=0.91)
    axis.plot(counts, nanoseconds, "o-", color=COLORS["csg"], lw=2.4,
              label="Native distance time")
    axis.set_xlabel("Coils in shared top-level BVH")
    axis.set_ylabel("Distance time (ns/ray)", color=COLORS["csg"])
    axis.tick_params(axis="y", labelcolor=COLORS["csg"])
    axis.grid(alpha=0.22)
    second = axis.twinx()
    second.plot(counts, candidates, "s-", color=COLORS["fine"], lw=2.1,
                label="Candidate coils/ray")
    second.plot(counts, spans, "^-", color=COLORS["coarse"], lw=2.1,
                label="Candidate spans/ray")
    second.set_ylabel("Candidates per ray")
    lines = axis.lines + second.lines
    axis.legend(lines, [line.get_label() for line in lines], loc="upper left")
    axis.set_title(
        "WISTELL-D shared coil-set BVH scales sublinearly",
        fontsize=16, weight="bold", color=COLORS["ink"],
    )
    axis.annotate(
        "48× more coils\n2.29× distance cost\n2.86 candidate coils/ray",
        xy=(48, nanoseconds[-1]), xytext=(27, 820),
        arrowprops={"arrowstyle": "->", "color": COLORS["ink"]},
        fontsize=10, color=COLORS["ink"],
    )
    figure.text(
        0.5, 0.008,
        "Intel i9-10850K · 1 thread pinned to CPU 2 · 100,000 deterministic rays/case · "
        "circular specialization · zero production oracle calls · 6,000 brute-set mismatches: 0",
        ha="center", fontsize=9,
    )
    path = OUTPUT / "wistell_coil_set_scaling.png"
    figure.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(figure)
    return path


def speed_plot(openmc):
    methods = ("native_csg", "dagmc_coarse", "dagmc_fine")
    labels = ("Native CSG\n48-coil BVH", "Direct DAGMC\ncoarse mesh",
              "Direct DAGMC\nfine mesh")
    colors = (COLORS["csg"], COLORS["coarse"], COLORS["fine"])
    medians = [openmc["results"][method]["median_histories_per_s"]
               for method in methods]
    low = [medians[i] - openmc["results"][method]["minimum_histories_per_s"]
           for i, method in enumerate(methods)]
    high = [openmc["results"][method]["maximum_histories_per_s"] - medians[i]
            for i, method in enumerate(methods)]
    figure, axis = plt.subplots(figsize=(11.5, 7.2))
    figure.subplots_adjust(bottom=0.2, top=0.9, left=0.1, right=0.98)
    positions = np.arange(4)
    axis.bar(positions[:3], medians, color=colors, width=0.68,
             yerr=np.array([low, high]), capsize=6)
    for position, method, color in zip(positions[:3], methods, colors):
        values = openmc["results"][method]["raw_histories_per_s"]
        jitter = np.linspace(-0.11, 0.11, len(values))
        axis.scatter(position + jitter, values, color="#172033", s=18, zorder=3)
        axis.text(position, medians[position] + high[position] + 8500,
                  f"{medians[position]:,.0f}", ha="center", weight="bold",
                  color=color)
    axis.bar(3, 0, edgecolor=COLORS["embree"], facecolor="none",
             linestyle="--", linewidth=2.0, width=0.68)
    axis.text(3, 0.48 * max(medians), "NOT RUN\nunavailable in\npinned binary",
              ha="center", va="center", color=COLORS["embree"], weight="bold")
    axis.set_xticks(positions, labels + ("Double Down /\nEmbree",))
    axis.set_ylabel("OpenMC calculation rate (histories/s)")
    axis.set_ylim(0, max(medians) * 1.23)
    axis.grid(axis="y", alpha=0.22)
    ratio = openmc["ratios"]["native_over_fine_dagmc"]
    axis.set_title(
        f"Complete WISTELL-D coil set · native CSG is {ratio:.2f}× faster than fine DAGMC",
        fontsize=15, weight="bold", color=COLORS["ink"],
    )
    figure.text(
        0.5, 0.008,
        "100,000 histories × 7 randomized repetitions · identical source/seed/materials · "
        "1 thread pinned to CPU 2 · native geometry debug PASS; DAGMC OpenMC overlap check FAILS on implicit complement",
        ha="center", fontsize=8.8,
    )
    path = OUTPUT / "wistell_coil_set_openmc_speed.png"
    figure.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(figure)
    return path


def multiconfig_geometry_plot(multiconfig):
    rows = multiconfig["results"]
    figure, axes = plt.subplots(
        len(rows), 3, figsize=(14, 2.45 * len(rows)), constrained_layout=True
    )
    columns = (
        ("Native swept CSG", COLORS["csg"]),
        ("Direct DAGMC mesh", COLORS["fine"]),
        ("Embree / Double Down\nsame fine triangles", COLORS["embree"]),
    )
    for column, (title, _) in enumerate(columns):
        axes[0, column].set_title(title, fontsize=13, weight="bold", pad=12)
    for row_index, record in enumerate(rows):
        payload = MAGNETS.parent.parent / record["case"] / "magnets/swept_coils_1cm.h5"
        with h5py.File(payload, "r") as handle:
            angle = 2.0 * np.pi * np.arange(192) / 192
            curves = [frame(handle["coils"][name], angle)[0]
                      for name in sorted(handle["coils"])]
        bounds = np.concatenate(curves)[:, :2]
        low, high = np.min(bounds, axis=0), np.max(bounds, axis=0)
        center = 0.5 * (low + high)
        radius = 0.53 * np.max(high - low)
        for column, (_, color) in enumerate(columns):
            axis = axes[row_index, column]
            for index, curve in enumerate(curves, start=1):
                axis.plot(
                    curve[:, 0], curve[:, 1],
                    color=color if index == record["representative_coil_id"]
                    else COLORS["context"],
                    lw=1.25 if index == record["representative_coil_id"] else 0.34,
                    alpha=1.0 if index == record["representative_coil_id"] else 0.42,
                )
            axis.set_xlim(center[0] - radius, center[0] + radius)
            axis.set_ylim(center[1] - radius, center[1] + radius)
            axis.set_aspect("equal")
            axis.set_xticks([])
            axis.set_yticks([])
            if column == 0:
                axis.set_ylabel(
                    f"{record['label']}\n{record['source_coil_count']} coils",
                    rotation=0, ha="right", va="center", fontsize=8.5,
                    labelpad=10,
                )
    figure.suptitle(
        "Thirteen stellarator coil configurations · same-lineage geometry",
        fontsize=17, weight="bold", color=COLORS["ink"],
    )
    figure.text(
        0.5, 0.002,
        "Colored curve: independently qualified most-nonplanar coil. Gray: complete set. "
        "Mesh and Embree share triangles; device-scale centerlines overlap the native source. Embree timing NOT RUN.",
        ha="center", fontsize=9,
    )
    path = OUTPUT / "multiconfig_coil_geometry_atlas.png"
    figure.savefig(path, dpi=145, bbox_inches="tight")
    plt.close(figure)
    return path


def multiconfig_kernel_plot(multiconfig):
    rows = multiconfig["results"]
    labels = [row["label"].replace("Landreman-Paul ", "LP ") for row in rows]
    times = [row["distance_ns_per_call"] for row in rows]
    fallback = [100.0 * row["local_subdivision_calls_per_call"] for row in rows]
    positions = np.arange(len(rows))
    figure, axis = plt.subplots(figsize=(14, 8))
    figure.subplots_adjust(bottom=0.28, top=0.89, left=0.09, right=0.91)
    axis.bar(positions, times, color=COLORS["csg"], alpha=0.92)
    axis.set_yscale("log")
    axis.set_ylabel("Native distance time (ns/ray, log scale)")
    axis.set_xticks(positions, labels, rotation=42, ha="right")
    axis.grid(axis="y", which="both", alpha=0.22)
    second = axis.twinx()
    second.plot(positions, fallback, "s--", color=COLORS["fine"],
                label="Local fallback (%)")
    second.set_ylabel("Local bounded fallback (%)")
    second.legend(loc="upper left")
    axis.set_title(
        "General swept-coil kernel across 13 stellarator configurations",
        fontsize=16, weight="bold", color=COLORS["ink"],
    )
    for position, value in zip(positions, times):
        axis.text(position, value * 1.08, f"{value / 1000:.2f} µs",
                  ha="center", va="bottom", fontsize=7.7)
    figure.text(
        0.5, 0.012,
        "Most-nonplanar coil per source set · 1,000 timed rays + 100 independent-oracle rays/case · "
        "1,300 total oracle mismatches: 0 · zero production global-reference calls",
        ha="center", fontsize=9,
    )
    path = OUTPUT / "multiconfig_coil_kernel_speed.png"
    figure.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(figure)
    return path


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    scaling = json.loads(
        (RAW / "wistell_coil_set_scaling_20260831.json").read_text()
    )
    openmc = json.loads(
        (RAW / "wistell_coil_set_openmc_20260831.json").read_text()
    )
    multiconfig = json.loads(
        (RAW / "multiconfig_coil_local_kernel_20260831.json").read_text()
    )
    paths = [geometry_plot(), scaling_plot(scaling), speed_plot(openmc),
             multiconfig_geometry_plot(multiconfig),
             multiconfig_kernel_plot(multiconfig)]
    print(json.dumps({"plots": [str(path) for path in paths]}, indent=2))


if __name__ == "__main__":
    main()
