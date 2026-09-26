"""Independent exact-rational support/witness certificate for analytic member 2.

Uses original binary64 controls as rational numbers, cardinal cubic Bezier
identities, and exact de Casteljau subdivision. No runtime stationary solver,
compiled powers, floating interval implementation, or candidate distance is
used to construct the reference.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import heapq
import json
import math
from pathlib import Path
import subprocess

import h5py


EXPECTED_HASH = "39f77da5ab1fe427cce58b153e9b52cf8915e9973a9b8f3dfad5ab3b00a9e46d"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rational(value: object) -> Fraction:
    return Fraction.from_float(float(value))


def split(controls: tuple[Fraction, ...]) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...]]:
    levels = [controls]
    while len(levels[-1]) > 1:
        previous = levels[-1]
        levels.append(tuple((previous[i] + previous[i + 1]) / 2
                            for i in range(len(previous) - 1)))
    return (tuple(level[0] for level in levels),
            tuple(level[-1] for level in reversed(levels)))


def bezier(values: list[Fraction], span: int) -> tuple[Fraction, ...]:
    n = len(values)
    p0, p1, p2, p3 = (values[(span + k) % n] for k in (-1, 0, 1, 2))
    return ((p0 + 4 * p1 + p2) / 6, (2 * p1 + p2) / 3,
            (p1 + 2 * p2) / 3, (p1 + 4 * p2 + p3) / 6)


def support(values: list[Fraction], tolerance: Fraction) -> dict:
    queue = []
    serial = 0
    lower = max(bezier(values, s)[0] for s in range(len(values)))
    subdivisions = 0
    maximum_depth = 0

    def insert(controls: tuple[Fraction, ...], span: int, depth: int) -> None:
        nonlocal serial, lower
        left, _ = split(controls)
        lower = max(lower, controls[0], controls[-1], left[-1])
        heapq.heappush(queue, (-max(controls), serial, controls, span, depth))
        serial += 1

    for span in range(len(values)):
        insert(bezier(values, span), span, 0)
    while -queue[0][0] - lower > tolerance:
        _, _, controls, span, depth = heapq.heappop(queue)
        if subdivisions >= 100000 or depth >= 100:
            raise RuntimeError("Exact support certificate budget exhausted")
        left, right = split(controls)
        insert(left, span, depth + 1)
        insert(right, span, depth + 1)
        subdivisions += 1
        maximum_depth = max(maximum_depth, depth + 1)
    upper = -queue[0][0]
    assert lower <= upper and upper - lower <= tolerance
    return {"lower": lower, "upper": upper, "subdivisions": subdivisions,
            "maximum_depth": maximum_depth, "terminal_tiles": len(queue)}


def encode(value: object) -> object:
    if isinstance(value, Fraction):
        return {"rational": str(value), "approximate": float(value)}
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h5", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--build-receipt", type=Path)
    parser.add_argument("--library", type=Path)
    parser.add_argument("--source-ref", help="Read-only Git source snapshot for a historical build")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    if (args.probe is None) != (args.binary is None):
        parser.error("--probe and --binary must be supplied together")
    if args.build_receipt is not None and args.binary is None:
        parser.error("--build-receipt requires --probe and --binary")
    if digest(args.h5) != EXPECTED_HASH:
        raise ValueError("Analytic input hash mismatch")
    with h5py.File(args.h5, "r") as handle:
        group = handle["coils/coil_002"]
        points = [[rational(value) for value in row]
                  for row in group["centerline_coefficients"][:]]
        normals = [[rational(value) for value in row]
                   for row in group["normal_coefficients"][:]]
        a = [rational(value) for value in group["major_radius_coefficients"][:]]
        b = [rational(value) for value in group["minor_radius_coefficients"][:]]
    if not (len(points) == 256 and all(row[2] == 0 for row in points)
            and all(row[0] == row[1] == 0 and row[2] > 0 for row in normals)
            and all(value == 24 for value in a) and all(value == 14 for value in b)):
        raise ValueError("Member 2 planar/axial-normal/constant-radius contract differs")
    x_support = support([point[0] for point in points], Fraction(1, 10**12))
    if not (abs(x_support["lower"] - 520) < Fraction(1, 10**10)
            and abs(x_support["upper"] - 520) < Fraction(1, 10**10)):
        raise ValueError("Global support is not within 1e-10 of x=520")
    witness = tuple(bezier([point[axis] for point in points], 0)[0]
                    for axis in range(3))
    t_prefix = 550 - (x_support["upper"] + 14)
    t_left = t_prefix - Fraction(1, 10**12)
    t_right = Fraction(16) + Fraction(1, 10**12)
    point_right = (550 - t_right, Fraction(0), Fraction(0))
    witness_q = sum((point_right[axis] - witness[axis])**2 /
                    (Fraction(24) if axis == 2 else Fraction(14))**2
                    for axis in range(3))
    x_clearance_left = 550 - t_left - x_support["upper"] - 14
    assert t_left < t_prefix < t_right and witness_q < 1 and x_clearance_left > 0
    report = {
        "schema": "stellarcsg.independent-exact-offset-seam-reference/v1",
        "state": "FIRST_BOUNDARY_BRACKET_CERTIFIED_EXACT_RATIONAL",
        "h5_path": str(args.h5), "h5_sha256": EXPECTED_HASH,
        "script_sha256": digest(Path(__file__)),
        "dataset": "/coils/coil_002", "sample_count": len(points),
        "geometry_representation": "exact_control_offset",
        "origin": [550, 0, 0], "direction": [-1, 0, 0],
        "actual_control_radii": {"a": 24, "b": 14},
        "global_x_support": x_support,
        "seam_witness_exact": witness,
        "strict_outside_t": t_left,
        "root_free_prefix_exclusive_upper_t": t_prefix,
        "strict_inside_t": t_right,
        "strict_outside_x_clearance": x_clearance_left,
        "inside_witness_scaled_distance_squared": witness_q,
        "inside_witness_margin": 1 - witness_q,
        "first_boundary_enclosure": [t_prefix, t_right],
        "first_boundary_enclosure_width": t_right - t_prefix,
        "proof": [
            "Exact Bezier convex hulls cover every owned cubic parameter; adaptive exact de Casteljau subdivision bounds global maximum x.",
            "For every t below the prefix upper endpoint, ray x exceeds every center x plus b=14, hence every scaled squared center distance exceeds one.",
            "The seam control-derived center witness has scaled squared distance strictly below one at the right endpoint, hence the global minimum is inside.",
            "Continuity of distance to the compact scaled curve proves a first boundary point within the enclosure; no stationarity or runtime arithmetic assumptions are used."
        ],
        "claim_boundary": "One member-2 exact-control x-ray first-boundary existence/enclosure. Does not prove crossing uniqueness, normals, implementation equivalence, legacy geometry, whole frozen bank, or transport qualification.",
    }
    source_root = Path(__file__).resolve().parents[1]
    report["source_sha256"] = {
        str(path.relative_to(source_root)): digest(path)
        for path in (source_root / "src" / "certified_spline_offset.cpp",
                     source_root / "src" / "compiled_swept_surface.cpp",
                     source_root / "qualification" / "certified_offset_probe.cpp")
        if path.is_file()
    }
    if args.probe is not None:
        rows = [json.loads(line) for line in args.probe.read_text().splitlines()
                if line.strip()]
        candidates = [row for row in rows if row.get("kind") == "member2_seam"]
        if len(candidates) != 1:
            raise ValueError("Probe must contain exactly one member-2 seam result")
        candidate = candidates[0]
        observed = candidate.get("distance_cm")
        if (candidate.get("representation") != "exact_control_offset"
                or candidate.get("found") is not True
                or candidate.get("unresolved") is not False
                or type(observed) not in (float, int) or not math.isfinite(observed)):
            raise ValueError("Probe lacks a finite admitted exact-control distance")
        observed_exact = Fraction.from_float(float(observed))
        worst_error = max(abs(observed_exact - t_prefix), abs(observed_exact - t_right))
        declared_tolerance = Fraction(1, 10**11)
        if worst_error > declared_tolerance:
            raise ValueError("Observed distance is outside independent first-root tolerance")
        report["observed_distance_acceptance"] = {
            "probe_path": str(args.probe), "probe_sha256": digest(args.probe),
            "binary_path": str(args.binary), "binary_sha256": digest(args.binary),
            "observed_binary64_distance_exact": observed_exact,
            "worst_error_to_any_first_root_in_enclosure": worst_error,
            "absolute_tolerance": declared_tolerance,
            "state": "SCALAR_DISTANCE_INDEPENDENTLY_ACCEPTED",
            "execution_binding_limit": "Hashes bind supplied artifacts; the build/launch receipt must establish that this executable produced the supplied probe and corresponds to these sources."
        }
        native = [row for row in rows if row.get("kind") == "native_surface"]
        if native:
            if (len(native) != 1 or native[0].get("state") != "PASS"
                    or native[0].get("surface_id") != 1902
                    or type(native[0].get("distance_cm")) not in (float, int)
                    or Fraction.from_float(float(native[0]["distance_cm"])) != observed_exact):
                raise ValueError("Native surface probe does not agree with checked seam distance")
            report["native_surface_observation"] = native[0]
    if args.build_receipt is not None:
        receipt = json.loads(args.build_receipt.read_text())
        repo_root = Path(__file__).resolve().parents[3]
        if (receipt.get("exit_code") != 0 or receipt.get("changed_inputs") != []
                or receipt.get("inputs_before") != receipt.get("inputs_after")):
            raise ValueError("Build receipt lacks stable successful compilation")
        checked = {}
        changed_live_inputs = {}
        snapshot_inputs = {}
        excluded_test_artifacts = {}
        for section in ("inputs_after", "outputs"):
            for relative, expected in receipt[section].items():
                actual = digest(repo_root / relative)
                if actual != expected:
                    if relative in ("dev/stellarcsg/tests/test_certified_offset.cpp",
                                    "build/astra/stellarcsg_offset_tests"):
                        excluded_test_artifacts[relative] = {"recorded_sha256": expected,
                                                            "live_sha256": actual}
                        continue
                    if section != "inputs_after" or args.source_ref is None:
                        raise ValueError("Build artifact hash mismatch: " + relative)
                    result = subprocess.run(["git", "-c", "safe.directory=" + str(repo_root),
                                             "show", args.source_ref + ":" + relative],
                                            cwd=repo_root, capture_output=True)
                    native_git = Path("/mnt/c/Program Files/Git/cmd/git.exe")
                    if result.returncode and native_git.is_file() and str(repo_root).startswith("/mnt/c/"):
                        # Linked Windows worktrees record Windows paths in .git.
                        windows_root = "C:/" + str(repo_root)[len("/mnt/c/"):]
                        result = subprocess.run([str(native_git), "-C", windows_root,
                                                 "show", args.source_ref + ":" + relative],
                                                capture_output=True)
                    if result.returncode:
                        raise ValueError("Cannot read historical source: " + result.stderr.decode(errors="replace"))
                    content = result.stdout
                    snapshot = hashlib.sha256(content).hexdigest()
                    # Git stores canonical LF while Windows checkout may use CRLF.
                    if snapshot != expected:
                        snapshot = hashlib.sha256(content.replace(b"\n", b"\r\n")).hexdigest()
                    if snapshot != expected:
                        raise ValueError("Historical build source mismatch: " + relative)
                    changed_live_inputs[relative] = actual
                    snapshot_inputs[relative] = snapshot
                checked[relative] = expected
        binary_relative = str(args.binary.resolve().relative_to(repo_root)).replace("\\", "/")
        if receipt["outputs"].get(binary_relative) != digest(args.binary):
            raise ValueError("Supplied executable is not a bound build output")
        if args.library is not None:
            library_relative = str(args.library.resolve().relative_to(repo_root)).replace("\\", "/")
            if receipt["outputs"].get(library_relative) != digest(args.library):
                raise ValueError("Supplied library is not a bound build output")
        report["build_artifact_binding"] = {
            "receipt_path": str(args.build_receipt), "receipt_sha256": digest(args.build_receipt),
            "checked_build_artifact_sha256": checked,
            "excluded_post_build_test_artifacts": excluded_test_artifacts,
            "changed_live_input_sha256": changed_live_inputs,
            "verified_historical_input_sha256": snapshot_inputs,
            "historical_source_ref": args.source_ref,
            "binary_relative_path": binary_relative,
            "library_relative_path": library_relative if args.library is not None else None,
            "state": "PRODUCTION_BUILD_ARTIFACTS_MATCH_WITH_EXPLICIT_EXCEPTIONS" if changed_live_inputs or excluded_test_artifacts else "ALL_RECORDED_BUILD_INPUTS_AND_OUTPUTS_MATCH_LIVE_FILES",
            "execution_limit": "Build and output identities verified; probe output is an observed launch artifact, not a cryptographic execution attestation."
        }
    args.output.write_text(json.dumps(encode(report), indent=2, allow_nan=False) + "\n")
    print(json.dumps({"state": report["state"],
                      "support_upper_approximate": float(x_support["upper"]),
                      "t_enclosure_approximate": [float(t_prefix), float(t_right)],
                      "subdivisions": x_support["subdivisions"],
                      "inside_margin_approximate": float(1-witness_q)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
