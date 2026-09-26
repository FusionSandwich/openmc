"""Bounded local incremental build with before/after provenance."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    root = Path.cwd()
    report = root / "dev/stellarcsg/reports/transport-proxy-20260926"
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    output = report / parser.parse_args().run
    output.mkdir(exist_ok=False)
    paths = [
        "src/surface_swept_spline.cpp", "src/surface_periodic_spline.cpp",
        "include/openmc/surface_swept_spline.h", "openmc/surface.py",
        "dev/stellarcsg/src/compiled_periodic_surface.cpp",
        "dev/stellarcsg/src/uniform_periodic_bicubic_spline.cpp",
        "dev/stellarcsg/src/certified_spline_offset.cpp",
        "dev/stellarcsg/include/stellarcsg/root_solver.hpp",
        "dev/stellarcsg/tests/test_compiled_surface.cpp",
        "dev/stellarcsg/tests/test_certified_offset.cpp",
        "CMakeLists.txt", "dev/stellarcsg/CMakeLists.txt",
        "build/astra/CMakeCache.txt", "build/astra/build.ninja",
        "build/astra-native/CMakeCache.txt", "build/astra-native/build.ninja",
    ]
    before = {p: sha(p) for p in paths}
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024**2,) * 2)
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    env["GIT_DIR"] = str(root.parent / "openmc-stellarcsg/.git/worktrees"
                        / root.name)
    env["GIT_WORK_TREE"] = str(root)
    runs = []
    for build, targets in [
        ("astra", ["stellarcsg_offset_tests", "stellarcsg_compiled_surface_tests",
                   "stellarcsg_recovery04_bank"]),
        ("astra-native", ["openmc", "stellarcsg_native_offset_probe"]),
    ]:
        cmd = ["cmake", "--build", f"build/{build}", "--parallel", "1",
               "--target", *targets]
        started = time.time()
        with (output / f"{build}.log").open("w") as log:
            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                    env=env, timeout=240)
        runs.append(dict(command=cmd, exit_code=result.returncode,
                         seconds=time.time() - started))
        if result.returncode:
            break
    after = {p: sha(p) for p in paths}
    binaries = [
        "build/astra/stellarcsg_offset_tests",
        "build/astra/stellarcsg_compiled_surface_tests",
        "build/astra/stellarcsg_recovery04_bank",
        "build/astra-native/bin/openmc",
        "build/astra-native/lib/libopenmc.so",
        "build/astra-native/bin/stellarcsg_native_offset_probe",
    ]
    receipt = dict(inputs_before=before, inputs_after=after,
                   changed_inputs=[p for p in paths if before[p] != after[p]],
                   outputs={p: sha(p) for p in binaries if Path(p).exists()},
                   builds=runs, acquisition_bytes=0, parallel_jobs=1,
                   memory_limit_bytes=1536 * 1024**2)
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if any(r["exit_code"] for r in runs) or receipt["changed_inputs"]:
        raise SystemExit("Build failed or inputs changed; inspect receipt.")
    print(json.dumps(dict(state="BUILT", outputs=receipt["outputs"])))


if __name__ == "__main__":
    main()
