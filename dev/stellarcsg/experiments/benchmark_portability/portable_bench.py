#!/usr/bin/env python3
"""Opt-in, stdlib-only geometry-query runner and independently replayable receipts.

This is measurement plumbing, not a root certificate or transport launcher.
All numeric timing claims in the distributed example are synthetic.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import uuid

SCHEMA = "stellarcsg.portable-benchmark/v1"
PIN = "c08eea92ca3fb63eb8adbf44cfb4ea8612639e30"
METRICS = ("distance", "classification", "normal")
COUNTERS = ("candidate_count", "newton_iterations", "recovery_calls",
            "fallback_calls", "allocations", "allocated_bytes")
THREAD_ENV = {k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                              "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
                              "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")}
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
MAX_INPUT = 2 * 1024 * 1024


class Invalid(ValueError):
    """An input, log or receipt violates its explicit contract."""


def need(condition, message):
    if not condition:
        raise Invalid(message)


def fields(value, required, optional=(), label="object"):
    need(isinstance(value, dict), f"{label}: expected object")
    need(set(required) <= value.keys(), f"{label}: missing {set(required) - value.keys()}")
    need(value.keys() <= set(required) | set(optional),
         f"{label}: unknown keys {value.keys() - set(required) - set(optional)}")


def number(value, label, *, nullable=False, integer=False, minimum=0):
    if value is None and nullable:
        return None
    need(type(value) in ((int,) if integer else (int, float)), f"{label}: invalid number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    need(finite and value >= minimum, f"{label}: nonfinite or below {minimum}")
    return value


def reject_constant(value):
    raise Invalid(f"nonstandard JSON constant: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_loads(text):
    try:
        value = json.loads(text, parse_constant=reject_constant,
                           object_pairs_hook=unique_object)
    except (ValueError, RecursionError) as exc:
        raise Invalid(f"invalid JSON: {exc}") from exc

    def walk(x):
        if isinstance(x, float):
            need(math.isfinite(x), "nonfinite JSON number")
        elif isinstance(x, dict):
            for child in x.values():
                walk(child)
        elif isinstance(x, list):
            for child in x:
                walk(child)
    walk(value)
    return value


def read_json(path, limit=MAX_INPUT):
    need(path.is_file() and path.stat().st_size <= limit,
         f"missing or oversized JSON: {path}")
    return strict_loads(path.read_text(encoding="utf-8"))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def object_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_new(path, value):
    """Create an immutable journal/receipt entry; never replace a previous run."""
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def vector(value, label):
    need(isinstance(value, list) and len(value) == 3, f"{label}: expected length 3")
    return [float(number(x, label, minimum=-sys.float_info.max)) for x in value]


def query_key(q):
    # IDs, categories and heldout labels cannot disguise a repeated input.
    # float conversion canonicalizes 1/1.0 and equality canonicalizes -0.0/0.0.
    return (q["geometry"], q["coincident"],
            *[0.0 if x == 0 else x for x in q["origin"] + q["direction"]])


def query_hash(q):
    return object_hash(query_key(q))


def load_bank(path, geometry_domains):
    """Read a canonical JSON bank or the frozen recovery04 CSV, without rewriting it."""
    need(path.is_file() and path.stat().st_size <= MAX_INPUT, "bank missing/oversized")
    if path.suffix.lower() == ".csv":
        rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
        queries = []
        for r in rows:
            need(None not in r, "CSV: excess columns")
            need(all(k in r for k in ("id", "geometry", "category", "ox", "oy", "oz",
                                     "dx", "dy", "dz")), "CSV: missing columns")
            try:
                q = {"id": r["id"], "geometry": r["geometry"], "category": r["category"],
                     "origin": [float(r[k]) for k in ("ox", "oy", "oz")],
                     "direction": [float(r[k]) for k in ("dx", "dy", "dz")],
                     "coincident": r["category"].startswith("coincident_"), "expected": None}
            except (ValueError, TypeError) as exc:
                raise Invalid("CSV: invalid coordinate") from exc
            # Preserve declared metadata for later log binding. FNV is NOT SHA256.
            q["legacy"] = {k: r.get(k) for k in
                           ("coefficient_hash", "source_sha256", "expected", "heldout")}
            queries.append(q)
    else:
        bank = read_json(path)
        fields(bank, ("schema", "queries"), label="bank")
        need(bank["schema"] == "stellarcsg.query-bank/v1", "unknown bank schema")
        queries = bank["queries"]
    need(isinstance(queries, list) and 0 < len(queries) <= 100000, "empty/oversized bank")
    ids, keys = set(), set()
    for q in queries:
        fields(q, ("id", "geometry", "category", "origin", "direction", "coincident", "expected"),
               ("legacy",), "query")
        need(isinstance(q["id"], str) and NAME.fullmatch(q["id"]), "invalid query id")
        need(q["id"] not in ids, "duplicate query id")
        need(isinstance(q["geometry"], str) and q["geometry"] in geometry_domains,
             "query outside declared geometry domains")
        need(isinstance(q["category"], str) and q["category"], "empty query category")
        need(type(q["coincident"]) is bool, "coincident must be boolean")
        q["origin"] = vector(q["origin"], "origin")
        q["direction"] = vector(q["direction"], "direction")
        need(any(x != 0 for x in q["direction"]), "zero direction")
        key = query_key(q)
        need(key not in keys, "duplicate numeric query input tuple")
        if q["expected"] is not None:
            e = q["expected"]
            fields(e, ("result", "distance_cm", "provenance"), label="expectation")
            need(e["result"] in ("HIT", "MISS", "UNRESOLVED"), "bad expected result")
            need(isinstance(e["provenance"], str) and e["provenance"], "missing expectation provenance")
            if e["result"] == "HIT":
                number(e["distance_cm"], "expected distance")
            else:
                need(e["distance_cm"] is None, "non-hit expectation must be null")
        ids.add(q["id"])
        keys.add(key)
    return queries


def quantile(values, p):
    """Linear interpolation at (n-1)*p (Hyndman-Fan type 7), no rounding."""
    need(0 <= p <= 1, "invalid quantile")
    if not values:
        return None
    values = sorted(number(v, "quantile value") for v in values)
    x = (len(values) - 1) * p
    i = int(math.floor(x))
    return values[i] + (values[min(i + 1, len(values) - 1)] - values[i]) * (x - i)


def distribution(values):
    if not values:
        return {k: None for k in ("median", "p95", "p99", "min", "max", "sample_sd", "cv")}
    avg = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else None
    return {"median": quantile(values, .5), "p95": quantile(values, .95),
            "p99": quantile(values, .99), "min": min(values), "max": max(values),
            "sample_sd": sd, "cv": sd / avg if sd is not None and avg > 0 else None}


def divide(numerator, denominator):
    if numerator is None or denominator is None:
        return None
    number(numerator, "numerator")
    number(denominator, "denominator")
    return numerator / denominator if denominator > 0 else None


def ratio_contract(candidate, control, metric):
    """Pure synthetic-testable ratio logic; never infers matched geometry from a label."""
    need(metric in (*METRICS, "transport"), "unknown ratio metric")
    if control is None:
        return {"value": None, "label": None, "reason": "CONTROL_UNAVAILABLE"}
    for k in ("session_id", "environment_hash", "mode", "timing_origin"):
        if candidate[k] != control[k]:
            return {"value": None, "label": None, "reason": f"MISMATCH_{k.upper()}"}
    if candidate["mode"] != "primary":
        return {"value": None, "label": None, "reason": "DIAGNOSTIC_NOT_PRIMARY"}
    value = divide(candidate["value"], control["value"])
    matched = all(candidate.get(k) is not None and candidate[k] == control.get(k)
                  for k in ("bank_sha256", "model_sha256", "query_class", "metric_inputs_sha256"))
    label = ("matched_cost_ratio" if metric != "transport" else "matched_throughput_ratio") if matched else (
        "sentinel_cost_ratio" if metric != "transport" else "sentinel_throughput_ratio")
    return {"value": value, "label": label,
            "reason": None if value is not None else "NULL_OR_ZERO_METRIC"}


def parse_legacy(raw, queries, mode, origin):
    """Normalize archived recovery04 logs. Never use a lane name as an oracle proof."""
    qmap = {q["id"]: q for q in queries}
    result = []
    for r in raw:
        need(isinstance(r, dict), "legacy record must be object")
        if r.get("kind") == "summary":
            result.append({"kind": "summary", "query_count": r.get("query_count"),
                           "candidate_failures": r.get("candidate_failures"),
                           "blocked": r.get("blocked"),
                           "reference_disagreements": r.get("reference_disagreements"),
                           "setup_ns": None, "warmup_ns": None, "warmup_queries": 0,
                           "peak_rss_bytes": None, "cache_policy": r.get("cache_policy"),
                           "mode": mode, "timing_origin": origin})
            continue
        need(r.get("kind") == "query" and r.get("id") in qmap, "legacy unknown record/id")
        q = qmap[r["id"]]
        # The pinned harness has a compact early BLOCKED record on surface,
        # coefficient or source-hash mismatch, before any metric/reference call.
        if set(r) == {"kind", "id", "state", "reason"} and r["state"] == "BLOCKED":
            need(isinstance(r["reason"], str) and r["reason"].strip(), "compact legacy BLOCKED reason missing")
            result.append({"kind": "query", "id": q["id"], "input_sha256": query_hash(q),
                           "candidate": {"state": "BLOCKED", "result": "UNRESOLVED", "distance_cm": None,
                                         "reason": r["reason"]},
                           "reference": {"strength": "sampled", "state": "SKIPPED", "reason": None},
                           "timing_ns": {k: None for k in METRICS},
                           "points": {"classification": None, "normal": None},
                           "counters": {k: None for k in COUNTERS},
                           "recovery_ns": None, "fallback_ns": None, "telemetry_blocked": False})
            continue
        required = {"candidate_state", "state", "candidate_found", "candidate_ok", "candidate_distance",
                    "candidate_distance_ns", "evaluate_ns", "normal_ns", "reference_available", "reference_state",
                    "reference_found", "reference_distance", "reference_agrees", "reference_distance_ns", "telemetry_state"}
        need(required <= r.keys(), "legacy required fields missing")
        need(r["telemetry_state"] in ("PASS", "BLOCKED"), "unknown legacy telemetry state")
        need(type(r["reference_found"]) is bool, "legacy reference_found must be boolean")
        for key in ("coefficient_hash", "source_sha256"):
            expected = q.get("legacy", {}).get(key)
            if expected is not None:
                need(r.get(key) == expected, f"legacy {key} mismatch")
        need(r.get("category") == q["category"], "legacy category mismatch")
        state = r.get("candidate_state")
        need(type(r.get("candidate_found")) is bool, "legacy found must be boolean")
        need(type(r.get("candidate_ok")) is bool, "legacy candidate_ok must be boolean")
        need(r.get("state") == state, "legacy state mismatch")
        need(r["candidate_ok"] == (state == "PASS"), "legacy candidate_ok inconsistent")
        blocked = state == "BLOCKED"
        outcome = "UNRESOLVED" if blocked else "HIT" if r["candidate_found"] else "MISS"
        if blocked:
            need(r.get("candidate_distance") is None, "legacy blocked distance must be null")
        reference_state = r.get("reference_state")
        need(type(r.get("reference_available")) is bool, "legacy reference_available must be boolean")
        need((reference_state == "SKIPPED") == (not r["reference_available"]),
             "legacy reference availability/state inconsistent")
        if reference_state in ("SKIPPED", "BLOCKED"):
            need(r["reference_agrees"] is None and r["reference_distance"] is None,
                 "legacy skipped/blocked reference fields inconsistent")
        else:
            need(type(r["reference_agrees"]) is bool and r["reference_agrees"] == (reference_state == "AGREE"),
                 "legacy reference_agrees/state mismatch")
        if reference_state == "SKIPPED":
            need(r["reference_found"] is False and r["reference_distance_ns"] is None,
                 "legacy skipped reference contains a result or timing")
        if mode == "primary":
            need(not r["reference_available"], "legacy reference calls contaminate primary timing")
        counters = {"candidate_count": r.get("candidate_spans"),
                    "newton_iterations": r.get("candidate_newton"),
                    "recovery_calls": None, "fallback_calls": None,
                    "allocations": None, "allocated_bytes": None}
        result.append({"kind": "query", "id": q["id"], "input_sha256": query_hash(q),
                       "candidate": {"state": state, "result": outcome,
                                     "distance_cm": r.get("candidate_distance"),
                                     "reason": r.get("candidate_error") if blocked else None},
                       # Historical distance_reference is sampled unless separate audited
                       # provenance establishes otherwise. This field is NOT the exact lane.
                       "reference": {"strength": "sampled", "state": reference_state,
                                     "reason": r.get("reference_error")},
                       "timing_ns": {"distance": r.get("candidate_distance_ns"),
                                     "classification": r.get("evaluate_ns"), "normal": r.get("normal_ns")},
                       "points": {"classification": None, "normal": None},
                       "counters": counters, "recovery_ns": None, "fallback_ns": None,
                       "telemetry_blocked": r.get("telemetry_state") == "BLOCKED"})
    return result


def analyze_log(path, queries, lane, plan):
    need(path.stat().st_size <= plan["max_log_bytes"], "stdout exceeds cap")
    lines = path.read_text(encoding="utf-8").splitlines()
    need(lines and all(line.strip() for line in lines), "empty log or blank records")
    records = [strict_loads(line) for line in lines]
    if lane["parser"] == "recovery04":
        records = parse_legacy(records, queries, plan["mode"], plan["timing_origin"])
    need(len(records) == len(queries) + 1, "missing/extra query records or summary")
    qmap = {q["id"]: q for q in queries}
    seen, normalized = set(), []
    for r in records[:-1]:
        fields(r, ("kind", "id", "input_sha256", "candidate", "reference", "timing_ns", "points",
                   "counters", "recovery_ns", "fallback_ns", "telemetry_blocked"), label="log query")
        need(r["kind"] == "query" and r["id"] in qmap, "unknown log record/id")
        need(r["id"] not in seen, "duplicate log query")
        seen.add(r["id"])
        q = qmap[r["id"]]
        need(r["input_sha256"] == query_hash(q), "log input hash mismatch")
        c = r["candidate"]
        fields(c, ("state", "result", "distance_cm", "reason"), label="candidate")
        need(c["state"] in ("PASS", "FAIL", "BLOCKED"), "bad candidate state")
        need(c["result"] in ("HIT", "MISS", "UNRESOLVED"), "bad candidate result")
        need((c["state"] == "BLOCKED") == (c["result"] == "UNRESOLVED"),
             "unresolved cannot be a hit/miss or PASS")
        if c["result"] == "HIT":
            number(c["distance_cm"], "hit distance")
        else:
            need(c["distance_cm"] is None, "non-hit distance must be null")
        if c["state"] == "BLOCKED":
            need(isinstance(c["reason"], str) and c["reason"].strip(), "BLOCKED reason missing")
        else:
            need(c["reason"] is None or isinstance(c["reason"], str), "bad candidate reason")
        ref = r["reference"]
        fields(ref, ("strength", "state", "reason"), label="reference")
        need(ref["strength"] in ("none", "sampled", "exact_oracle"), "bad reference strength")
        need(ref["state"] in ("SKIPPED", "AGREE", "DISAGREE", "BLOCKED"), "bad reference state")
        need(ref["strength"] != "none" or ref["state"] == "SKIPPED", "reference strength absent")
        if ref["state"] == "BLOCKED":
            need(isinstance(ref["reason"], str) and ref["reason"].strip(), "reference BLOCKED reason missing")
        if plan["mode"] == "primary":
            need(ref["state"] == "SKIPPED", "primary must disable second reference solve")
        need(type(r["telemetry_blocked"]) is bool, "bad telemetry flag")
        fields(r["timing_ns"], METRICS, label="timing_ns")
        fields(r["points"], ("classification", "normal"), label="points")
        for metric in METRICS:
            number(r["timing_ns"][metric], metric + " ns", nullable=True)
        for metric in ("classification", "normal"):
            if r["points"][metric] is not None:
                r["points"][metric] = vector(r["points"][metric], metric + " point")
        fields(r["counters"], COUNTERS, label="counters")
        for counter, value in r["counters"].items():
            number(value, counter, nullable=True, integer=True)
            if plan["mode"] == "primary":
                need(value is None, "instrumented counters in primary timing")
        for kind in ("recovery", "fallback"):
            ns = number(r[kind + "_ns"], kind + " ns", nullable=True)
            if plan["mode"] == "primary":
                need(ns is None, "instrumented recovery/fallback time in primary")
            if ns is not None:
                need(r["timing_ns"]["distance"] is not None and ns <= r["timing_ns"]["distance"],
                     f"{kind} time exceeds distance timing")
                calls = r["counters"][kind + "_calls"]
                need(calls is not None and (calls > 0 or ns == 0), "counter/time inconsistency")
        # Bank expectations are exact fixture checks, not tunable tolerances.
        e = q["expected"]
        r["fixture_mismatch"] = bool(e is not None and c["state"] != "BLOCKED" and
                                    (c["result"] != e["result"] or c["distance_cm"] != e["distance_cm"]))
        normalized.append(r)
    need(seen == set(qmap), "bank coverage mismatch")
    s = records[-1]
    fields(s, ("kind", "query_count", "candidate_failures", "blocked", "reference_disagreements",
               "setup_ns", "warmup_ns", "warmup_queries", "peak_rss_bytes", "cache_policy", "mode",
               "timing_origin"), label="summary")
    need(s["kind"] == "summary", "summary must be last")
    expected_counts = {"query_count": len(queries),
                       "candidate_failures": sum(r["candidate"]["state"] == "FAIL" for r in normalized),
                       "blocked": sum(r["candidate"]["state"] == "BLOCKED" for r in normalized),
                       "reference_disagreements": sum(r["reference"]["state"] == "DISAGREE" for r in normalized)}
    for k, expected in expected_counts.items():
        number(s[k], k, integer=True)
        need(s[k] == expected, f"summary {k} mismatch")
    for k in ("setup_ns", "warmup_ns", "peak_rss_bytes"):
        number(s[k], k, nullable=True, integer=k == "peak_rss_bytes")
    number(s["warmup_queries"], "warmup_queries", integer=True)
    need(s["warmup_queries"] == 0, "timed bank must not be used for warmup")
    need(s["cache_policy"] == "unique_queries_fresh_process", "unsupported cache policy")
    need(s["mode"] == plan["mode"] and s["timing_origin"] == plan["timing_origin"], "summary timing provenance mismatch")
    extra = {"fixture_mismatches": sum(r["fixture_mismatch"] for r in normalized),
             "reference_blocked": sum(r["reference"]["state"] == "BLOCKED" for r in normalized),
             "telemetry_blocked": sum(r["telemetry_blocked"] for r in normalized)}
    status = "FAIL" if expected_counts["candidate_failures"] or extra["fixture_mismatches"] else (
        "BLOCKED" if expected_counts["blocked"] or extra["reference_blocked"] or extra["telemetry_blocked"] else "PASS")
    return {"status": status, "counts": {**expected_counts, **extra}, "summary": s,
            "queries": sorted(normalized, key=lambda r: r["id"]),
            "candidate_authority": lane["authority"],
            "authority_evidence": lane["authority_evidence"],
            "authority_verification": "DECLARED_NOT_INDEPENDENTLY_CERTIFIED",
            "comparison_status": "REFERENCE_BLOCKED" if extra["reference_blocked"] else "DISAGREEMENTS" if expected_counts["reference_disagreements"] else "SAMPLED_OR_SKIPPED_NO_CERTIFICATE",
            "correctness_claim": "FINITE_BANK_ONLY_NOT_COMPLETENESS"}


def check_plan(plan):
    fields(plan, ("schema", "mode", "timing_origin", "repetitions", "timeout_s", "max_log_bytes",
                  "artifacts", "lanes"), label="plan")
    need(plan["schema"] == SCHEMA, "unknown plan schema")
    need(plan["mode"] in ("primary", "diagnostic"), "bad mode")
    need(plan["timing_origin"] in ("synthetic", "measured"), "bad timing origin")
    number(plan["repetitions"], "repetitions", integer=True, minimum=1)
    need(plan["repetitions"] <= 100, "repetitions cap 100")
    number(plan["timeout_s"], "timeout", minimum=.01)
    need(plan["timeout_s"] <= 180, "timeout cap 180s")
    number(plan["max_log_bytes"], "max_log_bytes", integer=True, minimum=256)
    need(plan["max_log_bytes"] <= MAX_INPUT, "log cap 2 MiB per stream")
    need(isinstance(plan["artifacts"], dict) and plan["artifacts"], "artifacts required")
    for name, spec in plan["artifacts"].items():
        need(NAME.fullmatch(name) and name not in ("python", "repeat"), "bad/reserved artifact name")
        fields(spec, ("path", "sha256"), label="artifact")
        need(isinstance(spec["path"], str) and spec["path"], "artifact path missing")
        need(isinstance(spec["sha256"], str) and HEX.fullmatch(spec["sha256"]), "SHA256 required")
    need(isinstance(plan["lanes"], list) and 0 < len(plan["lanes"]) <= 16, "lanes cap 16")
    need(len(plan["lanes"]) * plan["repetitions"] * plan["max_log_bytes"] * 4 <= 16 * 1024 * 1024,
         "planned log/journal/receipt budget exceeds 16 MiB; split into new bounded sessions")
    names = set()
    for lane in plan["lanes"]:
        fields(lane, ("name", "role", "command", "bank", "model", "parser", "geometry_domains",
                      "query_class", "implementation", "authority", "authority_evidence",
                      "compiler", "native_provenance"), label="lane")
        name = lane["name"]
        need(isinstance(name, str) and NAME.fullmatch(name), "invalid lane name")
        need(name not in names, "duplicate lane label")
        names.add(name)
        need(lane["role"] in ("candidate", "old_fast", "native_ztorus", "reference"), "bad lane role")
        need(lane["parser"] in ("portable_v1", "recovery04"), "bad log parser")
        need(lane["implementation"] in ("mock", "kernel", "native_openmc_csg_ztorus"), "bad implementation")
        need(lane["authority"] in ("implementation", "sampled_reference", "exact_reference", "analytic_exact"),
             "bad candidate authority")
        need(isinstance(lane["authority_evidence"], str) and lane["authority_evidence"].strip(),
             "authority evidence must be explicit, including unverified cases")
        need(isinstance(lane["query_class"], str) and lane["query_class"], "query class missing")
        need(lane["bank"] in plan["artifacts"] and lane["model"] in plan["artifacts"], "missing bank/model")
        domains = lane["geometry_domains"]
        need(isinstance(domains, dict) and domains and
             all(isinstance(k, str) and isinstance(v, str) and v for k, v in domains.items()), "geometry domains missing")
        need(isinstance(lane["command"], list) and lane["command"] and
             all(isinstance(x, str) and x and "\0" not in x for x in lane["command"]), "argv list required; no shell")
        for arg in lane["command"]:
            if "{" in arg or "}" in arg:
                need(arg.startswith("{") and arg.endswith("}") and
                     arg[1:-1] in {*plan["artifacts"], "python", "repeat"}, "invalid command placeholder")
        if lane["compiler"] is not None:
            fields(lane["compiler"], ("name", "version", "options", "provenance"), label="compiler")
            need(all(isinstance(lane["compiler"][k], str) and lane["compiler"][k]
                     for k in ("name", "version", "provenance")), "bad compiler provenance")
            need(isinstance(lane["compiler"]["options"], list) and
                 all(isinstance(x, str) for x in lane["compiler"]["options"]), "compiler options list required")
        if lane["native_provenance"] is not None:
            p = lane["native_provenance"]
            fields(p, ("review_record_artifact", "binary_sha256", "implementation", "review_status"), label="native provenance")
            need(p["review_record_artifact"] in plan["artifacts"], "missing native review artifact")
            need(isinstance(p["binary_sha256"], str) and HEX.fullmatch(p["binary_sha256"]), "bad native binary hash")
            need(p["implementation"] == "openmc::ZTorus" and p["review_status"] == "SOURCE_AND_BINARY_REVIEWED",
                 "native source/binary provenance unverified")
    for role in ("old_fast", "native_ztorus"):
        need(sum(l["role"] == role for l in plan["lanes"]) <= 1, f"ambiguous {role} control")
    return plan


def discover_environment():
    """Observe tools without acquiring software or executing a target OpenMC binary."""
    tools = {}
    for name, args in (("cc", ["--version"]), ("c++", ["--version"]), ("cmake", ["--version"]),
                       ("pkg-config", ["--version"]), ("h5cc", ["-showconfig"]), ("git", ["--version"])):
        path = shutil.which(name)
        entry = {"path": path, "version_output": None, "exit_code": None, "error": None}
        if path:
            try:
                r = subprocess.run([path, *args], capture_output=True, text=True, timeout=3, check=False)
                entry.update(version_output=(r.stdout + r.stderr)[:8192], exit_code=r.returncode)
            except (OSError, subprocess.TimeoutExpired) as exc:
                entry["error"] = str(exc)
        tools[name] = entry
    dependencies = {}
    pkg = shutil.which("pkg-config")
    for dep in ("hdf5", "gmp", "dagmc", "embree3", "embree4"):
        r = subprocess.run([pkg, "--modversion", dep], capture_output=True, text=True,
                           timeout=3, check=False) if pkg else None
        dependencies[dep] = {"version": r.stdout.strip() if r and r.returncode == 0 else None,
                             "exit_code": r.returncode if r else None}
    cpu = None
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        cpu = next((line.split(":", 1)[1].strip() for line in cpuinfo.read_text().splitlines()
                    if line.startswith("model name")), None)
    return {"platform": platform.platform(), "machine": platform.machine(), "cpu": cpu,
            "python": sys.version, "python_executable": sys.executable,
            "python_executable_resolved": str(Path(sys.executable).resolve()),
            "python_sha256": digest(sys.executable), "python_prefix": sys.prefix,
            "conda_prefix": os.environ.get("CONDA_PREFIX"),
            "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
            "thread_env": THREAD_ENV, "tools": tools, "dependencies": dependencies,
            "openmc_executable": shutil.which("openmc"),
            "cross_sections": os.environ.get("OPENMC_CROSS_SECTIONS"),
            "runner_sha256": digest(__file__),
            "note": "Discovery is not a build record. Null means unavailable, not zero cost."}


def validate_artifacts(plan, base):
    resolved = {}
    for name, item in plan["artifacts"].items():
        p = Path(item["path"])
        p = (base / p).resolve() if not p.is_absolute() else p.resolve()
        need(p.is_file(), f"missing artifact {name}: {p}")
        need(p.stat().st_size <= MAX_INPUT, f"artifact cap 2 MiB: {name}")
        need(digest(p) == item["sha256"], f"artifact hash mismatch: {name}")
        resolved[name] = p
    need(sum(p.stat().st_size for p in resolved.values()) <= MAX_INPUT,
         "total retained artifact snapshot budget exceeds 2 MiB")
    for lane in plan["lanes"]:
        proof = lane["native_provenance"]
        if proof is None:
            continue
        review = read_json(resolved[proof["review_record_artifact"]])
        fields(review, ("schema", "implementation", "binary_sha256", "openmc_commit", "review_status",
                        "reviewer", "source_artifacts", "compiler"), label="native ZTorus review")
        need(review["schema"] == "stellarcsg.native-ztorus-review/v1", "native review schema mismatch")
        need(all(review[k] == proof[k] for k in ("implementation", "binary_sha256", "review_status")),
             "native review does not bind the declared implementation/binary")
        need(review["compiler"] == lane["compiler"] and lane["compiler"] is not None,
             "native compiler provenance missing or inconsistent")
        need(isinstance(review["openmc_commit"], str) and re.fullmatch(r"[0-9a-f]{40}", review["openmc_commit"]),
             "native review needs OpenMC source commit")
        need(isinstance(review["reviewer"], str) and review["reviewer"].strip(), "native reviewer missing")
        sources = review["source_artifacts"]
        need(isinstance(sources, dict) and sources, "native source/harness artifacts missing")
        need(all(k in resolved and h == plan["artifacts"][k]["sha256"] for k, h in sources.items()),
             "native source/harness hash binding mismatch")
    return resolved


def expand_command(lane, artifacts, repeat):
    bindings = {**{k: str(v) for k, v in artifacts.items()}, "python": sys.executable, "repeat": str(repeat)}
    command = [bindings[arg[1:-1]] if arg.startswith("{") else arg for arg in lane["command"]]
    # Relative executable lookup is via PATH only, never an inherited desktop CWD.
    exe = command[0]
    if not Path(exe).is_absolute():
        exe = shutil.which(exe)
    need(exe is not None and Path(exe).is_file(), "executable not found")
    exe = str(Path(exe).resolve())
    need(os.access(exe, os.X_OK), "executable not executable")
    command[0] = exe
    # Interpreter payloads must be named hash-bound artifacts, not hidden -c code.
    if Path(exe).name.lower().startswith(("python", "pypy")):
        need(len(command) > 1 and command[1] in {str(p) for p in artifacts.values()},
             "Python child script must be a declared hashed artifact")
    return command


def kill_group(process):
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        raise Invalid("child could not be reaped")


def execute_child(command, output, stem, plan, session):
    """Bounded POSIX child; process-tree cleanup, per-stream file caps, no shell."""
    import resource
    outpath, errpath = output / f"{stem}.jsonl", output / f"{stem}.stderr"
    attempt = {"command": command, "working_directory": str(output), "binary_sha256_before": digest(command[0]),
               "binary_sha256_after": None, "exit_code": None, "termination": None,
               "error": None, "started_ns": time.time_ns(), "finished_ns": None,
               "child_wall_ns": None, "stdout": None, "stderr": None}
    start = time.perf_counter_ns()
    process = None
    cap = plan["max_log_bytes"]

    def child_limits():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (cap, cap))
        cpu_limit = max(1, math.ceil(plan["timeout_s"]))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 1))

    try:
        with outpath.open("xb") as out, errpath.open("xb") as err:
            process = subprocess.Popen(command, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                       cwd=output, env={**os.environ, **THREAD_ENV,
                                       "PYTHONDONTWRITEBYTECODE": "1", "STELLAR_BENCH_SESSION_ID": session},
                                       shell=False, start_new_session=True, preexec_fn=child_limits)
            try:
                process.wait(timeout=plan["timeout_s"])
            except subprocess.TimeoutExpired:
                attempt["termination"] = "TIMEOUT"
            finally:
                # Also terminate residual members after a nominally successful parent exit.
                kill_group(process)
            attempt["exit_code"] = process.returncode
            if attempt["termination"] is None and process.returncode != 0:
                attempt["termination"] = "NONZERO_CHILD_EXIT"
    except OSError as exc:
        attempt["termination"] = "SPAWN_ERROR"
        attempt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        kill_group(process)
        attempt["child_wall_ns"] = time.perf_counter_ns() - start
        attempt["finished_ns"] = time.time_ns()
        for key, path in (("stdout", outpath), ("stderr", errpath)):
            if path.exists():
                attempt[key] = {"path": path.name, "sha256": digest(path), "bytes": path.stat().st_size}
                if path.stat().st_size >= cap:
                    attempt["termination"] = "OUTPUT_LIMIT"
        try:
            attempt["binary_sha256_after"] = digest(command[0])
        except OSError as exc:
            attempt["error"] = f"binary vanished: {exc}"
        if attempt["binary_sha256_after"] != attempt["binary_sha256_before"]:
            attempt["termination"] = "BINARY_CHANGED"
    return attempt


def lane_statistics(lane, attempts, queries, repetitions):
    good = [a for a in attempts if a["lane"] == lane["name"]]
    usable = len(good) == repetitions and all(a["exit_code"] == 0 and a["termination"] is None and
              not a["validation_errors"] and a["analysis"] is not None and a["analysis"]["status"] == "PASS" for a in good)
    result = {"complete_attempts": usable, "metrics": {}, "diagnostics": {},
              "attempt_count": len(good), "authority": lane["authority"],
              "completeness_certificate": False}
    qmap = {q["id"]: q for q in queries}
    for metric in METRICS:
        all_values, bank_means, per_repeat, input_banks, unique_banks = [], [], {}, [], []
        coverage = []
        for a in good:
            analysis = a["analysis"]
            rows = analysis["queries"] if analysis else []
            values = [r["timing_ns"][metric] for r in rows]
            count = sum(v is not None for v in values)
            coverage.append(count)
            complete = len(values) == len(queries) and count == len(queries)
            mean = statistics.fmean(values) if complete else None
            per_repeat[str(a["repeat"])] = mean
            if mean is not None:
                bank_means.append(mean)
                all_values.extend(values)
            if metric == "distance":
                inputs = [query_key(qmap[r["id"]]) for r in rows]
            else:
                inputs = [[qmap[r["id"]]["geometry"], r["points"][metric]] for r in rows]
                if any(r["points"][metric] is None for r in rows):
                    inputs = None
            input_banks.append(object_hash(inputs) if inputs is not None and rows else None)
            unique_banks.append(len({canonical(x) for x in inputs}) == len(queries) if inputs is not None else None)
        full = usable and len(bank_means) == repetitions and all(v is True for v in unique_banks)
        inputs_hash = input_banks[0] if input_banks and input_banks[0] is not None and len(set(input_banks)) == 1 else None
        result["metrics"][metric] = {
            "cold_bank_ns_per_query": quantile(bank_means, .5) if full else None,
            "bank_mean_repeat_variability": distribution(bank_means if full else []),
            "pooled_per_query_ns": distribution(all_values if full else []),
            "bank_means_by_repeat": per_repeat,
            "available_queries_by_repeat": coverage,
            "metric_inputs_sha256": inputs_hash,
            "metric_inputs_unique_by_repeat": unique_banks,
            "reason": None if full else "INCOMPLETE_OR_NONUNIQUE_METRIC_BANK_OR_FAILED_ATTEMPT_NO_SURVIVOR_MEAN"}
    rows = [r for a in good if a["analysis"] for r in a["analysis"]["queries"]]
    n = repetitions * len(queries)
    for counter in COUNTERS:
        values = [r["counters"][counter] for r in rows]
        result["diagnostics"][counter] = sum(values) if len(values) == n and all(v is not None for v in values) else None
    for kind in ("recovery", "fallback"):
        calls = [r["counters"][kind + "_calls"] for r in rows]
        ns = [r[kind + "_ns"] for r in rows]
        elapsed = [r["timing_ns"]["distance"] for r in rows]
        complete_calls = len(calls) == n and all(c is not None for c in calls)
        complete_ns = len(ns) == n and all(t is not None for t in ns + elapsed)
        result["diagnostics"][kind + "_query_fraction"] = sum(c > 0 for c in calls) / n if complete_calls else None
        result["diagnostics"][kind + "_time_fraction"] = divide(math.fsum(ns), math.fsum(elapsed)) if complete_ns else None
    result["setup_ns_by_repeat"] = [a["analysis"]["summary"]["setup_ns"] if a["analysis"] else None for a in good]
    result["warmup_ns_by_repeat"] = [a["analysis"]["summary"]["warmup_ns"] if a["analysis"] else None for a in good]
    result["peak_rss_bytes_by_repeat"] = [a["analysis"]["summary"]["peak_rss_bytes"] if a["analysis"] else None for a in good]
    return result


def compare_reference_lanes(plan, attempts):
    comparisons = []
    refs = [l for l in plan["lanes"] if l["role"] == "reference"]
    candidates = [l for l in plan["lanes"] if l["role"] in ("candidate", "old_fast")]
    for candidate in candidates:
        for reference in refs:
            record = {"candidate": candidate["name"], "reference": reference["name"],
                      "declared_reference_authority": reference["authority"],
                      "authority_verification": "DECLARED_NOT_INDEPENDENTLY_CERTIFIED",
                      "claim": "FINITE_BANK_REPORTED_FLOAT_COMPARISON_NOT_COMPLETENESS",
                      "query_comparisons": [], "reason": None}
            matched = all(plan["artifacts"][candidate[k]]["sha256"] == plan["artifacts"][reference[k]]["sha256"]
                          for k in ("bank", "model")) and candidate["query_class"] == reference["query_class"]
            if not matched:
                record["reason"] = "UNLIKE_BANK_MODEL_OR_QUERY_CLASS"
                comparisons.append(record)
                continue
            for repeat in range(plan["repetitions"]):
                ca = next((a for a in attempts if a["lane"] == candidate["name"] and a["repeat"] == repeat), None)
                ra = next((a for a in attempts if a["lane"] == reference["name"] and a["repeat"] == repeat), None)
                if not ca or not ra or ca["analysis"] is None or ra["analysis"] is None:
                    record["query_comparisons"].append({"repeat": repeat, "status": "ATTEMPT_UNAVAILABLE"})
                    continue
                cr = {r["id"]: r["candidate"] for r in ca["analysis"]["queries"]}
                rr = {r["id"]: r["candidate"] for r in ra["analysis"]["queries"]}
                for id_, c in cr.items():
                    r = rr[id_]
                    item = {"repeat": repeat, "id": id_, "status": None, "delta_cm": None,
                            "candidate_block_reason": c["reason"] if c["state"] == "BLOCKED" else None,
                            "reference_block_reason": r["reason"] if r["state"] == "BLOCKED" else None}
                    if r["state"] == "BLOCKED":
                        item["status"] = "REFERENCE_BLOCKED"
                    elif c["state"] == "BLOCKED":
                        item["status"] = "CANDIDATE_BLOCKED"
                    elif ca["exit_code"] != 0 or ra["exit_code"] != 0 or ca["termination"] or ra["termination"]:
                        item["status"] = "FAILED_CHILD_RESULT_RETAINED_NOT_QUALIFIED"
                    elif c["result"] != r["result"]:
                        item["status"] = "OUTCOME_DISAGREEMENT"
                    elif c["result"] == "HIT":
                        item["delta_cm"] = c["distance_cm"] - r["distance_cm"]
                        item["status"] = "REPORTED_FLOAT_EQUAL" if item["delta_cm"] == 0 else "DISTANCE_DIFFERENCE_NOT_ADJUDICATED"
                    else:
                        item["status"] = "REPORTED_MISS_AGREEMENT"
                    record["query_comparisons"].append(item)
            comparisons.append(record)
    return comparisons


def summarize(plan, attempts, banks, environment_hash, session_id):
    lanes = {l["name"]: l for l in plan["lanes"]}
    stats = {name: lane_statistics(lane, attempts, banks[name], plan["repetitions"])
             for name, lane in lanes.items()}
    native = next((l for l in lanes.values() if l["role"] == "native_ztorus"), None)
    old = next((l for l in lanes.values() if l["role"] == "old_fast"), None)
    ratios = {}
    native_ok = (native is not None and native["implementation"] == "native_openmc_csg_ztorus" and
                 native["native_provenance"] is not None and native["compiler"] is not None and
                 plan["timing_origin"] == "measured" and plan["mode"] == "primary")
    if native_ok:
        native_runs = [a for a in attempts if a["lane"] == native["name"]]
        native_ok = bool(native_runs) and all(a["binary_sha256_before"] == native["native_provenance"]["binary_sha256"] for a in native_runs)

    def context(lane, metric, repeat=None):
        m = stats[lane["name"]]["metrics"][metric]
        return {"session_id": session_id, "environment_hash": environment_hash,
                "mode": plan["mode"], "timing_origin": plan["timing_origin"],
                "bank_sha256": plan["artifacts"][lane["bank"]]["sha256"],
                "model_sha256": plan["artifacts"][lane["model"]]["sha256"],
                "query_class": lane["query_class"], "metric_inputs_sha256": m["metric_inputs_sha256"],
                "value": m["cold_bank_ns_per_query"] if repeat is None else m["bank_means_by_repeat"].get(str(repeat))}
    for name, lane in lanes.items():
        row = {}
        for control_name, control, qualified in (("native_ztorus", native, native_ok), ("old_fast", old, old is not None)):
            metrics = {}
            for metric in METRICS:
                candidate_context = context(lane, metric)
                cmp = ratio_contract(candidate_context, context(control, metric) if control and qualified else None, metric)
                paired = []
                if cmp["value"] is not None:
                    for repeat in range(plan["repetitions"]):
                        v = divide(context(lane, metric, repeat)["value"], context(control, metric, repeat)["value"])
                        if v is not None:
                            paired.append(v)
                cmp["paired_repeat_ratios"] = paired
                cmp["paired_repeat_variability"] = distribution(paired)
                if control_name == "native_ztorus" and not native_ok:
                    cmp["reason"] = "NATIVE_OPENMC_ZTORUS_UNAVAILABLE_OR_UNVERIFIED"
                cmp["timing_origin"] = plan["timing_origin"]
                metrics[metric] = cmp
            metrics["transport"] = {"value": None, "label": "histories_per_second_candidate_over_control",
                                    "reason": "MATCHED_TRANSPORT_GATED_NOT_EXECUTED"}
            row[control_name] = metrics
        old_ratio = row["old_fast"]["distance"]
        measured_matched = (plan["timing_origin"] == "measured" and old_ratio["label"] == "matched_cost_ratio"
                            and old_ratio["value"] is not None)
        r = old_ratio["value"] if measured_matched else None
        row["old_fast_guardrail"] = (
            "PREFERRED_COST_ONLY_NOT_QUALIFIED" if r is not None and r <= 1.25 else
            "TEMPORARY_ONLY_WITH_DEMONSTRATED_CORRECTNESS_FIX" if r is not None and r <= 2 else
            "EXPERIMENTAL_OVER_2X" if r is not None else "NOT_EVALUATED")
        ratios[name] = row
    failures = any(a["termination"] or a["exit_code"] != 0 or a["validation_errors"] or
                   (a["analysis"] and a["analysis"]["status"] == "FAIL") for a in attempts)
    blocked = any(a["analysis"] and a["analysis"]["status"] == "BLOCKED" for a in attempts)
    expected = len(plan["lanes"]) * plan["repetitions"]
    execution = "FAIL" if failures or len(attempts) != expected else "BLOCKED" if blocked else "PASS"
    required = [l for l in lanes.values() if l["role"] in ("candidate", "old_fast")]
    comparison_complete = (native_ok and execution == "PASS" and plan["repetitions"] >= 2 and
                           bool(required) and all(l["compiler"] is not None and
                           all(ratios[l["name"]]["native_ztorus"][m]["value"] is not None for m in METRICS)
                           for l in required))
    return {"execution_status": execution, "performance_status": "COMPLETE_GEOMETRY_ONLY" if comparison_complete else "INCOMPLETE",
            "qualification_status": "NOT_ESTABLISHED", "matched_transport_status": "GATED_NOT_RUN",
            "statistics": stats, "ratios": ratios,
            "reference_comparisons": compare_reference_lanes(plan, attempts),
            "note": "Synthetic timings test accounting only. Declared reference authority is not certification. Fresh process is not a hardware cold-cache guarantee."}


def run_plan(plan_path, output, *, enabled=False, cpu=None):
    need(enabled, "experimental runner is OFF; pass --enable-experiment")
    need(os.name == "posix" and hasattr(os, "sched_setaffinity"),
         "CAPABILITY_BLOCKED: this runner requires POSIX process groups and explicit CPU affinity; native Windows not qualified")
    plan_path, output = Path(plan_path).resolve(), Path(output).resolve()
    plan = check_plan(read_json(plan_path))
    artifacts = validate_artifacts(plan, plan_path.parent)
    banks = {l["name"]: load_bank(artifacts[l["bank"]], l["geometry_domains"]) for l in plan["lanes"]}
    # Preflight every argv before creating results or launching any child.
    for lane in plan["lanes"]:
        if lane["parser"] == "recovery04":
            need(len(banks[lane["name"]]) == 160, "recovery04 executable contract requires 160 unique queries")
        expand_command(lane, artifacts, 0)
    affinity = os.sched_getaffinity(0)
    cpu = min(affinity) if cpu is None else cpu
    need(type(cpu) is int and cpu in affinity, "requested CPU outside allowed affinity")
    output.mkdir(parents=True, exist_ok=False)
    os.sched_setaffinity(0, {cpu})
    attempts = []
    try:
        environment = discover_environment()
        env_hash = object_hash(environment)
        session = str(uuid.uuid4())
        snapshots = output / "inputs"
        snapshots.mkdir()
        copied_plan = strict_loads(canonical(plan))
        for name, path in artifacts.items():
            dst = snapshots / (name + path.suffix)
            with dst.open("xb") as stream:
                stream.write(path.read_bytes())
            need(digest(dst) == plan["artifacts"][name]["sha256"], "artifact changed during snapshot")
            copied_plan["artifacts"][name]["path"] = str(dst.relative_to(output))
        write_new(output / "plan.json", copied_plan)
        write_new(output / "environment.json", environment)
        write_new(output / "started.json", {"session_id": session, "environment_hash": env_hash,
                  "plan_sha256": digest(output / "plan.json"), "pinned_commit": PIN,
                  "started_ns": time.time_ns(), "cpu": cpu})
        # Execute the hash-bound snapshots, not mutable original inputs.
        snapshots_map = validate_artifacts(copied_plan, output)
        for repeat in range(plan["repetitions"]):
            schedule = plan["lanes"] if repeat % 2 == 0 else list(reversed(plan["lanes"]))
            for lane in schedule:
                command = expand_command(lane, snapshots_map, repeat)
                a = execute_child(command, output, f'{lane["name"]}-{repeat}', plan, session)
                a.update(lane=lane["name"], repeat=repeat, analysis=None, validation_errors=[])
                try:
                    validate_artifacts(copied_plan, output)
                    a["analysis"] = analyze_log(output / a["stdout"]["path"], banks[lane["name"]], lane, plan)
                except (Invalid, OSError, UnicodeError, TypeError) as exc:
                    a["validation_errors"].append(str(exc))
                attempts.append(a)
                write_new(output / f'attempt-{len(attempts)-1:04d}.json', a)
        summary = summarize(copied_plan, attempts, banks, env_hash, session)
        receipt = {"schema": SCHEMA, "session_id": session, "environment_hash": env_hash,
                   "plan_sha256": digest(output / "plan.json"), "attempts": attempts,
                   "summary": summary, "finished_ns": time.time_ns()}
        write_new(output / "receipt.json", receipt)
        return receipt
    finally:
        os.sched_setaffinity(0, affinity)


def inside(base, relative):
    need(isinstance(relative, str) and not Path(relative).is_absolute(), "receipt paths must be relative")
    path = (base / relative).resolve()
    need(path.is_relative_to(base.resolve()), "receipt path escape")
    return path


def validate_receipt(path):
    """Re-hash retained inputs/logs and recompute status, metrics and ratios from raw data."""
    path = Path(path).resolve()
    base = path.parent
    receipt = read_json(path, limit=16 * 1024 * 1024)
    fields(receipt, ("schema", "session_id", "environment_hash", "plan_sha256", "attempts", "summary", "finished_ns"), label="receipt")
    need(receipt["schema"] == SCHEMA, "receipt schema mismatch")
    plan = check_plan(read_json(base / "plan.json"))
    need(receipt["plan_sha256"] == digest(base / "plan.json"), "plan hash mismatch")
    environment = read_json(base / "environment.json")
    need(receipt["environment_hash"] == object_hash(environment), "environment hash mismatch")
    started = read_json(base / "started.json")
    need(all(receipt[k] == started[k] for k in ("session_id", "environment_hash", "plan_sha256")), "session binding mismatch")
    for spec in plan["artifacts"].values():
        inside(base, spec["path"])
    artifacts = validate_artifacts(plan, base)
    lanes = {l["name"]: l for l in plan["lanes"]}
    banks = {n: load_bank(artifacts[l["bank"]], l["geometry_domains"]) for n, l in lanes.items()}
    need(isinstance(receipt["attempts"], list), "attempts must be list")
    seen = set()
    for i, a in enumerate(receipt["attempts"]):
        fields(a, ("command", "working_directory", "binary_sha256_before", "binary_sha256_after",
                   "exit_code", "termination", "error", "started_ns", "finished_ns", "child_wall_ns",
                   "stdout", "stderr", "lane", "repeat", "analysis", "validation_errors"), label="attempt")
        need(isinstance(a["command"], list) and a["command"] and all(isinstance(x, str) for x in a["command"]), "bad recorded command")
        need(isinstance(a["validation_errors"], list) and all(isinstance(x, str) for x in a["validation_errors"]), "bad validation errors")
        need(a["termination"] in (None, "TIMEOUT", "NONZERO_CHILD_EXIT", "OUTPUT_LIMIT", "SPAWN_ERROR", "BINARY_CHANGED"), "unknown termination")
        need(a["lane"] in lanes, "unknown attempt lane")
        number(a["repeat"], "repeat", integer=True)
        need(a["repeat"] < plan["repetitions"], "repeat out of range")
        key = (a["lane"], a["repeat"])
        need(key not in seen, "duplicate attempt")
        seen.add(key)
        need(read_json(base / f"attempt-{i:04d}.json", limit=16 * 1024 * 1024) == a, "attempt journal mismatch")
        need(started["started_ns"] <= a["started_ns"] <= a["finished_ns"] <= receipt["finished_ns"], "attempt outside session")
        number(a["child_wall_ns"], "wall ns")
        need(isinstance(a["working_directory"], str) and Path(a["working_directory"]).is_absolute(), "recorded cwd missing")
        bindings = {k: str(Path(a["working_directory"]) / item["path"]) for k, item in plan["artifacts"].items()}
        bindings.update(python=environment["python_executable_resolved"], repeat=str(a["repeat"]))
        template = lanes[a["lane"]]["command"]
        expected_args = [bindings[x[1:-1]] if x.startswith("{") else x for x in template]
        need(a["command"][1:] == expected_args[1:], "recorded argv differs from hash-bound plan")
        if template[0].startswith("{"):
            need(a["command"][0] == expected_args[0], "recorded executable differs from plan")
        need(a["exit_code"] is None or type(a["exit_code"]) is int, "invalid child exit code")
        need(isinstance(a["binary_sha256_before"], str) and HEX.fullmatch(a["binary_sha256_before"]), "missing binary hash")
        if a["termination"] is None:
            need(a["binary_sha256_after"] == a["binary_sha256_before"], "binary changed without failure")
        for stream in ("stdout", "stderr"):
            item = a[stream]
            need(isinstance(item, dict), "missing child stream receipt")
            p = inside(base, item["path"])
            need(p.is_file() and p.stat().st_size == item["bytes"] and digest(p) == item["sha256"], "log hash/size mismatch")
        try:
            fresh = analyze_log(inside(base, a["stdout"]["path"]), banks[a["lane"]], lanes[a["lane"]], plan)
        except (Invalid, OSError, UnicodeError) as exc:
            need(a["analysis"] is None and a["validation_errors"], "invalid log hidden by receipt")
        else:
            need(fresh == a["analysis"], "normalized log analysis mismatch")
            need(not a["validation_errors"], "unexpected validation errors on clean logs")
    fresh_summary = summarize(plan, receipt["attempts"], banks, receipt["environment_hash"], receipt["session_id"])
    need(fresh_summary == receipt["summary"], "receipt metric/status/ratio mismatch")
    return {"receipt_integrity": "VALID", "execution_status": fresh_summary["execution_status"],
            "performance_status": fresh_summary["performance_status"],
            "matched_transport_status": fresh_summary["matched_transport_status"],
            "binary_revalidation": "PRE_POST_HASHES_RECORDED_NOT_CURRENTLY_REEXECUTED_OR_REHASHED",
            "authenticity": "UNSIGNED_LOCAL_RECEIPT_NOT_A_THIRD_PARTY_ATTESTATION"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--enable-experiment", action="store_true")
    run.add_argument("--cpu", type=int)
    run.add_argument("--require-native-control", action="store_true")
    val = sub.add_parser("validate")
    val.add_argument("receipt", type=Path)
    sub.add_parser("discover")
    a = p.parse_args(argv)
    try:
        if a.action == "discover":
            print(json.dumps(discover_environment(), indent=2, allow_nan=False))
            return 0
        if a.action == "run":
            r = run_plan(a.plan, a.output, enabled=a.enable_experiment, cpu=a.cpu)
            result = {k: r["summary"][k] for k in ("execution_status", "performance_status", "matched_transport_status")}
            result["receipt"] = str(a.output / "receipt.json")
            require_native = a.require_native_control
        else:
            result = validate_receipt(a.receipt)
            require_native = False
        print(json.dumps(result, indent=2, allow_nan=False))
        if result["execution_status"] == "FAIL":
            return 1
        if result["execution_status"] == "BLOCKED":
            return 2
        return 3 if require_native and result["performance_status"] == "INCOMPLETE" else 0
    except (Invalid, OSError, UnicodeError, KeyError, TypeError, OverflowError, subprocess.SubprocessError) as exc:
        print(f"INVALID_OR_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
