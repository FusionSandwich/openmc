#!/usr/bin/env python3
"""Read-only local runtime evidence. Never execute OpenMC, ldd, SSH or transport.

DT_NEEDED, names, symbols and flags are evidence, not proof of the active ray
tracer. This collector deliberately does not auto-promote a backend to VERIFIED.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from portable_bench import Invalid, digest, need, write_new


MAX_TEXT = 262144


def inspect_elf(path):
    path = Path(path).resolve()
    need(path.is_file(), f"binary/component missing: {path}")
    result = {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size,
              "format": None, "needed": [], "build_ids": [], "dynamic_output": None,
              "notes_output": None, "inspection_errors": [], "version": None}
    with path.open("rb") as stream:
        result["format"] = "ELF" if stream.read(4) == b"\x7fELF" else "NOT_ELF"
    tool = shutil.which("readelf")
    if result["format"] != "ELF" or tool is None:
        result["inspection_errors"].append("READELF_UNAVAILABLE_OR_UNSUPPORTED_FORMAT")
        return result
    for flag, key in (("-d", "dynamic_output"), ("-n", "notes_output")):
        # Only invoke the known inspection utility, never the target binary.
        try:
            with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                process = subprocess.Popen([tool, flag, str(path)], stdout=out, stderr=err,
                                           stdin=subprocess.DEVNULL, shell=False)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    result["inspection_errors"].append(f"{flag}: TIMEOUT")
                out.seek(0); err.seek(0)
                data = out.read(MAX_TEXT + 1)
                errors = err.read(MAX_TEXT + 1)
                if len(data) > MAX_TEXT or len(errors) > MAX_TEXT:
                    result["inspection_errors"].append(f"{flag}: TEXT_TRUNCATED_NOT_COMPLETE")
                result[key] = data[:MAX_TEXT].decode("utf-8", errors="replace")
                if process.returncode:
                    result["inspection_errors"].append(f"{flag}: exit {process.returncode}: " + errors[:4096].decode(errors="replace"))
        except OSError as exc:
            result["inspection_errors"].append(str(exc))
    result["needed"] = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", result["dynamic_output"] or "")
    result["build_ids"] = re.findall(r"Build ID:\s*(\S+)", result["notes_output"] or "")
    result["name_hints_only"] = [name for name in result["needed"]
                                  if any(term in name.lower() for term in ("dagmc", "double", "embree", "moab"))]
    result["version_note"] = "ELF build-id is not a package version. Supply hash-bound build/version records."
    return result


def capture_process(pid, target_sha):
    """Inspect an explicitly identified, already running LOCAL process; no launch."""
    need(type(pid) is int and pid > 0, "PID must be positive")
    proc = Path("/proc") / str(pid)
    try:
        stat_before = (proc / "stat").read_text()
        # comm can contain spaces/parentheses; fields after the final ')' are stable.
        start_ticks = stat_before.rsplit(")", 1)[1].split()[19]
        exe = (proc / "exe").resolve(strict=True)
        exe_hash = digest(exe)
        maps = (proc / "maps").read_text()
        need(len(maps.encode()) <= MAX_TEXT, "maps exceed bounded inspection size")
        inspected, errors = [], []
        seen = set()
        for line in maps.splitlines():
            parts = line.split(None, 5)
            if len(parts) < 6 or not parts[5].startswith("/"):
                continue
            path = parts[5]
            if path in seen:
                continue
            seen.add(path)
            # Only inspect target/runtime-relevant objects; retain full maps hash.
            relevant = (path == str(exe) or any(s in path.lower() for s in ("openmc", "dagmc", "double", "embree", "moab")))
            if not relevant:
                continue
            if path.endswith(" (deleted)"):
                errors.append("DELETED_MAPPING_UNVERIFIED: " + path)
                continue
            try:
                p = Path(path)
                st = p.stat()
                major, minor = (int(x, 16) for x in parts[3].split(":"))
                need(st.st_ino == int(parts[4]) and os.major(st.st_dev) == major and os.minor(st.st_dev) == minor,
                     "mapping device/inode differs from visible path")
                inspected.append(inspect_elf(p))
            except (OSError, Invalid) as exc:
                errors.append(f"MAPPING_UNVERIFIED: {path}: {exc}")
        stat_after = (proc / "stat").read_text()
        need(start_ticks == stat_after.rsplit(")", 1)[1].split()[19], "PID changed during inspection")
        need(exe_hash == digest(proc / "exe"), "process executable changed during inspection")
        target_seen = exe_hash == target_sha or any(row["sha256"] == target_sha for row in inspected)
        return {"pid": pid, "start_ticks": start_ticks, "exe_sha256": exe_hash,
                "target_present": target_seen,
                "maps_sha256": __import__("hashlib").sha256(maps.encode()).hexdigest(),
                "objects": inspected, "errors": errors,
                "status": "LOCAL_MAPPINGS_OBSERVED" if target_seen else "TARGET_NOT_VERIFIED_IN_PROCESS",
                "limitation": "Path/inode checks cannot prove an active backend call path or exclude in-place binary changes."}
    except (OSError, Invalid, IndexError) as exc:
        return {"pid": pid, "status": "UNVERIFIED", "reason": str(exc)}


def collect(binary=None, components=(), records=(), pid=None):
    binary = binary or shutil.which("openmc")
    result = {"schema": "stellarcsg.runtime-identification/v1", "backend_status": "UNVERIFIED",
              "ordinary_dagmc": "UNVERIFIED", "double_down_embree": "UNVERIFIED",
              "scope": "LOCAL_READ_ONLY_NO_TARGET_EXECUTION", "binary": None,
              "components": [], "build_records": [], "process": None,
              "missing_evidence": ["Hash-bound source/configuration and complete dynamic dependency chain or static link map",
                                   "DAGMC, Double Down, Embree and OpenMC versions/commits tied to these binary hashes",
                                   "Reviewed active DAGMC ray-tracing backend, not just a filename or enable flag"],
              "bateman_live_linkage": "UNKNOWN_NOT_CONTACTED"}
    if binary:
        result["binary"] = inspect_elf(binary)
    else:
        result["missing_evidence"].append("OpenMC binary unavailable in this environment")
    result["components"] = [inspect_elf(p) for p in components]
    for record in records:
        record = Path(record).resolve()
        need(record.is_file() and record.stat().st_size <= MAX_TEXT, "build record missing/oversized")
        text = record.read_text(encoding="utf-8")
        interesting = [line for line in text.splitlines()
                       if any(term in line.lower() for term in ("double_down", "double-down", "embree", "dagmc", "compiler", "cxx_flags", "git_sha", "version"))]
        result["build_records"].append({"path": str(record), "sha256": digest(record),
                                        "relevant_lines": interesting,
                                        "binding_status": "UNVERIFIED_UNLESS_REVIEWED_AGAINST_BINARY"})
    if pid is not None:
        need(result["binary"] is not None, "explicit target binary required for process binding")
        result["process"] = capture_process(pid, result["binary"]["sha256"])
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path)
    p.add_argument("--component", type=Path, action="append", default=[])
    p.add_argument("--build-record", type=Path, action="append", default=[])
    p.add_argument("--pid", type=int)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = collect(a.binary, a.component, a.build_record, a.pid)
        write_new(a.output, result)
        print(json.dumps({"backend_status": result["backend_status"], "output": str(a.output)}))
        return 0
    except (OSError, Invalid, UnicodeError) as exc:
        print(f"INSPECTION_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
