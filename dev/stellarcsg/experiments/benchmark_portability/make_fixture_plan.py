#!/usr/bin/env python3
"""Create a new, relocatable example with fully hash-bound local Python fixtures."""
import argparse
from pathlib import Path
import shutil

from analytic_fixture import fixture_data
from portable_bench import SCHEMA, digest, write_new


def make_plan(output, *, repetitions=3, mode="primary", fault="none", lanes=3):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    model, bank = fixture_data()
    write_new(output / "model.json", model)
    write_new(output / "bank.json", bank)
    source = Path(__file__).resolve().parent
    for name in ("portable_bench", "analytic_fixture", "mock_child"):
        with (output / (name + ".py")).open("xb") as stream:
            stream.write((source / (name + ".py")).read_bytes())
    files = {p.stem: {"path": p.name, "sha256": digest(p)} for p in output.iterdir() if p.is_file()}
    plan = {"schema": SCHEMA, "mode": mode, "timing_origin": "synthetic", "repetitions": repetitions,
            "timeout_s": 3, "max_log_bytes": 65536, "artifacts": files, "lanes": []}
    for name, role, scale, authority in [
        ("candidate", "candidate", 2, "implementation"),
        ("old_fast_mock", "old_fast", 1, "implementation"),
        ("exact_reference_fixture", "reference", 3, "analytic_exact")][:lanes]:
        plan["lanes"].append({"name": name, "role": role,
            "command": ["{python}", "{mock_child}", "--bank", "{bank}", "--model", "{model}",
                        "--repeat", "{repeat}", "--mode", mode, "--scale", str(scale), "--fault", fault],
            "bank": "bank", "model": "model", "parser": "portable_v1",
            "geometry_domains": {name: model["domain"] for name in model["geometries"]},
            "query_class": "exact-rational-fixture-rays/v1", "implementation": "mock",
            "authority": authority,
            "authority_evidence": "analytic_fixture.py: restricted exact rational fixtures only; synthetic timings, not a native OpenMC oracle",
            "compiler": None, "native_provenance": None})
    write_new(output / "plan.json", plan)
    return output / "plan.json"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--repetitions", type=int, default=3)
    p.add_argument("--mode", choices=["primary", "diagnostic"], default="primary")
    p.add_argument("--fault", default="none")
    a = p.parse_args()
    print(make_plan(a.output, repetitions=a.repetitions, mode=a.mode, fault=a.fault))
