#!/usr/bin/env python3
"""Deterministic *synthetic timing* child with exact, deliberately limited fixtures."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from analytic_fixture import solve
from portable_bench import COUNTERS, load_bank, query_hash, read_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bank", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--repeat", type=int, default=0)
    p.add_argument("--mode", choices=["primary", "diagnostic"], default="primary")
    p.add_argument("--scale", type=float, default=1)
    p.add_argument("--fault", default="none")
    a = p.parse_args()
    if a.fault == "spawn_grandchild":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
        Path("descendant.pid").write_text(str(child.pid))
    if a.fault == "timeout":
        time.sleep(10)
    if a.fault == "signal":
        os.kill(os.getpid(), signal.SIGTERM)
    if a.fault == "flood":
        while True:
            sys.stdout.write("x" * 4096)
            sys.stdout.flush()
    model = read_json(a.model)
    bank = load_bank(a.bank, {name: model["domain"] for name in model["geometries"]})
    rows = []
    for i, q in enumerate(bank):
        outcome, distance, reason = solve(q, model)
        ns = (i + 1) * 10 * a.scale * (1 + a.repeat / 10)
        counters = {key: None for key in COUNTERS}
        recovery_ns, fallback_ns = None, None
        if a.mode == "diagnostic":
            counters.update(candidate_count=i + 1, newton_iterations=i + 2,
                            recovery_calls=int(i % 3 == 0), fallback_calls=int(i == len(bank) - 1),
                            allocations=0, allocated_bytes=0)
            recovery_ns = ns * .2 if counters["recovery_calls"] else 0
            fallback_ns = ns * .5 if counters["fallback_calls"] else 0
        normal_point = q["origin"][:]
        if outcome == "HIT":
            norm = math.sqrt(sum(x*x for x in q["direction"]))
            normal_point = [o + distance * d / norm for o, d in zip(q["origin"], q["direction"])]
        r = {"kind": "query", "id": q["id"], "input_sha256": query_hash(q),
             "candidate": {"state": "BLOCKED" if outcome == "UNRESOLVED" else "PASS",
                           "result": outcome, "distance_cm": distance, "reason": reason},
             "reference": {"strength": "sampled", "state": "SKIPPED", "reason": None},
             "timing_ns": {"distance": ns, "classification": ns / 2, "normal": ns * 1.5},
             # Dedicated unique point banks, not repeated origins or candidate-dependent hits.
             # These points and their timings are synthetic telemetry test data.
             "points": {"classification": [i + .125, .25, .375],
                        "normal": [0, i, 0] if q["geometry"] == "slab" else
                                  [(1-i*i)/(1+i*i), 2*i/(1+i*i), 0]},
             "counters": counters, "recovery_ns": recovery_ns, "fallback_ns": fallback_ns,
             "telemetry_blocked": False}
        if i == 0:
            if a.fault == "blocked":
                r["candidate"] = {"state": "BLOCKED", "result": "UNRESOLVED", "distance_cm": None,
                                  "reason": "EARLIER_PREFIX_UNRESOLVED_TEST_FIXTURE"}
                r["timing_ns"]["distance"] = None
            elif a.fault == "fail":
                r["candidate"]["state"] = "FAIL"
                r["candidate"]["reason"] = "DELIBERATE_FIXTURE_FAILURE"
            elif a.fault == "wrong_result":
                r["candidate"].update(result="MISS", distance_cm=None)
            elif a.fault == "negative_time":
                r["timing_ns"]["distance"] = -1
            elif a.fault == "null_timing":
                r["timing_ns"]["distance"] = None
            elif a.fault == "counter_primary":
                r["counters"]["newton_iterations"] = 3
            elif a.fault == "telemetry_blocked":
                r["telemetry_blocked"] = True
            elif a.fault == "reference_blocked":
                r["reference"].update(state="BLOCKED", reason="REFERENCE_GEOMETRY_ADMISSION_BLOCKED")
            elif a.fault == "reference_disagreement":
                r["reference"].update(state="DISAGREE")
        rows.append(r)
    summary = {"kind": "summary", "query_count": len(bank),
               "candidate_failures": sum(r["candidate"]["state"] == "FAIL" for r in rows),
               "blocked": sum(r["candidate"]["state"] == "BLOCKED" for r in rows),
               "reference_disagreements": sum(r["reference"]["state"] == "DISAGREE" for r in rows),
               "setup_ns": 1000, "warmup_ns": 0, "warmup_queries": 0,
               "peak_rss_bytes": None, "cache_policy": "unique_queries_fresh_process",
               "mode": a.mode, "timing_origin": "synthetic"}
    if a.fault == "wrong_summary":
        summary["query_count"] += 1
    if a.fault == "missing_record":
        rows.pop()
    if a.fault == "duplicate_id":
        rows[-1] = rows[0]
    if a.fault == "malformed":
        print('{"kind":"query", BROKEN')
    elif a.fault == "nan":
        print('{"bad":NaN}')
    else:
        for row in rows + [summary]:
            print(json.dumps(row, allow_nan=False))
    if a.fault == "mutate_input":
        a.bank.write_text(a.bank.read_text() + "\n")
    return 7 if a.fault == "exit7" else 0


if __name__ == "__main__":
    sys.exit(main())
