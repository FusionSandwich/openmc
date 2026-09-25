#!/usr/bin/env python3
"""Reduce recovery04 raw subprocess receipts without changing their evidence.

An attempt with a nonzero exit can still be complete: the harness returns one
for an observed candidate failure.  Timeout, missing, malformed, or truncated
attempts are instead invalid and are never silently converted to PASS.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


QUERY_COUNT = 160
TIME_FIELDS = {
    "distance": "candidate_distance_ns",
    "classification": "evaluate_ns",
    "normal": "normal_ns",
    "candidates": "candidate_spans",
    "newton": "candidate_newton",
    "subdivision": "candidate_subdivision",
}


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    location = (len(ordered) - 1) * fraction
    lower, upper = math.floor(location), math.ceil(location)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (location - lower)


def finite(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records, errors = [], []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return records, [f"cannot_read:{error}"]
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"malformed_json_line:{number}")
            continue
        if not isinstance(value, dict):
            errors.append(f"non_object_line:{number}")
        else:
            records.append(value)
    return records, errors


def parse_attempt(campaign: Path, attempt: dict[str, Any], bank_rows: dict[str, dict[str, str]]) -> dict[str, Any]:
    label = f"{campaign}:{attempt.get('lane')}:{attempt.get('repeat')}"
    errors: list[str] = []
    if attempt.get("timeout"):
        errors.append("timeout")
    stdout_name = attempt.get("stdout")
    if not isinstance(stdout_name, str):
        errors.append("missing_stdout_name")
        records: list[dict[str, Any]] = []
    else:
        records, read_errors = read_jsonl(campaign / stdout_name)
        errors.extend(read_errors)
    queries = [record for record in records if record.get("kind") == "query"]
    summaries = [record for record in records if record.get("kind") == "summary"]
    ids = [query.get("id") for query in queries]
    if len(summaries) != 1:
        errors.append("missing_or_multiple_summary")
    elif summaries[0].get("query_count") != QUERY_COUNT:
        errors.append("summary_query_count_not_160")
    if len(queries) != QUERY_COUNT:
        errors.append(f"query_count_not_160:{len(queries)}")
    if len(set(ids)) != QUERY_COUNT or any(not isinstance(value, str) for value in ids):
        errors.append("query_ids_not_unique_160")
    for query in queries:
        frozen = bank_rows.get(query.get("id"))
        if frozen is None:
            errors.append(f"query_not_in_frozen_bank:{query.get('id')}")
            continue
        # JSONL does not repeat coordinates, so bind every identity field it
        # does carry back to the immutable full coordinate row in the CSV.
        for key in ("category", "heldout", "coefficient_hash", "source_sha256", "expected"):
            observed = str(int(query.get(key))) if key == "heldout" and isinstance(query.get(key), bool) else str(query.get(key)).lower()
            if observed != str(frozen.get(key)).lower():
                errors.append(f"frozen_identity_mismatch:{query.get('id')}:{key}")
    return {"label": label, "lane": attempt.get("lane"), "repeat": attempt.get("repeat"),
            "campaign": str(campaign), "exit_code": attempt.get("exit_code"),
            "valid": not errors, "errors": errors, "queries": queries,
            "summary": summaries[0] if len(summaries) == 1 else None}


def input_signature(query: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(query.get(key) for key in ("id", "category", "heldout", "coefficient_hash", "source_sha256", "expected"))


def status_signature(query: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(query.get(key) for key in ("state", "candidate_state", "reference_state", "telemetry_state", "candidate_found"))


def load_frozen_bank(hashes: dict[str, Any]) -> tuple[dict[str, dict[str, str]], list[str]]:
    csv_keys = [path for path in hashes if str(path).endswith(".csv")]
    if len(csv_keys) != 1:
        return {}, ["receipt_requires_exactly_one_bank_csv_hash"]
    bank_path = Path(csv_keys[0])
    try:
        with bank_path.open(newline="", encoding="ascii") as stream:
            rows = list(csv.DictReader(stream))
    except OSError as error:
        return {}, [f"cannot_read_frozen_bank:{error}"]
    errors = []
    if hashlib.sha256(bank_path.read_bytes()).hexdigest() != hashes[csv_keys[0]]:
        errors.append('frozen_bank_hash_changed')
    if len(rows) != QUERY_COUNT:
        errors.append(f"frozen_bank_row_count_not_160:{len(rows)}")
    ids = [row.get("id") for row in rows]
    if len(set(ids)) != QUERY_COUNT or any(not value for value in ids):
        errors.append("frozen_bank_ids_not_unique_160")
    tuples = [(row['geometry'], row['category'].startswith('coincident_'),
               *(float(row[key]) for key in ('ox', 'oy', 'oz', 'dx', 'dy', 'dz'))) for row in rows]
    if len(set(tuples)) != QUERY_COUNT:
        errors.append("frozen_bank_full_query_tuples_not_unique_160")
    return {row["id"]: row for row in rows if row.get("id")}, errors


def attempt_means(queries: list[dict[str, Any]], field: str) -> tuple[float | None, int]:
    values = [finite(query.get(field)) for query in queries]
    usable = [value for value in values if value is not None]
    return (sum(usable) / len(usable) if usable else None, QUERY_COUNT - len(usable))


def summarize_lane(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [attempt for attempt in attempts if attempt["valid"]]
    primary_complete = len(attempts) == 7 and len(valid) == 7
    first = min(attempts, key=lambda attempt: attempt.get("repeat", math.inf)) if attempts else None
    first_queries = first["queries"] if first and first["valid"] else []
    result: dict[str, Any] = {"attempt_count": len(attempts), "valid_attempt_count": len(valid),
                               "invalid_attempt_count": len(attempts) - len(valid), "metrics": {}}
    result["primary_median_of_7_complete"] = primary_complete
    result["first_run_unique_status"] = {"available": bool(first_queries),
        "candidate_failure_query_ids": sorted(query["id"] for query in first_queries if query.get("candidate_state") == "FAIL"),
        "candidate_blocked_query_ids": sorted(query["id"] for query in first_queries if query.get("candidate_state") == "BLOCKED"),
        "reference_blocked_query_ids": sorted(query["id"] for query in first_queries if query.get("reference_state") == "BLOCKED"),
        "states": {state: sum(query.get("state") == state for query in first_queries)
                   for state in sorted({query.get("state") for query in first_queries})}}
    result["attempts"] = [{"repeat": attempt.get("repeat"), "exit_code": attempt.get("exit_code"),
                            "valid": attempt["valid"], "errors": attempt["errors"]} for attempt in attempts]
    by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in valid:
        for query in attempt["queries"]:
            by_query[query["id"]].append(query)
    for metric, field in TIME_FIELDS.items():
        means, exclusions = [], 0
        for attempt in valid:
            value, excluded = attempt_means(attempt["queries"], field)
            exclusions += excluded
            if value is not None:
                means.append(value)
        per_query = [value for rows in by_query.values() for q in rows
                     if (value := finite(q.get(field))) is not None]
        result["metrics"][metric] = {"median_of_bank_means": median(means) if primary_complete and means and exclusions == 0 else None,
            "pooled_perquery_median": percentile(per_query, .50),
            "pooled_perquery_p95": percentile(per_query, .95),
            "pooled_perquery_p99": percentile(per_query, .99),
            "timing_excluded_values": exclusions, "available": bool(means)}
    result["per_category"] = group_aggregate(valid, "category")
    result["heldout"] = group_aggregate(valid, "heldout")
    return result


def group_aggregate(attempts: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in attempts:
        for query in attempt["queries"]:
            groups[str(query.get(field))].append(query)
    result = {}
    for group, rows in sorted(groups.items()):
        item = {"unique_query_count": len({row.get("id") for row in rows}), "metrics": {}}
        for metric, metric_field in TIME_FIELDS.items():
            values = [value for row in rows if (value := finite(row.get(metric_field))) is not None]
            item["metrics"][metric] = {"median": percentile(values, .5), "p95": percentile(values, .95),
                                         "p99": percentile(values, .99), "available": bool(values)}
        result[group] = item
    return result


def repeat_consistency(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [attempt for attempt in attempts if attempt["valid"]]
    if not valid:
        return {"available": False, "input_mismatches": [], "status_mismatches": []}
    baseline = {query["id"]: query for query in valid[0]["queries"]}
    inputs, statuses = set(), set()
    for attempt in valid[1:]:
        current = {query["id"]: query for query in attempt["queries"]}
        for query_id in sorted(set(baseline) | set(current)):
            if query_id not in baseline or query_id not in current or input_signature(baseline[query_id]) != input_signature(current[query_id]):
                inputs.add(query_id)
            elif status_signature(baseline[query_id]) != status_signature(current[query_id]):
                statuses.add(query_id)
    return {"available": True, "input_mismatches": sorted(inputs), "status_mismatches": sorted(statuses)}


def exact_reference_comparison(lanes: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    references = [attempt for attempt in lanes.get("exact_reference", []) if attempt["valid"]]
    if not references:
        return {"available": False, "reason": "exact_reference_lane_absent"}
    reference = {query["id"]: query for query in references[0]["queries"]}
    comparisons = {}
    for lane, attempts in lanes.items():
        if lane == "exact_reference":
            continue
        mismatches, blocked = set(), set()
        for attempt in attempts:
            if not attempt["valid"]:
                continue
            for query in attempt["queries"]:
                oracle = reference.get(query["id"])
                if not oracle:
                    mismatches.add(query["id"]); continue
                if oracle.get('candidate_state') == 'BLOCKED' or oracle.get("reference_state") == "BLOCKED":
                    blocked.add(query["id"]); continue
                if query.get('candidate_state') == 'BLOCKED':
                    mismatches.add(query['id']); continue
                found_a = query.get("candidate_found")
                found_b = oracle.get("reference_found") if oracle.get("reference_available") else oracle.get("candidate_found")
                if found_a != found_b:
                    mismatches.add(query["id"]); continue
                a, b = finite(query.get("candidate_distance")), finite(oracle.get("reference_distance") if oracle.get("reference_available") else oracle.get("candidate_distance"))
                if found_a and (a is None or b is None or abs(a - b) > 2e-8):
                    mismatches.add(query["id"])
        comparisons[lane] = {"distance_tolerance_absolute": 2e-8, "mismatched_query_ids": sorted(mismatches),
                             "reference_blocked_query_ids": sorted(blocked)}
    return {"available": True, "comparisons": comparisons}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--repeat", action="append", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    campaigns = [args.campaign, *args.repeat]
    parsed, receipt_hashes, errors = [], [], []
    for campaign in campaigns:
        try:
            receipt = json.loads((campaign / "receipt.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{campaign}:receipt_unreadable:{error}"); continue
        if receipt.get("schema") != "stellarcsg.recovery04.measure/v1":
            errors.append(f"{campaign}:unexpected_receipt_schema")
        hashes = receipt.get("hashes")
        if not isinstance(hashes, dict):
            errors.append(f"{campaign}:missing_hashes"); hashes = {}
        receipt_hashes.append(hashes)
        bank_rows, bank_errors = load_frozen_bank(hashes)
        errors.extend(f"{campaign}:{error}" for error in bank_errors)
        raw_attempts = receipt.get("attempts")
        if not isinstance(raw_attempts, list) or not raw_attempts:
            errors.append(f"{campaign}:missing_or_empty_attempts")
            raw_attempts = []
        for attempt in raw_attempts:
            if not isinstance(attempt, dict):
                errors.append(f"{campaign}:non_object_attempt"); continue
            parsed.append(parse_attempt(campaign, attempt, bank_rows))
    lanes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in parsed:
        if isinstance(attempt["lane"], str): lanes[attempt["lane"]].append(attempt)
        else: errors.append(f"{attempt['label']}:missing_lane")
        if not attempt["valid"]: errors.append(f"{attempt['label']}:{','.join(attempt['errors'])}")
    bank_hashes = {value for hashes in receipt_hashes for path, value in hashes.items() if str(path).endswith(".csv")}
    if len(bank_hashes) != 1:
        errors.append("campaigns_do_not_share_exactly_one_frozen_bank_hash")
    lane_results = {lane: summarize_lane(attempts) for lane, attempts in sorted(lanes.items())}
    for lane, attempts in lanes.items(): lane_results[lane]["repeat_consistency"] = repeat_consistency(attempts)
    ratios = {"available": False, "reason": "requires_old_and_experimental_160_query_reports_with_one_bank_hash"}
    if {"old", "experimental"} <= set(lanes) and len(bank_hashes) == 1 and all(lane_results[x]["primary_median_of_7_complete"] for x in ("old", "experimental")):
        old, experimental = lane_results["old"]["metrics"]["distance"]["median_of_bank_means"], lane_results["experimental"]["metrics"]["distance"]["median_of_bank_means"]
        if old is not None and experimental not in (None, 0): ratios = {"available": True, "old_over_experimental_distance": old / experimental, "bank_sha256": next(iter(bank_hashes))}
    report = {"schema": "stellarcsg.recovery04.reduce/v1", "campaigns": [str(path) for path in campaigns],
              "bank_hashes": sorted(bank_hashes), "errors": errors, "lanes": lane_results,
              "exact_reference": exact_reference_comparison(lanes), "old_experimental_ratio": ratios,
              "unknown_fallback_count": None, "unknown_fallback_time_ns": None,
              "unknown_allocation_count": None, "unknown_memory_bytes": None,
              "raw_evidence_retained_on_disk": True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
