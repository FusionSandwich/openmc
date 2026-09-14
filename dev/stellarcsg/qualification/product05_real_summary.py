"""Reduce actual dispositions, not the replay recorder's exit code."""
import json
from pathlib import Path
import statistics


def main():
    root = Path(__file__).resolve().parents[3]
    campaign = root / "dev/stellarcsg/reports/product05/real-replay-01"
    def read(lane):
        return {r["id"]: r for r in map(json.loads, (campaign / f"{lane}-0.jsonl").read_text().splitlines()) if "id" in r}
    reference = read("exact_reference")
    output = {"status": "single_run_stress_not_transport", "reference_hits": sum(r["candidate_found"] for r in reference.values()), "lanes": {}}
    for lane in ["old", "experimental", "exact_reference"]:
        rows = read(lane)
        failures = []
        for key, row in rows.items():
            ref = reference[key]
            if row["candidate_state"] == "BLOCKED" or ref["candidate_state"] == "BLOCKED":
                failures.append({"id": key, "type": "BLOCKED_NOT_COMPARED"})
            elif row["candidate_found"] != ref["candidate_found"]:
                failures.append({"id": key, "type": "hit_disposition", "candidate": row["candidate_distance"], "reference": ref["candidate_distance"]})
            elif row["candidate_found"] and abs(row["candidate_distance"] - ref["candidate_distance"]) > 2e-8:
                failures.append({"id": key, "type": "root_distance", "candidate": row["candidate_distance"], "reference": ref["candidate_distance"]})
        output["lanes"][lane] = {"query_count": len(rows), "hit_count": sum(r["candidate_found"] for r in rows.values()),
                                "failures": failures, "single_bank_mean_ns": statistics.mean(r["candidate_distance_ns"] for r in rows.values())}
    (campaign / "summary.json").write_text(json.dumps(output, indent=2))
    print(json.dumps({k: {"queries": v["query_count"], "hits": v["hit_count"], "disagreements": len(v["failures"]), "single_bank_mean_ns": v["single_bank_mean_ns"]} for k, v in output["lanes"].items()}, indent=2))


if __name__ == "__main__":
    main()
