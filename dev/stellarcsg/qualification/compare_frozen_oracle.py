#!/usr/bin/env python3
"""Compare complete frozen-bank candidate and independent exact-lane JSONL."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def read(path: Path) -> tuple[dict[str, dict], dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    queries = [row for row in rows if row.get("kind") == "query"]
    summaries = [row for row in rows if row.get("kind") == "summary"]
    if len(queries) != 160 or len({row["id"] for row in queries}) != 160 or len(summaries) != 1:
        raise ValueError(f"incomplete or duplicate frozen bank: {path}")
    if summaries[0].get("query_count") != 160:
        raise ValueError(f"invalid summary: {path}")
    return {row["id"]: row for row in queries}, summaries[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--exact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    candidate, candidate_summary = read(args.candidate)
    exact, exact_summary = read(args.exact)
    if set(candidate) != set(exact):
        raise ValueError("query IDs differ")
    if exact_summary.get("blocked") != 0 or exact_summary.get("candidate_failures") != 0:
        raise ValueError("exact lane is incomplete or failed")
    failures = []
    for query_id in sorted(exact):
        a, b = candidate[query_id], exact[query_id]
        if a.get("coefficient_hash") != b.get("coefficient_hash") or a.get("source_sha256") != b.get("source_sha256"):
            raise ValueError(f"query provenance differs: {query_id}")
        if a.get("candidate_state") == "BLOCKED":
            failures.append({"id": query_id, "kind": "BLOCKED", "reason": a.get("candidate_error")})
            continue
        af, bf = a.get("candidate_found"), b.get("candidate_found")
        ad, bd = a.get("candidate_distance"), b.get("candidate_distance")
        if af != bf or (af and (not isinstance(ad, (int, float)) or
                                 not isinstance(bd, (int, float)) or abs(ad - bd) > 2e-8)):
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
