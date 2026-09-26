#!/usr/bin/env python3
"""Compare complete frozen-bank candidate and independent exact-lane JSONL."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys


QUERY_COUNT = 160
TOLERANCE = 2e-8
SUMMARY_FIELDS = {
    "kind", "query_count", "candidate_failures", "candidate_nearest_failures",
    "reference_disagreements", "blocked", "cache_policy", "claim",
}
KNOWN_REPRESENTATION = "legacy_rounded_frame"
FROZEN_BANK = Path(__file__).with_name("recovery04_frozen_bank.csv")


def _json_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"nonstandard JSON constant: {value}")


def _frozen_metadata() -> list[dict[str, str]]:
    with FROZEN_BANK.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _finite_nonnegative(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _valid_found_distance(found: object, distance: object, *, label: str) -> None:
    if type(found) is not bool:
        raise ValueError(f"invalid {label} found flag")
    if found:
        if not _finite_nonnegative(distance):
            raise ValueError(f"invalid {label} distance")
    elif distance is not None:
        raise ValueError(f"distance present for {label} miss")


def _provenance(row: dict, *, path: Path) -> tuple[str, str]:
    coefficient = row.get("coefficient_hash")
    source = row.get("source_sha256")
    if not isinstance(coefficient, str) or not coefficient.strip():
        raise ValueError(f"missing coefficient provenance: {path}")
    if not isinstance(source, str):
        raise ValueError(f"missing source provenance: {path}")
    # Generated torus fixtures have no source file and encode that explicitly as
    # an empty string. WISTELL rows must bind the actual source file hash.
    if (row.get("geometry") == "wistell_coil031" or
            str(row.get("category", "")).startswith("wistell")) and not source.strip():
        raise ValueError(f"missing WISTELL source hash: {path}")
    return coefficient, source


def read(path: Path, *, exact: bool = False) -> tuple[dict[str, dict], dict]:
    try:
        rows = [json.loads(line, object_pairs_hook=_json_object, parse_constant=_reject_constant)
                for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid JSONL: {path}") from exc
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"JSONL records must be objects: {path}")
    queries = [row for row in rows if row.get("kind") == "query"]
    summaries = [row for row in rows if row.get("kind") == "summary"]
    if len(queries) != QUERY_COUNT or len(summaries) != 1 or len(rows) != QUERY_COUNT + 1:
        raise ValueError(f"incomplete or duplicate frozen bank: {path}")
    ids = [row.get("id") for row in queries]
    if any(not isinstance(query_id, str) or not query_id for query_id in ids) or len(set(ids)) != QUERY_COUNT:
        raise ValueError(f"incomplete or duplicate frozen bank: {path}")
    frozen = _frozen_metadata()
    if len(frozen) != QUERY_COUNT:
        raise ValueError(f"invalid tracked frozen bank: {FROZEN_BANK}")
    if ids != [row["id"] for row in frozen]:
        raise ValueError(f"query IDs or order differ from tracked frozen bank: {path}")

    summary = summaries[0]
    if not SUMMARY_FIELDS.issubset(summary):
        raise ValueError(f"incomplete summary: {path}")
    for field in ("query_count", "candidate_failures", "candidate_nearest_failures",
                  "reference_disagreements", "blocked"):
        if not _nonnegative_int(summary[field]):
            raise ValueError(f"invalid summary field {field}: {path}")
    if summary["kind"] != "summary" or summary["query_count"] != QUERY_COUNT:
        raise ValueError(f"invalid summary: {path}")
    if not isinstance(summary["cache_policy"], str) or not summary["cache_policy"] or \
            not isinstance(summary["claim"], str) or not summary["claim"]:
        raise ValueError(f"invalid summary provenance: {path}")

    blocked_count = 0
    failed_count = 0
    disagreement_count = 0
    for row in queries:
        if row.get("kind") != "query":
            raise ValueError(f"invalid query row: {path}")
        _provenance(row, path=path)
        if not all(ch in "0123456789abcdef" for ch in row["coefficient_hash"]):
            raise ValueError(f"invalid coefficient hash syntax: {path}")
        source_hash = row["source_sha256"]
        if source_hash and (len(source_hash) != 64 or
                            any(ch not in "0123456789abcdef" for ch in source_hash)):
            raise ValueError(f"invalid source hash syntax: {path}")
        canonical = frozen[ids.index(row["id"])]
        if any(row.get(field) != canonical[field] for field in
               ("category", "expected", "coefficient_hash", "source_sha256")):
            raise ValueError(f"query metadata differs from tracked frozen bank: {row['id']}")
        heldout = row.get("heldout")
        if type(heldout) is not bool or heldout != (canonical["heldout"] == "1"):
            raise ValueError(f"query heldout metadata differs from tracked frozen bank: {row['id']}")
        representation = row.get("geometry_representation", KNOWN_REPRESENTATION)
        if representation != KNOWN_REPRESENTATION:
            raise ValueError(f"unsupported geometry representation: {path}")
        state = row.get("candidate_state")
        if state not in ("PASS", "FAIL", "BLOCKED"):
            raise ValueError(f"invalid candidate state: {path}")
        if type(row.get("state")) is not str or row["state"] not in ("PASS", "FAIL", "BLOCKED"):
            raise ValueError(f"invalid row state: {path}")
        if row["state"] != state:
            raise ValueError(f"candidate state disagrees with row state: {path}")
        if type(row.get("candidate_ok")) is not bool or row["candidate_ok"] != (state == "PASS"):
            raise ValueError(f"candidate_ok disagrees with candidate state: {path}")
        reference_state = row.get("reference_state")
        if reference_state not in ("AGREE", "DISAGREE", "SKIPPED"):
            raise ValueError(f"invalid reference state: {path}")
        if state == "BLOCKED":
            blocked_count += 1
        if state == "FAIL":
            failed_count += 1
        if row.get("reference_state") == "DISAGREE":
            disagreement_count += 1
        if exact and state != "PASS":
            raise ValueError(f"exact lane contains non-PASS row: {path}")
        _valid_found_distance(row.get("candidate_found"), row.get("candidate_distance"),
                              label="candidate")
        if "reference_found" in row or "reference_distance" in row:
            _valid_found_distance(row.get("reference_found"), row.get("reference_distance"),
                                  label="reference")

    if summary["blocked"] != blocked_count:
        raise ValueError(f"summary blocked count disagrees with rows: {path}")
    if summary["candidate_failures"] != failed_count:
        raise ValueError(f"summary candidate failure count disagrees with rows: {path}")
    if summary["candidate_nearest_failures"] != failed_count:
        raise ValueError(f"summary nearest failure count disagrees with rows: {path}")
    if summary["reference_disagreements"] != disagreement_count:
        raise ValueError(f"summary reference disagreement count disagrees with rows: {path}")
    if exact and summary["candidate_nearest_failures"] != 0:
        raise ValueError(f"exact lane has candidate nearest failures: {path}")
    return {row["id"]: row for row in queries}, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--exact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    candidate, candidate_summary = read(args.candidate)
    exact, exact_summary = read(args.exact, exact=True)
    if set(candidate) != set(exact):
        raise ValueError("query IDs differ")
    if exact_summary["blocked"] != 0 or exact_summary["candidate_failures"] != 0:
        raise ValueError("exact lane is incomplete or failed")
    failures = []
    for query_id in sorted(exact):
        a, b = candidate[query_id], exact[query_id]
        if _provenance(a, path=args.candidate) != _provenance(b, path=args.exact):
            raise ValueError(f"query provenance differs: {query_id}")
        if a["candidate_state"] in ("BLOCKED", "FAIL"):
            failures.append({"id": query_id, "kind": a["candidate_state"],
                             "reason": a.get("candidate_error")})
            continue
        af, bf = a["candidate_found"], b["candidate_found"]
        ad, bd = a["candidate_distance"], b["candidate_distance"]
        if af != bf or (af and abs(ad - bd) > TOLERANCE):
            failures.append({"id": query_id, "kind": "WRONG", "candidate_found": af,
                             "candidate_distance": ad, "exact_found": bf,
                             "exact_distance": bd})
    report = {
        "schema": "stellarcsg.frozen-oracle-comparison/v1",
        "candidate_jsonl_sha256": hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        "exact_jsonl_sha256": hashlib.sha256(args.exact.read_bytes()).hexdigest(),
        "candidate_summary": candidate_summary,
        "exact_summary": exact_summary,
        "matched_queries": len(exact), "failures": failures,
        "status": "FAIL" if failures else "PASS",
        "claim_boundary": "Agreement with this retained exact lane is a bounded-corpus result, not a general root-completeness proof.",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "matched_queries": len(exact),
                      "failure_ids": [item["id"] for item in failures]}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
