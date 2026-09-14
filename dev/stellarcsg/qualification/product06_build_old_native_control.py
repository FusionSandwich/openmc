#!/usr/bin/env python3
"""Plan or build a relinked old-native control without modifying its source tree.

The only compilation unit replaced is ``compiled_swept_surface.cpp``.  The
default is plan-only; ``--execute`` is deliberately required to compile/link.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_path(build: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (build / path).resolve()


def command_path(directory: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (directory / path).resolve()


def command_tokens(entry: dict[str, object]) -> list[str]:
    if "arguments" in entry:
        return [str(value) for value in entry["arguments"]]
    if "command" in entry:
        return shlex.split(str(entry["command"]))
    raise ValueError("compile_commands entry lacks command and arguments")


def replace_compile_command(build: Path, old_source: Path, new_object: Path) -> tuple[list[str], Path]:
    database = json.loads((build / "compile_commands.json").read_text())
    matches = [entry for entry in database if Path(str(entry["file"])).name == "compiled_swept_surface.cpp"]
    if len(matches) != 1:
        raise ValueError("expected exactly one compiled_swept_surface.cpp compile_commands entry")
    entry = matches[0]
    database_source = command_path(Path(str(entry.get("directory", build))), str(entry["file"]))
    tokens = command_tokens(entry)
    if tokens.count("-c") != 1 or "-o" not in tokens:
        raise ValueError("compile command must have one -c and an -o")
    compile_index, output_index = tokens.index("-c"), tokens.index("-o")
    if compile_index + 1 >= len(tokens) or output_index + 1 >= len(tokens):
        raise ValueError("truncated compile command")
    compiled_source = command_path(Path(str(entry.get("directory", build))), tokens[compile_index + 1])
    if compiled_source != database_source:
        raise ValueError("compile command -c source does not match its compile_commands file")
    original_object = build_path(build, tokens[output_index + 1])
    tokens[compile_index + 1] = str(old_source.resolve())
    tokens[output_index + 1] = str(new_object)
    return tokens, original_object


def link_tokens(build: Path, original_object: Path, replacement_object: Path, output_library: Path) -> list[str]:
    probe = subprocess.run(["ninja", "-t", "commands", "-s", "lib/libopenmc.so"], cwd=build, text=True, capture_output=True, check=False)
    if probe.returncode != 0:
        raise RuntimeError(f"ninja command query failed: {probe.stderr.strip()}")
    candidates: list[list[str]] = []
    for line in probe.stdout.splitlines():
        tokens = shlex.split(line)
        if len(tokens) < 7 or tokens[:2] != [":", "&&"] or tokens[-2:] != ["&&", ":"] or tokens.count("&&") != 2:
            continue
        body = tokens[2:-2]
        if not body or body[0].startswith("-") or body.count("-o") != 1:
            continue
        output_index = body.index("-o")
        if output_index + 1 < len(body) and body[output_index + 1] == "lib/libopenmc.so":
            candidates.append(tokens)
    if len(candidates) != 1:
        raise ValueError("expected one final lib/libopenmc.so linker command after ninja -t commands -s")
    tokens = candidates[0]
    body = tokens[2:-2]
    output_index = body.index("-o")
    object_matches = [index for index, token in enumerate(body) if build_path(build, token) == original_object.resolve()]
    if len(object_matches) != 1:
        raise ValueError("expected the compiled swept object exactly once in shared-library link command")
    body[object_matches[0]] = str(replacement_object)
    body[output_index + 1] = str(output_library)
    return [":", "&&", *body, "&&", ":"]


def existing_executable(build: Path) -> Path:
    candidates = [build / "openmc", build / "bin/openmc"]
    found = [path for path in candidates if path.is_file()]
    if len(found) != 1:
        raise ValueError("expected one recovered OpenMC executable at build/openmc or build/bin/openmc")
    return found[0]


def ldd_binding(executable: Path, library: Path) -> dict[str, object]:
    environment = {"LD_LIBRARY_PATH": str(library.parent)}
    probe = subprocess.run(["ldd", str(executable)], env=environment, text=True, capture_output=True, check=False)
    if probe.returncode != 0:
        raise RuntimeError("ldd failed for copied control executable")
    matches = [line for line in probe.stdout.splitlines() if "libopenmc.so" in line]
    if len(matches) != 1 or str(library.resolve()) not in matches[0]:
        raise RuntimeError("LD_LIBRARY_PATH did not resolve the rebuilt old-native control library")
    return {"ldd": probe.stdout, "resolved_library": str(library.resolve())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--old-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="compile and relink after reviewing the plan")
    args = parser.parse_args()
    build, old_source, output = args.build.resolve(), args.old_source.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError("output must be a new control directory")
    if old_source.name != "compiled_swept_surface.cpp" or not old_source.is_file():
        raise ValueError("--old-source must name the preserved compiled_swept_surface.cpp")
    output.mkdir(parents=True)
    new_object, new_library = output / "compiled_swept_surface_old.o", output / "libopenmc.so"
    compile, original_object = replace_compile_command(build, old_source, new_object)
    link = link_tokens(build, original_object, new_object, new_library)
    base_library = build / "lib/libopenmc.so"
    if not base_library.is_file() or not original_object.is_file():
        raise ValueError("base library or original swept object is absent")
    base_objects = [build_path(build, token) for token in link[2:-2] if token.endswith((".o", ".obj")) and build_path(build, token).is_file()]
    receipt: dict[str, object] = {
        "schema": "stellarcsg.product06.old-native-control/v1", "mode": "EXECUTE" if args.execute else "PLAN_ONLY",
        "source": {"path": str(old_source), "sha256": sha256(old_source)},
        "base": {"library": str(base_library), "library_sha256": sha256(base_library), "replaced_object": str(original_object), "replaced_object_sha256": sha256(original_object),
                 "link_object_sha256": {str(path): sha256(path) for path in base_objects}},
        "compile_command": compile, "link_command": link,
        "output": {"object": str(new_object), "library": str(new_library)},
        "claim_boundary": "This control reuses completed native-build objects and changes only one preserved source object. It does not execute transport or qualify either lane.",
    }
    if args.execute:
        subprocess.run(compile, cwd=build, check=True)
        subprocess.run(link[2:-2], cwd=build, check=True)
        executable = output / "openmc"
        shutil.copy2(existing_executable(build), executable)
        receipt["output"].update(object_sha256=sha256(new_object), library_sha256=sha256(new_library), executable=str(executable), executable_sha256=sha256(executable), loader=ldd_binding(executable, new_library))
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"mode": receipt["mode"], "receipt": str(output / "receipt.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
