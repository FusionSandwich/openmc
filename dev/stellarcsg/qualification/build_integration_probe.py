"""Bounded local native probe build; assumes recorded preflight, no acquisition."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("before", "after"))
    args = parser.parse_args()
    root = Path.cwd()
    report = root / "dev/stellarcsg/reports/openmc-integration-20260926"
    output = report / f"native-{args.stage}"
    output.mkdir(exist_ok=False)
    for name in ("prebuild-windows.json", "prebuild-wsl.json"):
        json.loads((report / name).read_text())
    source = root / "dev/stellarcsg/qualification/check_spherical_equator.cpp"
    library = root / "build/astra-native/lib/libopenmc.so"
    binary = root / "build/astra-native/bin/stellarcsg_spherical_equator_probe"
    sibling = root.parent / "openmc-stellarcsg"
    paths = [source, root / "src/mesh.cpp", root / "include/openmc/mesh.h",
             root / "build/astra-native/CMakeCache.txt", root / "build/astra-native/build.ninja"]
    before = {str(p): sha(p) for p in paths}
    old_library = sha(library)
    if args.stage == "before":
        shutil.copyfile(library, output / "libopenmc.so")
        shutil.copyfile(root / "build/astra-native/bin/openmc", output / "openmc.bin")
    resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024**2,) * 2)
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               GIT_DIR=str(sibling / ".git/worktrees" / root.name), GIT_WORK_TREE=str(root))
    commands = []
    if args.stage == "after":
        commands.append(["cmake", "--build", "build/astra-native", "--parallel", "1", "--target", "openmc"])
    commands.append(["g++", "-std=c++17", "-O2", "-fno-fast-math", "-Iinclude",
        "-Ibuild/astra-native/include", "-I/usr/include/hdf5/serial",
        f"-I{sibling}/vendor/fmt/include", f"-I{sibling}/vendor/pugixml/src",
        str(source), str(library), str(sibling / "build/openmc-stellarcsg-enabled/lib/libfmt.a"),
        str(sibling / "build/openmc-stellarcsg-enabled/lib/libpugixml.a"),
        f"-Wl,-rpath,{library.parent}", "-o", str(binary)])
    observed = []
    for index, command in enumerate(commands):
        started = time.time()
        with (output / f"command-{index}.txt").open("x") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    env=env, timeout=240)
        observed.append(dict(command=command, exit_code=result.returncode, seconds=time.time()-started))
        if result.returncode:
            raise RuntimeError("build failed; see preserved command log")
    test = subprocess.run([str(binary)], capture_output=True, text=True, env=env, timeout=30)
    (output / "probe.txt").write_text(test.stdout + test.stderr)
    after = {str(p): sha(p) for p in paths}
    if before != after:
        raise RuntimeError("build inputs changed")
    result = dict(stage=args.stage, inputs_before=before, inputs_after=after,
        old_library_sha256=old_library, new_library_sha256=sha(library),
        executable_sha256=sha(root / "build/astra-native/bin/openmc"),
        python_library_sha256=sha(root / "openmc/lib/libopenmc.so"),
        probe_sha256=sha(binary), commands=observed, test_exit_code=test.returncode,
        acquisition_bytes=0, parallel_jobs=1, memory_cap_bytes=1536*1024**2)
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if args.stage == "after" and test.returncode:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
