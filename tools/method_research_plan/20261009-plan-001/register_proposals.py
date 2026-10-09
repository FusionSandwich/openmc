"""Register a new immutable proposal snapshot; no scientific execution."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parents[1] / "method_documentation_audit" / "20261009-review-001"
CATALOG = AUDIT / "METHOD_RESULTS.json"
EXPECTED = "5f612261467a6b04949522b81dfb51f575d4d6192e693e88274f736fa35848fb"
assert hashlib.sha256(CATALOG.read_bytes()).hexdigest() == EXPECTED
catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
by_id = {m["id"]: m for m in catalog["methods"]}

COMMON = [
    "Freeze actual target, units, frames, mode conventions, source/bank and fidelity budget before a target claim",
    "Conservative actual-surface domain coverage; uncertain earlier prefixes cannot be pruned",
    "Complete first event and admitted owner/sense/normal/continuation/scoring semantics before native acceptance",
    "No scalar midpoint substitution for nonpoint polynomial isolating intervals",
    "Keep every unresolved/exception result and its full cost; no survivor-only bank timing",
    "Independent Sol review; local-first and existing user-wide resource/acquisition rules",
]

proposals = [
    {
        "id": "NEXT-G01", "domain": "shared", "priority": "prerequisite",
        "combination": "Target/input admission plus complete first-event, interval scheduling and ownership/scoring contract",
        "evidence_ids": ["M22", "M23", "R01", "R02", "R03", "Q01", "Q02"],
        "hypothesis": "Close the existing physical-identity and coupled event gaps without promoting unresolved reference results",
        "first_bounded_experiment": "Freeze existing witnesses; design independent event/owner/per-bin expected results and failure corruptions for each candidate's supported domain",
        "negative_controls": ["equal-time conflicting cube faces and reversed order", "2^-48 cm positive gap", "subnormal positive-gap mathematical reference", "P00 overlaps15/16 and17/18", "origin contacts and even/near tangencies", ".002 versus .502 cm missed earlier coil entry", "thin two-root pair near49.999909268 cm", "near-parallel lead/slab exclusions", "periodic seams/transforms", "reused-particle reset", "redistributed tally bins", "nonpoint interval midpoint false scalar HIT"],
        "promotion_requires": COMMON,
    },
    {
        "id": "NEXT-P01", "domain": "plasma", "priority": 1,
        "combination": "Incumbent bicubic spline plus validated closed ceilings, immutable enclosures/BVH and candidate-plan reuse",
        "evidence_ids": ["M04", "M12", "M22", "L07", "L12", "L13", "L14", "L15", "Q01"],
        "hypothesis": "Reduce full surface solves with actual-surface exclusion certificates and measure real cache reuse",
        "first_bounded_experiment": "Same admitted spline target/bank: ceiling off/on and candidate reuse off/on; independently verify every exclusion and complete query disposition",
        "metrics": ["complete-query cost including unknown/exception paths", "full-solver calls", "interval operations", "unresolved fraction", "cache hit/miss and invalidation", "preprocessing/memory", "normal/evaluate/sense parity"],
        "negative_controls": ["ceiling equality", "earlier unresolved interval with later known root", "inside/outside/near-boundary origins", "seams/tangencies", "wrong geometry/transform/ray/domain/ceiling/coincidence cache key", "sampled voxel clearance without whole-domain certificate", "M22 sense counterexample"],
        "promotion_requires": COMMON + ["Actual spline bounds/callback completeness; Q01 contracts alone insufficient", "Geometry-source identity bound alongside NEXT-P02's independent Fourier reference"],
    },
    {
        "id": "NEXT-P02", "domain": "plasma", "priority": 2,
        "combination": "Direct original vector-parametric VMEC/Fourier evaluator and certified parameter patches",
        "evidence_ids": ["H08", "I03", "FT-007", "Q01"],
        "hypothesis": "Measure whether evaluator savings remain at actual mode counts and under correct VMEC parameterization",
        "first_bounded_experiment": "Bind original coefficients/modes/units and independently verify reconstruction alongside NEXT-P01; evaluator/derivative ablation over mode counts with explicit spline approximation error",
        "metrics": ["evaluator/derivative cost separately from candidate search", "mode-count scaling", "source reconstruction discrepancy", "spline approximation discrepancy", "complete intersection work and unknown prefixes"],
        "negative_controls": ["physical n versus stored xn convention", "raw VMEC theta versus geometric theta", "high-mode m2048 missed crossing", "vector-grid singularity discarding earlier candidates", "folded/unsupported radial chart", "periodic seams", "silent spectral truncation"],
        "promotion_requires": COMMON + ["Admitted chart/parameter coverage and regularity; scalar radial specialization is not general VMEC", "Source reference starts alongside spline work, not after incumbent acceptance", "Any fallback evaluator represents an admitted equivalent target"],
    },
    {
        "id": "NEXT-P03", "domain": "plasma", "priority": 3,
        "combination": "Local full-quartic or torus candidates with Cartesian admission, exact polynomial reference and actual-target refinement",
        "evidence_ids": ["FT-003", "FT-004", "FT-007", "FT-008", "Q01", "Q02"],
        "hypothesis": "Candidate fits reduce completed actual-target work when their neighborhoods, competing intervals and prefixes are certified",
        "first_bounded_experiment": "Same admitted target/bank/domains: baseline, torus seeds, full35-coefficient quartic seeds; retain all actual-target refinement/prefix costs",
        "metrics": ["completed-query time", "candidate count and work", "fit conditioning", "extra-sheet rejects", "actual-boundary residual/enclosure", "seam/domain coverage", "unresolved fraction"],
        "negative_controls": ["extra quartic sheet near t.730003116 m / target field+.784203364 m", "angular trim without Cartesian neighborhood", "small residual near tangent not longitudinal bound", "polynomial miss with actual-target hit", "earlier unknown prefix", "nonpoint Q02 interval supplied as rounded scalar", "uncovered seam", "uncertain coefficients/ray-substitution roundoff"],
        "promotion_requires": COMMON + ["NEXT-G01 interval-valued scheduler review or explicit reference-only disposition", "Conservative actual-surface coverage; polynomial roots are not physical HIT", "Compare all arms on common target; old attempts0002/0003 targets differ"],
    },
    {
        "id": "NEXT-C01", "domain": "coils", "priority": 1,
        "combination": "P00 facets v2/v3/v5 ablation plus coupled event/owner repair and physical CAD binding",
        "evidence_ids": ["M14", "M15", "M23", "R01", "R02", "R03", "L04", "L05", "L06", "L08", "L10", "L11"],
        "hypothesis": "Retain represented-facet speed while closing actual first-event, continuation, physical-owner and fidelity defects",
        "first_bounded_experiment": "Replay R02/R03 owner/continuation/per-bin witnesses on bound payloads; independently admit v5 exclusion before an ablation or throughput claim",
        "metrics": ["earliest contacts and successor cell/material", "per-bin path/current", "crease/tie unresolved states", "CAD/section/frame/facet identity", "ceiling exclusion certificate", "corrected same-build transport/initialization and robust worst pair"],
        "negative_controls": ["facet-order-dependent owner/normal", "overlap pairs15/16 and17/18", "seam-repaired payload mistaken for original CAD", "tiny gap skipped by continuation", "normal at crease fails solid sense", "equal tallies with shared geometry defect", "v3 effect assumed additive", "bitwise equality mistaken for v5 exclusion proof"],
        "promotion_requires": COMMON + ["Physical owner/CAD binding covers cap repair and overlaps, not only hashes of18 selectors", "M23 restricted plane acceptance does not qualify general facets/materials", "Corrected candidate must remeasure; old timing1.1046 is not transferred automatically"],
    },
    {
        "id": "NEXT-C02", "domain": "coils", "priority": 2,
        "combination": "Admitted ruled rational cubic rectangular faces/endcaps with degree-six reference, certified hierarchy and full event ordering",
        "evidence_ids": ["M17", "M19", "Q01", "Q02"],
        "hypothesis": "A direct face representation avoids generic swept-offset stationary search on an admitted physical rectangular pack",
        "first_bounded_experiment": "Recover/bind M17 artifact or create a newly scoped one-span closed reference with known cubic/rational edges, positive denominators and endcaps",
        "metrics": ["all ray-ordered contacts", "degree/denominator admission", "endcap and incident-face coverage", "one-sided solid membership", "reference/complete-query cost", "actual section/frame/CAD fidelity"],
        "negative_controls": ["six crossings with parameter order reversed from ray order", "denominator zero/negative or uncertified clearing", "endpoint/even roots", "near-parallel rays", "missing endcap", "seam/crease/corner sense", "degree6 polynomial sent to degree4 Q02", "irrational interval midpoint false scalar HIT"],
        "promotion_requires": COMMON + ["Separately reviewed degree-six-capable reference; Q02 unchanged is insufficient", "NEXT-G01 interval-event scheduler gate or reference-only use", "Native nonvirtual sense/normal coupling admitted", "Actual CAD section/frame is not replaced with a circular approximation"],
    },
    {
        "id": "NEXT-C03", "domain": "coils", "priority": "conditional reference only",
        "combination": "Restricted constant-metric exact-control offset, certified Bernstein prefix, immutable interval cache and newly certified hierarchy",
        "evidence_ids": ["M11", "M12", "M13", "M16"],
        "hypothesis": "Retain a trustworthy restricted scalar reference and measure one combined workload only where its geometry domain is admitted",
        "first_bounded_experiment": "Only circular/constant planar-ellipse metric: retain nine normal gaps, add genuine imported hits and test full prefix/cache/hierarchy costs",
        "metrics": ["complete scalar outcomes and normals", "imported hit/entry/exit coverage", "full combined workload cost", "preprocessing/memory", "unknown/normal failure fraction"],
        "negative_controls": ["variable frame or rectangular pack admitted as constant metric", "miss-only imported bank mistaken for coil validation", "nine normal gaps omitted", "multiply4.052x and1.993x across differing denominators", "primitive ratio labeled native transport"],
        "promotion_requires": COMMON + ["Restricted reference remains distinct from physical rectangular pack", "No general physical/native claim from old160-query bank"],
    },
]

now = datetime.now(timezone.utc).isoformat()
for proposal in proposals:
    proposal["status"] = "PROPOSED_NOT_RUN"
    proposal["execution_result"] = None
    proposal["input_binding"] = "PENDING_PER_EXECUTION_FREEZE"
    proposal["evidence"] = [
        {"id": mid, "catalog_status": by_id[mid]["status"],
         "catalog_anchor": "../../method_documentation_audit/20261009-review-001/METHOD_RESULTS.md#" + mid.lower()}
        for mid in proposal["evidence_ids"]
    ]

registry = {
    "registered_utc": now,
    "kind": "immutable prospective experiment registry",
    "ranking_basis": "engineering judgment from retained evidence and implementation risk; not demonstrated future speed/success probability",
    "evidence_catalog": {"path": "../../method_documentation_audit/20261009-review-001/METHOD_RESULTS.json", "sha256": EXPECTED, "source_commit": "918161c09f24fc7fb14477e5f202ea89d2c67175"},
    "execution_authorized_by_this_record": False,
    "new_experiments_executed": 0,
    "acquisitions_or_builds": 0,
    "remote_launches": 0,
    "proposal_count": len(proposals),
    "preservation_rule": "New proposal revision uses a new plan directory; each execution/retry gets a fresh attempt/run directory and its append-only events. Historical attempts and this initial registry are not overwritten.",
    "proposals": proposals,
}
events = [{"recorded_utc": now, "event": "PROPOSAL_REGISTERED", "id": p["id"], "status": p["status"], "execution_result": None, "evidence_catalog_sha256": EXPECTED} for p in proposals]

for name in ["EXPERIMENT_REGISTRY.json", "EVENTS.jsonl"]:
    if (HERE / name).exists():
        raise FileExistsError("Preserved proposal record already exists: " + name)
with (HERE / "EXPERIMENT_REGISTRY.json").open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")
with (HERE / "EVENTS.jsonl").open("x", encoding="utf-8") as stream:
    stream.writelines(json.dumps(event, ensure_ascii=False) + "\n" for event in events)
print(json.dumps({"registered_proposals": len(proposals), "scientific_executions": 0, "catalog_sha256": EXPECTED}))
