"""Finite six-case compatibility campaign, one bounded local child at a time."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "dev/stellarcsg/reports/openmc-integration-20260926"
WORKER = Path(__file__).with_name("check_openmc_integration.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--library-sha256", default="7fa3dbf5bef055aa2227842800e54a2daa84537a1ba6730e97f4fb6cd25d317e")
    args = parser.parse_args()
    report = args.report.resolve()
    report.mkdir(parents=True, exist_ok=True)
    plan = [("plasma", variant, source) for source in ("mesh", "box")
            for variant in ("native", "spline")]
    plan += [("coil", variant, "file") for variant in ("native", "spline")]
    worker_hash = sha(WORKER)
    with (report / "campaign-plan.json").open("x") as handle:
        json.dump(dict(plan=plan, worker_sha256=worker_hash, timeout_s=180,
                       memory_cap_bytes=2 * 1024**3, threads=1,
                       library_sha256=args.library_sha256), handle, indent=2)
    rows = []
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               OPENMC_CROSS_SECTIONS="/mnt/c/Users/joshu/Documents/2026_DPA/openc-hts-dpa/.data/openmc/cross_sections.xml")

    def cap():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)

    for family, variant, source in plan:
        if sha(WORKER) != worker_hash:
            raise ValueError("worker changed during campaign")
        name = f"{family}-{variant}-{source}"
        output = report / name
        command = [sys.executable, str(WORKER), "--family", family, "--variant", variant,
                   "--source", source, "--output", str(output),
                   "--library-sha256", args.library_sha256]
        started = time.time()
        timeout = False
        with (report / f"{name}.txt").open("x") as log:
            try:
                child = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                       cwd=ROOT, env=env, preexec_fn=cap, timeout=180)
                code = child.returncode
            except subprocess.TimeoutExpired:
                timeout, code = True, None
        diagnostics = (report / f"{name}.txt").read_text().lower()
        failures = [token for token in ("lost particle", "could not be located",
                    "unresolved", "traceback", "error:", "terminate called") if token in diagnostics]
        receipt = output / "receipt.json"
        row = dict(name=name, command=command, start_unix=started,
                   seconds=time.time() - started, exit_code=code, timed_out=timeout,
                   failures=failures, receipt_sha256=sha(receipt) if receipt.is_file() else None,
                   log_sha256=sha(report / f"{name}.txt"))
        rows.append(row)
        (report / "campaign-progress.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps(row), flush=True)
        if code != 0 or failures or timeout or not receipt.is_file():
            raise SystemExit(1)


if __name__ == "__main__":
    main()
