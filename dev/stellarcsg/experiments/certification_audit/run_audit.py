#!/usr/bin/env python3
"""Offline, bounded audit runner. Does not install, download, or run transport.

Run from a pinned checkout or the supplied two-header snapshot. All generated
files are placed in a NEW output directory. A successful witness means the
observed defect/proof limitation reproduced, not that any solver is qualified.
Linux and existing g++ / clang++ are required for the complete C++ checks.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PIN = "c08eea92ca3fb63eb8adbf44cfb4ea8612639e30"
BLOBS = {
    "dev/stellarcsg/include/stellarcsg/vector.hpp":
        "af3fc2b8a86f6945adeb27b4f46157e172137349",
    "dev/stellarcsg/src/swept_span_bounds.hpp":
        "2c576398257a7e1f118fa99b99e55d92c4003bc9",
}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def limits():
    # Each compiler/test child: one inherited allowed CPU; no large outputs.
    resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
    resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 2**20, 16 * 2**20))


def execute(command, *, timeout=12, env=None, bounded=False):
    result = {"command": [str(x) for x in command]}
    try:
        process = subprocess.run(result["command"], text=True, capture_output=True,
            timeout=timeout, env=env, preexec_fn=limits if bounded else None)
        result.update(returncode=process.returncode, stdout=process.stdout,
                      stderr=process.stderr)
    except (subprocess.TimeoutExpired, OSError) as error:
        result.update(returncode=None, error=str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=HERE.parents[3])
    args = parser.parse_args()
    source = args.source_root.resolve()
    out = args.output.resolve()
    cgroup_lines = Path("/proc/self/cgroup").read_text().splitlines()
    unified = [line.split(":", 2)[2] for line in cgroup_lines
               if line.startswith("0::")]
    cgroup = (Path("/sys/fs/cgroup") / unified[0].lstrip("/")).resolve() if len(unified) == 1 else None
    if out.exists():
        parser.error("Output must be a new directory; prior evidence is never overwritten.")
    out.mkdir(parents=True)
    before = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "pinned_commit": PIN,
        "source_root": str(source), "output": str(out),
        "source_scope": "two expected pinned headers, not a full upstream checkout verification",
        "python": sys.version, "python_executable": sys.executable,
        "python_prefix": sys.prefix,
        "planned_new_acquisition_bytes": 0,
        "planned_build_cap_bytes": 16*2**20,
        "planned_artifacts_cap_bytes": 8*2**20,
        "rollback": "Remove only this newly created output directory.",
        "selected_environment": {k: os.environ.get(k) for k in
            ("VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "OPENMC_CROSS_SECTIONS")},
    }
    commands = {
        "ram_limits": ["bash", "-c", "free -b; cat " + " ".join(str(cgroup / name) for name in
            ("memory.max", "memory.current", "cpu.max"))] if cgroup else ["false"],
        "disk": ["df", "-B1", "/", str(source), str(out), "/tmp"],
        "processes": ["bash", "-c", "ps -eo pid,ppid,pcpu,pmem,rss,comm --sort=-rss | head -18"],
        "cpu": ["bash", "-c", "lscpu | head -30"],
        "versions": ["bash", "-c", "for t in bash git python gcc g++ clang clang++ cmake make ninja pkg-config taskset conda mamba micromamba openmc; do if command -v \"$t\"; then \"$t\" --version 2>&1 | head -2; else echo \"$t MISSING\"; fi; done"],
        "environments_checkouts": ["bash", "-c", "for p in /mnt/data /home/oai /opt /tmp /workspace /workspaces; do if [ -d \"$p\" ]; then find \"$p\" -maxdepth 3 \\( -name .git -o -name conda-meta -o -name pyvenv.cfg -o -name envs -o -name openmc -o -name stellarcsg \\) -print 2>/dev/null; fi; done"],
        "caches": ["bash", "-c", "for p in /home/oai/.cache /root/.cache /opt/conda/pkgs /opt/conda/envs /tmp; do if [ -e \"$p\" ]; then du -sh \"$p\"; else echo \"$p absent\"; fi; done"],
    }
    for name, command in commands.items():
        before[name] = execute(command)
    blockers = [name for name in commands if before[name]["returncode"] != 0]
    if not hasattr(os, "sched_getaffinity"):
        blockers.append("single-CPU affinity capability unavailable")
    else:
        before["available_cpu_affinity"] = sorted(os.sched_getaffinity(0))
        cpu = before["available_cpu_affinity"][0]
        os.sched_setaffinity(0, {cpu})
        before["execution_cpu_affinity"] = sorted(os.sched_getaffinity(0))
    before["cgroup_path"] = str(cgroup) if cgroup else None
    for name in ("memory.max", "memory.current", "cpu.max"):
        try:
            if cgroup is None or not cgroup.is_relative_to("/sys/fs/cgroup"):
                raise OSError("unified cgroup path unavailable")
            before["cgroup_" + name] = (cgroup / name).read_text().strip()
        except OSError as error:
            blockers.append(f"unknown required cgroup observation {name}: {error}")
    for path in (Path("/"), source, out, Path("/tmp")):
        usage = shutil.disk_usage(path)
        if usage.free < 64*2**20:
            blockers.append(f"less than 64 MiB free: {path}")
    try:
        limit = before["cgroup_memory.max"]
        used = int(before["cgroup_memory.current"])
        if limit != "max" and int(limit)-used < 768*2**20:
            blockers.append("less than 768 MiB cgroup RAM headroom")
    except (KeyError, ValueError):
        blockers.append("RAM headroom unknown")
    hashes = []
    for path, expected in BLOBS.items():
        local = source / path
        try:
            data = local.read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            hashes.append({"path": path, "bytes": len(data), "git_blob_sha1": blob,
                "expected_git_blob_sha1": expected, "sha256": digest(local)})
            if blob != expected:
                blockers.append(f"pinned header hash mismatch: {path}")
        except OSError as error:
            blockers.append(f"missing pinned header: {error}")
    before["verified_header_hashes"] = hashes
    before["blockers"] = blockers
    save(out / "preflight.json", before)
    if blockers:
        print(json.dumps({"status": "BLOCKED_BEFORE_BUILD", "reasons": blockers}, indent=2))
        return 2
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        env[key] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    results = {"purpose": "proof-boundary witnesses, NOT solver qualification",
        "pinned_commit": PIN, "execution_cpu_affinity": sorted(os.sched_getaffinity(0)),
        "thread_settings": {k: env[k] for k in
            ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
        "headers": hashes, "commands": [], "performance": {
            "native_openmc_ztorus": "UNAVAILABLE; no runtime acquired or built",
            "distance_ns_per_query": None, "classification_ns_per_query": None,
            "normal_ns_per_query": None, "transport_histories_per_second": None,
            "candidate_distance_over_ztorus": None,
            "candidate_classification_over_ztorus": None,
            "candidate_normal_over_ztorus": None,
            "candidate_throughput_over_ztorus": None,
            "candidate_over_old_fast": None, "repeated_run_variability": None,
            "status": "INCOMPLETE_NOT_MEASURED"}}
    analytical = execute([sys.executable, HERE / "audit.py", "--output", out / "analytic-results.json"],
                         timeout=20, env=env, bounded=True)
    results["commands"].append(analytical)
    failed = analytical["returncode"] != 0
    if not failed:
        results["analytic_case_count"] = json.loads((out / "analytic-results.json").read_text())["case_count"]
    for compiler in ("g++", "clang++"):
        executable = shutil.which(compiler)
        if executable is None:
            results["commands"].append({"compiler": compiler, "status": "BLOCKED_COMPILER_MISSING"})
            failed = True
            continue
        label = "gcc" if compiler == "g++" else "clang"
        binary = out / ("probe-" + label)
        command = [executable, "-std=c++17", "-O2", "-fno-fast-math", "-ffp-contract=off",
                   "-Wall", "-Wextra", "-pedantic", "-I" + str(source / "dev/stellarcsg/include"),
                   "-I" + str(source / "dev/stellarcsg/src"),
                   HERE / "probe_bounds.cpp", "-o", binary]
        built = execute(command, timeout=30, env=env, bounded=True)
        built["compiler_version"] = execute([executable, "--version"])
        results["commands"].append(built)
        if built["returncode"] != 0:
            failed = True
            continue
        checked = execute([binary], timeout=5, env=env, bounded=True)
        checked["binary_sha256"] = digest(binary)
        results["commands"].append(checked)
        (out / ("probe-" + label + ".jsonl")).write_text(checked.get("stdout", ""))
        failed = failed or checked["returncode"] != 0
    results["status"] = "AUDIT_WITNESSES_REPRODUCED_NOT_SOLVER_PASS" if not failed else "INCOMPLETE_OR_FAILED"
    results["full_kernel_executed"] = False
    results["input_sha256"] = {p.name: digest(p) for p in
        (HERE / "audit.py", HERE / "probe_bounds.cpp", HERE / "retained_shape2_controls.json", Path(__file__))}
    save(out / "results.json", results)
    print(json.dumps({"status": results["status"], "analytic_case_count": results.get("analytic_case_count"),
                      "full_kernel_executed": False, "output": str(out)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
