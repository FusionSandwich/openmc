"""Focused schema and historical-bank tests for the frozen oracle comparator."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
COMPARATOR_PATH = ROOT / "qualification" / "compare_frozen_oracle.py"
SPEC = importlib.util.spec_from_file_location("compare_frozen_oracle", COMPARATOR_PATH)
COMPARATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(COMPARATOR)


REPORTS = ROOT / "reports" / "local-cont-20260925"


def load_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_records(path: Path, records: list[dict], *, allow_nonfinite: bool = False) -> None:
    path.write_text("".join(json.dumps(row, allow_nan=allow_nonfinite) + "\n" for row in records))


class FrozenOracleComparatorTests(unittest.TestCase):
    def test_retained_73_blocked_bank_and_legacy_wrong_ids(self) -> None:
        blocked = REPORTS / "same-span-prefix-bank-01" / "candidate-0.jsonl"
        exact = REPORTS / "strict-old-01" / "exact-reference-0.jsonl"
        rows, summary = COMPARATOR.read(blocked)
        self.assertEqual(73, summary["blocked"])
        self.assertEqual(160, len(rows))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "comparison.json"
            with mock.patch("sys.argv", [str(COMPARATOR_PATH), "--candidate", str(blocked),
                                          "--exact", str(exact), "--output", str(output)]):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(1, COMPARATOR.main())
            report = json.loads(output.read_text())
            self.assertEqual(73, sum(item["kind"] == "BLOCKED" for item in report["failures"]))

        old = REPORTS / "strict-old-01" / "oracle-0.jsonl"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "comparison.json"
            with mock.patch("sys.argv", [str(COMPARATOR_PATH), "--candidate", str(old),
                                          "--exact", str(exact), "--output", str(output)]):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(1, COMPARATOR.main())
            report = json.loads(output.read_text())
            self.assertEqual(["a03", "a06", "a08", "a15"],
                             [item["id"] for item in report["failures"]])

    def _assert_bad_input(self, mutation, *, target: str = "candidate", nonfinite: bool = False) -> None:
        source = (REPORTS / "same-span-prefix-bank-01" / "candidate-0.jsonl"
                  if target == "candidate" else
                  REPORTS / "strict-old-01" / "exact-reference-0.jsonl")
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp) / "input.jsonl"
            records = load_records(source)
            mutation(records)
            write_records(temp, records, allow_nonfinite=nonfinite)
            with self.assertRaises(ValueError):
                COMPARATOR.read(temp, exact=(target == "exact"))

    def test_nonfinite_found_distances_rejected_on_both_lanes(self) -> None:
        for target in ("candidate", "exact"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(target=target, value=value):
                    self._assert_bad_input(
                        lambda records, v=value: records[0].update(
                            candidate_found=True, candidate_distance=v),
                        target=target, nonfinite=True)

    def test_boolean_distance_and_found_flag_rejected(self) -> None:
        self._assert_bad_input(lambda records: records[1].update(candidate_distance=True))
        self._assert_bad_input(lambda records: records[0].update(candidate_found=1))

    def test_negative_distance_and_miss_with_distance_rejected(self) -> None:
        self._assert_bad_input(lambda records: records[1].update(candidate_distance=-1.0))
        self._assert_bad_input(lambda records: records[0].update(candidate_distance=0.0))

    def test_invalid_states_provenance_duplicates_and_summary_rejected(self) -> None:
        self._assert_bad_input(lambda records: records[0].update(candidate_state="MAYBE"))
        self._assert_bad_input(lambda records: records[0].pop("coefficient_hash"))
        self._assert_bad_input(lambda records: records[0].pop("source_sha256"))
        self._assert_bad_input(lambda records: records[1].update(id=records[0]["id"]))
        self._assert_bad_input(lambda records: records[-1].pop("cache_policy"))
        self._assert_bad_input(lambda records: records[-1].update(blocked=72))
        self._assert_bad_input(lambda records: records[-1].update(candidate_nearest_failures=1),
                               target="exact")
        self._assert_bad_input(lambda records: records[0].update(candidate_ok=False))
        self._assert_bad_input(lambda records: records[0].update(reference_state="UNKNOWN"))
        self._assert_bad_input(lambda records: records[0].update(coefficient_hash="bogus"))
        self._assert_bad_input(lambda records: records[0].update(source_sha256="bogus"))
        self._assert_bad_input(lambda records: records[0].update(category="forged"))
        self._assert_bad_input(lambda records: records[0].update(
            geometry_representation="exact_control_offset"))
        self._assert_bad_input(lambda records: records[0].update(id="replacement_0"))

    def test_exact_lane_rejects_blocked_query(self) -> None:
        self._assert_bad_input(lambda records: records[0].update(
            candidate_state="BLOCKED", state="BLOCKED"), target="exact")

    def test_duplicate_object_keys_rejected(self) -> None:
        source = REPORTS / "strict-old-01" / "exact-reference-0.jsonl"
        lines = source.read_text().splitlines()
        lines[0] = lines[0].replace('"candidate_found":false',
                                    '"candidate_found":true,"candidate_found":false')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.jsonl"
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                COMPARATOR.read(path, exact=True)

    def test_nonstandard_json_constant_rejected(self) -> None:
        source = REPORTS / "strict-old-01" / "exact-reference-0.jsonl"
        lines = source.read_text().splitlines()
        lines[0] = lines[0].replace('"candidate_distance":null',
                                    '"candidate_distance":NaN', 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonfinite.jsonl"
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(ValueError, "nonstandard JSON constant"):
                COMPARATOR.read(path, exact=True)


if __name__ == "__main__":
    unittest.main()
