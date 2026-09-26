"""Stdlib-only negative test for the compiled swept-span BVH auditor."""

from __future__ import annotations

import copy
import unittest

from audit_compiled_span_bvh import validate_member


def box(prefix: str, lower: tuple[float, float, float],
        upper: tuple[float, float, float]) -> dict:
    return {
        f"{prefix}_lower_hex": [value.hex() for value in lower],
        f"{prefix}_upper_hex": [value.hex() for value in upper],
    }


def synthetic_bucket() -> tuple[dict, dict]:
    spans = {}
    prior = {}
    indices = []
    nodes = {}
    for span_id in range(256):
        lo = float(span_id)
        hi = lo + 0.5
        record = {"record": "span", "member": 2, "span": span_id}
        record.update(box("centerline", (lo, 0.0, 0.0), (hi, 1.0, 1.0)))
        record.update(box("conservative", (lo - 0.25, -0.25, -0.25),
                          (hi + 0.25, 1.25, 1.25)))
        spans[span_id] = record
        prior[(2, span_id)] = {
            "member": 2,
            "span": span_id,
            "lower_hex": record["centerline_lower_hex"],
            "upper_hex": record["centerline_upper_hex"],
        }
        indices.append(span_id)

    next_node = 0

    def build(first: int, last: int) -> int:
        nonlocal next_node
        node_id = next_node
        next_node += 1
        count = last - first
        node = {
            "record": "node",
            "member": 2,
            "node": node_id,
            "left": 0,
            "right": 0,
            "first": 0,
            "count": 0,
            "leaf": False,
        }
        children = [spans[indices[slot]] for slot in range(first, last)]

        def union(prefix: str) -> dict:
            lows = [
                min(float.fromhex(child[f"{prefix}_lower_hex"][axis])
                    for child in children)
                for axis in range(3)
            ]
            highs = [
                max(float.fromhex(child[f"{prefix}_upper_hex"][axis])
                    for child in children)
                for axis in range(3)
            ]
            return box(prefix, tuple(lows), tuple(highs))

        node.update(union("centerline"))
        node.update(union("conservative"))
        nodes[node_id] = node
        if count <= 4:
            node["first"] = first
            node["count"] = count
            node["leaf"] = True
            return node_id
        middle = first + count // 2
        node["left"] = build(first, middle)
        node["right"] = build(middle, last)
        return node_id

    root = build(0, 256)
    assert root == 0
    root_box = nodes[0]
    bucket = {
        "meta": {
            "record": "meta",
            "member": 2,
            "dataset": "/coils/coil_002",
            "sample_count": 256,
            "span_count": 256,
            "index_count": 256,
            "node_count": len(nodes),
            "root": 0,
            "surface_lower_hex": root_box["conservative_lower_hex"],
            "surface_upper_hex": root_box["conservative_upper_hex"],
        },
        "indices": {
            "record": "indices",
            "member": 2,
            "span_indices": indices,
        },
        "spans": spans,
        "nodes": nodes,
    }
    return bucket, prior


class CompiledSpanBVHNegativeTest(unittest.TestCase):
    def test_corrupted_parent_box_is_rejected(self) -> None:
        bucket, prior = synthetic_bucket()
        validate_member(2, bucket, prior)
        corrupted = copy.deepcopy(bucket)
        corrupted["nodes"][0]["centerline_upper_hex"][0] = (0.25).hex()
        with self.assertRaisesRegex(ValueError, "does not contain"):
            validate_member(2, corrupted, prior)


if __name__ == "__main__":
    unittest.main()
