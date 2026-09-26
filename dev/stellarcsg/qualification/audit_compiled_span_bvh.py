"""Audit the compiled swept-span BVH for the two analytic shaped members.

This diagnostic validates the serialized in-memory BVH topology and box-union
relationships. It is deliberately not a solver/root or transport qualification.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import struct


PINNED_START_COMMIT = "52dbc175891838dfbf3e0b97808f354144a51e6e"
PINNED_HORNER_RECEIPT_SHA256 = (
    "763f0c48d7ac34967267da5832ce0dfd22bb14fd12b4b6f840fc1c8f6015f049"
)
PINNED_SPAN_BOXES_SHA256 = (
    "c14b80516f33ab741f2bc2a72d981c97f10955312c91af27489e1f066d4430f1"
)
PINNED_PRODUCTION_SOURCE_SHA256 = (
    "dd4db0fb66dda806f0061f67e4d3ad0b673c5a46d1598f667191016a2157c163"
)
PINNED_ANALYTIC_H5_SHA256 = (
    "39f77da5ab1fe427cce58b153e9b52cf8915e9973a9b8f3dfad5ab3b00a9e46d"
)
EXPECTED_MEMBER_SPANS = {2: 256, 3: 384}
BOX_PREFIXES = ("centerline", "conservative")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binary64(token: str) -> float:
    if not isinstance(token, str):
        raise ValueError("box endpoint is not a hexadecimal string")
    try:
        value = float.fromhex(token)
    except ValueError as error:
        raise ValueError(f"invalid hexadecimal endpoint {token!r}") from error
    if not math.isfinite(value):
        raise ValueError("nonfinite BVH endpoint")
    return value


def exact(token: str) -> Fraction:
    return Fraction.from_float(binary64(token))


def bits(token: str) -> bytes:
    return struct.pack(">d", binary64(token))


def read_box(record: dict, prefix: str) -> tuple[list[Fraction], list[Fraction]]:
    try:
        lower_tokens = record[f"{prefix}_lower_hex"]
        upper_tokens = record[f"{prefix}_upper_hex"]
    except KeyError as error:
        raise ValueError(f"missing {prefix} box field") from error
    if (not isinstance(lower_tokens, list) or not isinstance(upper_tokens, list)
            or len(lower_tokens) != 3 or len(upper_tokens) != 3):
        raise ValueError(f"invalid {prefix} box shape")
    lower = [exact(token) for token in lower_tokens]
    upper = [exact(token) for token in upper_tokens]
    for axis in range(3):
        if lower[axis] > upper[axis]:
            raise ValueError(f"inverted {prefix} box axis {axis}")
    return lower, upper


def read_dump(path: Path) -> dict[int, dict]:
    members: dict[int, dict] = {}
    with path.open(encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                member = int(record["member"])
                kind = record["record"]
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise ValueError(f"invalid BVH dump line {lineno}") from error
            bucket = members.setdefault(
                member, {"meta": None, "indices": None, "spans": {}, "nodes": {}})
            if kind == "meta":
                if bucket["meta"] is not None:
                    raise ValueError(f"duplicate metadata for member {member}")
                bucket["meta"] = record
            elif kind == "indices":
                if bucket["indices"] is not None:
                    raise ValueError(f"duplicate index vector for member {member}")
                bucket["indices"] = record
            elif kind == "span":
                span = record.get("span")
                if not isinstance(span, int) or span in bucket["spans"]:
                    raise ValueError(f"duplicate or invalid span on line {lineno}")
                bucket["spans"][span] = record
            elif kind == "node":
                node = record.get("node")
                if not isinstance(node, int) or node in bucket["nodes"]:
                    raise ValueError(f"duplicate or invalid node on line {lineno}")
                bucket["nodes"][node] = record
            else:
                raise ValueError(f"unknown BVH dump record {kind!r}")
    return members


def read_previous_boxes(path: Path) -> dict[tuple[int, int], dict]:
    rows = {}
    with path.open(encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                key = (int(row["member"]), int(row["span"]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                raise ValueError(f"invalid prior box row {lineno}") from error
            if key in rows:
                raise ValueError(f"duplicate prior box row {key}")
            rows[key] = row
    return rows


def bitwise_box_matches_prior(span: dict, prior: dict) -> int:
    checks = 0
    for new_name, old_name in (
            ("centerline_lower_hex", "lower_hex"),
            ("centerline_upper_hex", "upper_hex")):
        new_values = span.get(new_name)
        old_values = prior.get(old_name)
        if (not isinstance(new_values, list) or not isinstance(old_values, list)
                or len(new_values) != 3 or len(old_values) != 3):
            raise ValueError("malformed centerline box comparison")
        for new_token, old_token in zip(new_values, old_values):
            if bits(new_token) != bits(old_token):
                raise ValueError("compiled centerline box bit pattern differs")
            checks += 1
    return checks


def contained(parent: dict, child: dict, prefix: str) -> int:
    parent_lower, parent_upper = read_box(parent, prefix)
    child_lower, child_upper = read_box(child, prefix)
    checks = 0
    for axis in range(3):
        if parent_lower[axis] > child_lower[axis]:
            raise ValueError(
                f"{prefix} parent does not contain child lower axis {axis}")
        if parent_upper[axis] < child_upper[axis]:
            raise ValueError(
                f"{prefix} parent does not contain child upper axis {axis}")
        checks += 2
    return checks


def exact_union(parent: dict, children: list[dict], prefix: str) -> int:
    if not children:
        raise ValueError("cannot form an empty BVH union")
    parent_lower, parent_upper = read_box(parent, prefix)
    boxes = [read_box(child, prefix) for child in children]
    checks = 0
    for axis in range(3):
        expected_lower = min(box[0][axis] for box in boxes)
        expected_upper = max(box[1][axis] for box in boxes)
        if parent_lower[axis] != expected_lower:
            raise ValueError(f"{prefix} parent lower is not exact child union")
        if parent_upper[axis] != expected_upper:
            raise ValueError(f"{prefix} parent upper is not exact child union")
        checks += 2
    return checks


def validate_member(
    member: int,
    bucket: dict,
    previous: dict[tuple[int, int], dict],
) -> dict:
    expected_spans = EXPECTED_MEMBER_SPANS[member]
    meta = bucket["meta"]
    indices_record = bucket["indices"]
    spans = bucket["spans"]
    nodes = bucket["nodes"]
    if meta is None or indices_record is None:
        raise ValueError(f"member {member} is missing metadata or indices")
    expected_dataset = f"/coils/coil_00{member}"
    if (meta.get("dataset") != expected_dataset
            or meta.get("sample_count") != expected_spans
            or meta.get("span_count") != expected_spans):
        raise ValueError(f"member {member} metadata differs")
    if set(spans) != set(range(expected_spans)):
        raise ValueError(f"member {member} span coverage differs")
    if meta.get("node_count") != len(nodes) or not nodes:
        raise ValueError(f"member {member} node count differs")
    if set(nodes) != set(range(len(nodes))):
        raise ValueError(f"member {member} node indices are not contiguous")
    if meta.get("root") != 0:
        raise ValueError(f"member {member} root is not node zero")

    span_indices = indices_record.get("span_indices")
    if not isinstance(span_indices, list):
        raise ValueError(f"member {member} span index vector is missing")
    if (meta.get("index_count") != len(span_indices)
            or len(span_indices) != expected_spans):
        raise ValueError(f"member {member} span index count differs")
    if (any(not isinstance(value, int) for value in span_indices)
            or sorted(span_indices) != list(range(expected_spans))):
        raise ValueError(f"member {member} span indices are not a bijection")

    prior_keys = {(member, span) for span in range(expected_spans)}
    if not prior_keys.issubset(previous):
        raise ValueError(f"member {member} prior centerline boxes are incomplete")
    prior_bit_checks = 0
    for span_id, span in spans.items():
        for prefix in BOX_PREFIXES:
            read_box(span, prefix)
        prior_bit_checks += bitwise_box_matches_prior(
            span, previous[(member, span_id)])

    root = nodes[0]
    root_bit_checks = 0
    for new_name, root_name in (
            ("surface_lower_hex", "conservative_lower_hex"),
            ("surface_upper_hex", "conservative_upper_hex")):
        meta_values = meta.get(new_name)
        root_values = root.get(root_name)
        if (not isinstance(meta_values, list) or not isinstance(root_values, list)
                or len(meta_values) != 3 or len(root_values) != 3):
            raise ValueError(f"member {member} malformed root surface box")
        for meta_token, root_token in zip(meta_values, root_values):
            if bits(meta_token) != bits(root_token):
                raise ValueError(
                    f"member {member} root differs from surface bounds")
            root_bit_checks += 1

    state = [0] * len(nodes)
    indegree = [0] * len(nodes)
    internal_edges = 0

    def visit(node_id: int) -> None:
        nonlocal internal_edges
        if not 0 <= node_id < len(nodes):
            raise ValueError(f"member {member} child node index out of range")
        if state[node_id] == 1:
            raise ValueError(f"member {member} BVH contains a cycle")
        if state[node_id] == 2:
            return
        state[node_id] = 1
        node = nodes[node_id]
        count = node.get("count")
        first = node.get("first")
        left = node.get("left")
        right = node.get("right")
        if not all(isinstance(value, int)
                   for value in (count, first, left, right)):
            raise ValueError(f"member {member} node fields are not integers")
        leaf = count != 0
        if node.get("leaf") is not leaf:
            raise ValueError(f"member {member} leaf marker differs")
        for prefix in BOX_PREFIXES:
            read_box(node, prefix)
        if leaf:
            if not 1 <= count <= 4:
                raise ValueError(f"member {member} leaf size differs")
        else:
            if left == right or left == node_id or right == node_id:
                raise ValueError(f"member {member} invalid child topology")
            for child in (left, right):
                if not 0 <= child < len(nodes):
                    raise ValueError(
                        f"member {member} child node index out of range")
                indegree[child] += 1
                internal_edges += 1
                visit(child)
        state[node_id] = 2

    visit(0)
    if any(value != 2 for value in state):
        raise ValueError(f"member {member} contains unreachable BVH nodes")
    if indegree[0] != 0 or any(value != 1 for value in indegree[1:]):
        raise ValueError(f"member {member} BVH is not a rooted tree")

    slot_hits = [0] * len(span_indices)
    leaf_nodes = 0
    internal_nodes = 0
    containment_checks = 0
    union_checks = 0
    leaf_span_refs = 0
    for node_id in range(len(nodes)):
        node = nodes[node_id]
        count = node["count"]
        if count:
            leaf_nodes += 1
            first = node["first"]
            if first < 0 or first + count > len(span_indices):
                raise ValueError(f"member {member} leaf range escapes index vector")
            children = []
            for slot in range(first, first + count):
                slot_hits[slot] += 1
                span_id = span_indices[slot]
                children.append(spans[span_id])
                leaf_span_refs += 1
            for prefix in BOX_PREFIXES:
                for child in children:
                    containment_checks += contained(node, child, prefix)
                union_checks += exact_union(node, children, prefix)
        else:
            internal_nodes += 1
            children = [nodes[node["left"]], nodes[node["right"]]]
            for prefix in BOX_PREFIXES:
                for child in children:
                    containment_checks += contained(node, child, prefix)
                union_checks += exact_union(node, children, prefix)
    if any(hit != 1 for hit in slot_hits):
        raise ValueError(f"member {member} leaf index ranges overlap or leave gaps")
    if leaf_span_refs != expected_spans:
        raise ValueError(f"member {member} leaf span coverage differs")

    return {
        "spans": expected_spans,
        "nodes": len(nodes),
        "leaf_nodes": leaf_nodes,
        "internal_nodes": internal_nodes,
        "internal_edges": internal_edges,
        "leaf_span_references": leaf_span_refs,
        "prior_centerline_endpoints_bitwise": prior_bit_checks,
        "root_surface_endpoints_bitwise": root_bit_checks,
        "exact_rational_containment_inequalities": containment_checks,
        "exact_rational_union_endpoint_equalities": union_checks,
    }


def validate_provenance(args: argparse.Namespace) -> dict:
    hashes = {
        "bvh_dump": digest(args.bvh_dump),
        "span_boxes": digest(args.span_boxes),
        "horner_receipt": digest(args.horner_receipt),
        "helper_source": digest(args.helper_source),
        "header": digest(args.header),
        "production_source": digest(args.production_source),
        "analytic_h5": digest(args.h5),
        "auditor": digest(Path(__file__)),
    }
    if hashes["span_boxes"] != PINNED_SPAN_BOXES_SHA256:
        raise ValueError("prior compiled span box dump differs")
    if hashes["horner_receipt"] != PINNED_HORNER_RECEIPT_SHA256:
        raise ValueError("final Horner enclosure receipt differs")
    if hashes["production_source"] != PINNED_PRODUCTION_SOURCE_SHA256:
        raise ValueError("production swept-surface source differs")
    if hashes["analytic_h5"] != PINNED_ANALYTIC_H5_SHA256:
        raise ValueError("analytic swept HDF5 differs")
    horner = json.loads(args.horner_receipt.read_text(encoding="utf-8"))
    if (horner.get("schema") != "stellarcsg.compiled-horner-enclosure/v1"
            or horner.get("state")
            != "ALL_ANALYTIC_ROUNDED_HORNER_BOXES_ENCLOSE"
            or horner.get("member_spans") != {"2": 256, "3": 384}
            or horner.get("hashes", {}).get("boxes")
            != hashes["span_boxes"]
            or horner.get("hashes", {}).get("production_source")
            != hashes["production_source"]):
        raise ValueError("final Horner enclosure lineage differs")
    return hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bvh-dump", type=Path, required=True)
    parser.add_argument("--span-boxes", type=Path, required=True)
    parser.add_argument("--horner-receipt", type=Path, required=True)
    parser.add_argument("--helper-source", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")

    hashes = validate_provenance(args)
    dump = read_dump(args.bvh_dump)
    if set(dump) != set(EXPECTED_MEMBER_SPANS):
        raise ValueError("BVH dump member coverage differs")
    previous = read_previous_boxes(args.span_boxes)
    expected_prior = {
        (member, span)
        for member, count in EXPECTED_MEMBER_SPANS.items()
        for span in range(count)
    }
    if set(previous) != expected_prior:
        raise ValueError("prior span box coverage differs")

    results = {}
    totals = {
        "nodes": 0,
        "leaf_span_references": 0,
        "prior_centerline_endpoints_bitwise": 0,
        "root_surface_endpoints_bitwise": 0,
        "exact_rational_containment_inequalities": 0,
        "exact_rational_union_endpoint_equalities": 0,
    }
    for member in sorted(EXPECTED_MEMBER_SPANS):
        result = validate_member(member, dump[member], previous)
        results[str(member)] = result
        for key in totals:
            totals[key] += result[key]

    receipt = {
        "schema": "stellarcsg.compiled-span-bvh-audit/v1",
        "state": "ANALYTIC_COMPILED_BVH_TOPOLOGY_AND_UNIONS_AUDITED",
        "qualification": "NOT_SOLVER_PASS",
        "starting_commit": PINNED_START_COMMIT,
        "members": results,
        "totals": totals,
        "sha256": hashes,
        "claim_boundary": (
            "NOT_SOLVER_PASS: for analytic shaped members 2/3, this checks the "
            "serialized actual compiled span-BVH node/index topology, rooted-tree "
            "acyclicity, leaf span coverage without duplication, bitwise identity "
            "of leaf centerline boxes to the prior 640-span dump, and exact-rational "
            "containment plus union equality for child/leaf boxes. It does not "
            "execute or prove BVH traversal decisions, nearest-center selection, "
            "surface-root prefix completeness, arbitrary imported coils, physical "
            "fidelity, transport, or production readiness."
        ),
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        receipt["state"],
        receipt["qualification"],
        totals["nodes"],
        totals["leaf_span_references"],
    )


if __name__ == "__main__":
    main()
