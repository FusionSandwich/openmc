"""Execute the fixed, bounded proxy test matrix sequentially; stop on failure."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "dev/stellarcsg/reports/transport-proxy-20260926"
HARNESS = ROOT / "dev/stellarcsg/qualification/proxy_transport.py"


def main():
    plan = []
    for family, orders, particles in (
        ("plasma", [("native", "spline"), ("spline", "native"),
                    ("native", "spline")], 1000),
        ("coil", [("native", "spline", "ordered", "annulus"),
                  ("annulus", "ordered", "spline", "native"),
                  ("spline", "native", "annulus", "ordered")], 10),
    ):
        for seed, variants in zip((1741, 2741, 3741), orders):
            for variant in variants:
                plan.append(dict(family=family, variant=variant, seed=seed,
                                 particles=particles, batches=20))
    manifest = REPORT / "campaign-plan.json"
    with manifest.open("x") as f:
        json.dump(dict(plan=plan, per_child_timeout_s=180, max_processes=1,
                       acquisition_bytes=0), f, indent=2)
    harness_hash = hashlib.sha256(HARNESS.read_bytes()).hexdigest()
    env = dict(os.environ, PYTHONPATH=f"{ROOT}:{ROOT / 'dev/stellarcsg/python'}",
               OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    observations = []
    for item in plan:
        if hashlib.sha256(HARNESS.read_bytes()).hexdigest() != harness_hash:
            raise RuntimeError("harness changed during campaign")
        output = REPORT / f"{item['family']}-{item['variant']}-{item['seed']}"
        command = [sys.executable, str(HARNESS), "--fixtures", str(REPORT / "fixtures"),
                   "--output", str(output), "--timeout", "180"]
        for key, value in item.items():
            command.extend((f"--{key}", str(value)))
        started = time.time()
        result = subprocess.run(command, env=env, timeout=210)
        observations.append(dict(item, exit_code=result.returncode,
                                 wrapper_seconds=time.time() - started))
        (REPORT / "campaign-progress.json").write_text(
            json.dumps(dict(planned=len(plan), observations=observations), indent=2) + "\n")
        if result.returncode:
            raise SystemExit("Stopped after failed observation; inspect its artifacts.")
    print(json.dumps(dict(state="CAMPAIGN_EXECUTED", runs=len(observations))))


if __name__ == "__main__":
    main()
