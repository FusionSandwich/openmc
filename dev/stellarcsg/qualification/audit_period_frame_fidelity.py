"""Sample cross-section support changes across WISTELL-D frame candidates.

This compares the geometry constructed by the runtime's tangent/normal frame,
not the stored but unused interpolated binormal. Results are sample witnesses,
not a continuous whole-coil Hausdorff certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cubic(values: np.ndarray, span: np.ndarray, u: np.ndarray):
    count = len(values)
    p0, p1, p2, p3 = (values[(span + offset) % count]
                      for offset in (-1, 0, 1, 2))
    x = u[:, None] if values.ndim == 2 else u
    c0 = (p0 + 4.0 * p1 + p2) / 6.0
    c1 = (-p0 + p2) / 2.0
    c2 = (p0 - 2.0 * p1 + p2) / 2.0
    c3 = (-p0 + 3.0 * p1 - 3.0 * p2 + p3) / 6.0
    return ((c3 * x + c2) * x + c1) * x + c0, \
        (3.0 * c3 * x + 2.0 * c2) * x + c1


def unit(values: np.ndarray) -> np.ndarray:
    lengths = np.linalg.norm(values, axis=-1)
    if not np.isfinite(lengths).all() or (lengths <= 0.0).any():
        raise ValueError("invalid frame vector")
    return values / lengths[..., None]


def sampled_frame(group: h5py.Group, span: np.ndarray, u: np.ndarray):
    center_control = np.asarray(group["centerline_coefficients"], dtype=float)
    normal_control = np.asarray(group["normal_coefficients"], dtype=float)
    major_control = np.asarray(group["major_radius_coefficients"], dtype=float)
    minor_control = np.asarray(group["minor_radius_coefficients"], dtype=float)
    center, derivative = cubic(center_control, span, u)
    supplied_normal, _ = cubic(normal_control, span, u)
    major, _ = cubic(major_control, span, u)
    minor, _ = cubic(minor_control, span, u)
    tangent = unit(derivative)
    normal = unit(supplied_normal
                  - np.sum(supplied_normal * tangent, axis=1)[:, None] * tangent)
    binormal = unit(np.cross(tangent, normal))
    normal = np.cross(binormal, tangent)
    if not np.isfinite(center).all() or (major <= 0.0).any() or (minor <= 0.0).any():
        raise ValueError("invalid center or radii")
    return center, tangent, normal, binormal, major, minor


def support(frame, directions: np.ndarray) -> np.ndarray:
    _, _, normal, binormal, major, minor = frame
    n = np.sum(normal[:, None, :] * directions, axis=2)
    b = np.sum(binormal[:, None, :] * directions, axis=2)
    return np.sqrt((major[:, None] * n) ** 2 + (minor[:, None] * b) ** 2)


def compare(left, right, span: np.ndarray, u: np.ndarray, angles: np.ndarray):
    c0, _, n0, b0, _, _ = left
    c1, _, _, _, _, _ = right
    direction = unit(np.cos(angles)[None, :, None] * n0[:, None, :]
                     + np.sin(angles)[None, :, None] * b0[:, None, :])
    change = (np.sum((c1 - c0)[:, None, :] * direction, axis=2)
              + support(right, direction) - support(left, direction))
    absolute = np.abs(change)
    sample, angle_index = np.unravel_index(np.argmax(absolute), absolute.shape)
    return {"max_sampled_support_difference_cm": float(absolute[sample, angle_index]),
            "witness": {"span": int(span[sample]), "u": float(u[sample]),
                        "section_angle_rad": float(angles[angle_index]),
                        "signed_support_change_cm": float(change[sample, angle_index]),
                        "center_separation_cm": float(np.linalg.norm(c1[sample] - c0[sample]))}}


def rotate_frame(frame, turns: int):
    vectors = []
    for value in frame[:4]:
        rotated = value.copy()
        for _ in range(turns):
            x, y = rotated[:, 0].copy(), rotated[:, 1].copy()
            rotated[:, 0], rotated[:, 1] = -y, x
        vectors.append(rotated)
    return (*vectors, *frame[4:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-h5", type=Path, required=True)
    parser.add_argument("--frame-h5", type=Path, required=True)
    parser.add_argument("--exact-h5", type=Path, required=True)
    parser.add_argument("--original-manifest", type=Path, required=True)
    parser.add_argument("--frame-manifest", type=Path, required=True)
    parser.add_argument("--exact-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    h5 = {name: getattr(args, name + "_h5") for name in ("original", "frame", "exact")}
    manifests = {name: getattr(args, name + "_manifest")
                 for name in ("original", "frame", "exact")}
    hashes = {name: sha256(path) for name, path in h5.items()}
    parsed = {name: json.loads(path.read_text()) for name, path in manifests.items()}
    for name in h5:
        if parsed[name]["input_hashes"]["h5_sha256"] != hashes[name]:
            raise ValueError(f"{name} manifest does not bind its HDF5")
    names = {name: {row["member"] for row in parsed[name]["members"]} for name in h5}
    if any(members != names["original"] for members in names.values()) \
            or len(names["original"]) != 48:
        raise ValueError("the three HDF5 variants have different members")
    if (parsed["original"]["families"] != parsed["frame"]["families"]
            or parsed["original"]["families"] != parsed["exact"]["families"]):
        raise ValueError("variants have different rotational families")
    rows = []
    rotational_pairs = []
    angles = np.arange(32) * (2.0 * np.pi / 32.0)
    with (h5py.File(h5["original"], "r") as original,
          h5py.File(h5["frame"], "r") as frame,
          h5py.File(h5["exact"], "r") as exact):
        for member in sorted(names["original"]):
            groups = {"original": original["coils"][member],
                      "frame": frame["coils"][member],
                      "exact": exact["coils"][member]}
            count = len(groups["original"]["centerline_coefficients"])
            if count != 256:
                raise ValueError("receipt sampling schema expects 256 controls per member")
            if any(len(group["centerline_coefficients"]) != count
                   for group in groups.values()):
                raise ValueError("different spline control counts")
            span = np.repeat(np.arange(count), 4)
            u = np.tile(np.asarray([0.0, 0.25, 0.5, 0.75]), count)
            sampled = {name: sampled_frame(group, span, u)
                       for name, group in groups.items()}
            rows.append({"member": member,
                         "original_to_frame": compare(sampled["original"],
                             sampled["frame"], span, u, angles),
                         "frame_to_exact": compare(sampled["frame"],
                             sampled["exact"], span, u, angles),
                         "original_to_exact": compare(sampled["original"],
                             sampled["exact"], span, u, angles)})
        handles = {"original": original, "frame": frame, "exact": exact}
        for family in parsed["original"]["families"]:
            members = family["full_device_members"]
            for turns, successor in enumerate(members[1:], start=1):
                cases = {}
                for name, handle in handles.items():
                    canonical_group = handle["coils"][members[0]]
                    successor_group = handle["coils"][successor]
                    count = len(canonical_group["centerline_coefficients"])
                    if count != 256:
                        raise ValueError("receipt sampling schema expects 256 controls per member")
                    if len(successor_group["centerline_coefficients"]) != count:
                        raise ValueError("rotational pair has different control count")
                    span = np.repeat(np.arange(count), 4)
                    u = np.tile(np.asarray([0.0, 0.25, 0.5, 0.75]), count)
                    rotated = rotate_frame(sampled_frame(canonical_group, span, u), turns)
                    image = sampled_frame(successor_group, span, u)
                    cases[name] = compare(rotated, image, span, u, angles)
                rotational_pairs.append({"canonical_member": members[0],
                                         "successor_member": successor,
                                         "quarter_turns": turns, "cases": cases})
    maxima = {key: max(row[key]["max_sampled_support_difference_cm"] for row in rows)
              for key in ("original_to_frame", "frame_to_exact", "original_to_exact")}
    rotational_maxima = {name: max(pair["cases"][name]["max_sampled_support_difference_cm"]
                                 for pair in rotational_pairs) for name in h5}
    report = {"schema": "stellarcsg.period-frame-fidelity-sample/v1",
              "state": "SAMPLED_SECTION_SUPPORT_ONLY_NOT_PHYSICAL_FIDELITY",
              "hashes": {**{name + "_h5_sha256": hashes[name] for name in h5},
                         **{name + "_manifest_sha256": sha256(manifests[name])
                            for name in manifests},
                         "auditor_sha256": sha256(Path(__file__))},
              "samples_per_member": 4 * 256,
              "directions_per_sample": len(angles),
              "maxima_cm": maxima, "rows": rows,
              "rotational_pair_count": len(rotational_pairs),
              "rotational_maxima_cm": rotational_maxima,
              "rotational_pairs": rotational_pairs,
              "claim_boundary": "Support differences of corresponding filled elliptical cross-sections at 1024 spline parameters and 32 in-plane directions per member. Rotational pairs compare each 90-degree canonical image with its stored successor. A sampled witness is a local section-support difference, not a global full-coil surface Hausdorff bound. The original and frame candidates are separate payloads; no source filament, winding-pack, wall or transport fidelity is certified."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"state": report["state"], "maxima_cm": maxima,
                      "rotational_maxima_cm": rotational_maxima}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
