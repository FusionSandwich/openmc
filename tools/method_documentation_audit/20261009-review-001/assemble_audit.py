"""Assemble an additive documentation review from preserved local records.

This reads records; it does not execute scientific methods or their tests.
Generated files are drafts until independent coverage review is recorded.
"""

import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CAT = json.loads((HERE / "document_catalog_final.json").read_text(encoding="utf-8-sig"))
CAT.extend(json.loads((HERE / "late_document_catalog.json").read_text(encoding="utf-8-sig")))
INV = json.loads((HERE / "source_inventory_final.json").read_text(encoding="utf-8-sig"))
BY_PATH = {p: d for d in CAT for p in d["copies"]}
METHODS = []
DATA = {}


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def evidence(path):
    if path in BY_PATH:
        doc = BY_PATH[path]
        return {"original_path": path, "sha256": doc["sha256"], "snapshot": doc["snapshot"]}
    source = ROOT / path
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    dest = "source_data/" + digest + source.suffix
    target = HERE / dest
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        assert target.read_bytes() == raw
    else:
        target.write_bytes(raw)
    item = {"original_path": path, "sha256": digest, "snapshot": dest, "bytes": len(raw)}
    DATA[path] = item
    return item


def add(mid, title, status, result, limitation, paths, category):
    METHODS.append({"id": mid, "method": title, "category": category,
                    "status": status, "recorded_result": result,
                    "limitations_or_negative_results": limitation,
                    "evidence": [evidence(p) for p in paths]})


def p(checkout, name):
    return checkout + "/dev/stellarcsg/reports/" + name


ASTRA = "stellarcsg-astra-kernel-20260926"
REPAIR = "stellarcsg-root-repair-07"
LADDER = "stellarcsg-workload-ladder-20261008"
PROTO = "stellarcsg-fourier-torus-prototype-20261009/tools/fourier_torus_prototype"
HISTORY = p("stellarcsg-fast-recovery-04", "FAST_RECOVERY_04_HISTORY.md")
RECOVERY = p("stellarcsg-fast-recovery-04", "FAST_RECOVERY_04_CHECKPOINT.md")
PRODUCT = p(REPAIR, "PRODUCT_05_CHECKPOINT.md")
R07 = p(REPAIR, "REPAIR_07_CHECKPOINT.md")
LRESULT = LADDER + "/RESULTS.md"
FLEDGER = PROTO + "/METHOD_LEDGER.md"

# Preserve all 32 rows of the previous broad ledger verbatim, with addenda.
old = (ROOT / "ai-review-handoff-20261008/METHODS_AND_FAILURES.md").read_text(encoding="utf-8-sig")
index = (ROOT / "ai-review-handoff-20261008/EVIDENCE_INDEX.md").read_text(encoding="utf-8-sig")
source_map = {}
for line in index.splitlines():
    match = re.match(r"\| (S\d+) \|", line)
    link = re.search(r"\]\((sources/[^)]+)\)", line)
    if match and link:
        source_map[match[1]] = "ai-review-handoff-20261008/" + link[1]

statuses = {
    "M01": "REFERENCE / INCOMPLETE GENERAL ROOT COVERAGE", "M02": "PARTIAL: EXACT ANALYTIC INPUTS",
    "M03": "PARTIAL; NATIVE SHAPED/HELICAL GATES NOT_RUN", "M04": "FAILED HISTORICAL GATE; LATER OPTIMIZATION DIAGNOSTICS",
    "M05": "PARTIAL ROUND-TUBE SPEED; PHYSICAL PACK UNQUALIFIED", "M06": "FAILED GENERAL SOLVER",
    "M07": "FAILED; FINAL PATCH UNRECOVERED", "M08": "BLOCKED / APPROXIMATION ONLY",
    "M09": "NOT ADMITTED; FINAL ARTIFACT UNRECOVERED", "M10": "REJECTED AUTHORITATIVE SOLVER",
    "M11": "ACCEPTED RESTRICTED SCALAR CORRECTNESS / INTERNAL SPEED", "M12": "ACCEPTED NARROW CACHE PATCH / PARTIAL SPEED",
    "M13": "PROPOSAL; REAL COMPILED AUDIT NOT_RUN", "M14": "HISTORICAL FAIL; LATER REPORTED TIMING PASS; PHYSICAL GATE OPEN",
    "M15": "PARTIAL FINITE CLASSIFICATION / CONFOUNDED TRANSPORT EFFECT", "M16": "PRO-REPORTED PROTOTYPE / PHYSICAL BINDING OPEN",
    "M17": "PRO-REPORTED SYNTHETIC REFERENCE; GENERAL NATIVE NOT_RUN", "M18": "PRO-REPORTED STANDALONE; PROOF UNACCEPTED",
    "M19": "PROPOSAL NOT_IMPLEMENTED", "M20": "PARTIAL PROOF INGREDIENT", "M21": "PROPOSAL / UNMEASURED",
    "M22": "REJECTED NORMAL/SENSE SHORTCUT; CACHE PROPOSAL UNBUILT", "M23": "ACCEPTED RESTRICTED DETERMINISTIC NATIVE EVENT SLICE",
    "I01": "PARTIAL MESH REFERENCES / DEBUG NEGATIVES", "I02": "HISTORICAL VERIFIED BACKEND; CURRENT TARGET NOT_RUN",
    "I03": "PARTIAL IMPORT; HELD-OUT FIT REJECTED", "I04": "PARTIAL INTERFACES; PHYSICAL PREDICTIONS FAILED",
    "I05": "PARTIAL FINITE NATIVE INTEGRATION", "I06": "PARTIAL EQUATOR REPAIR; TINY-TRACK NATIVE OPEN",
    "I07": "ACCEPTED NARROW IDENTITY/HDF REPAIR", "I08": "PARTIAL VALIDATOR/ADAPTER REPAIR",
    "I09": "OFFLINE PREPARATION PASS; ORIGINAL NATIVE MATRIX NOT_RUN",
}
for line in old.splitlines():
    if not re.match(r"\| [MI]\d{2} ", line):
        continue
    fields = [s.strip() for s in line.strip("|").split("|")]
    mid, title = fields[0].split(" ", 1)
    sources = [source_map[s] for s in re.findall(r"S\d+", fields[4])]
    add(mid, title, statuses[mid], fields[1], fields[2], sources, "Historical geometry" if mid.startswith("M") else "Reference and integration")
    METHODS[-1]["historical_ledger_row_verbatim"] = line
    METHODS[-1]["historical_disposition"] = fields[3]
    METHODS[-1]["historical_record_cutoff"] = "2026-10-01; packet prepared 2026-10-08"
    METHODS[-1]["current_addendum"] = None

by_id = {m["id"]: m for m in METHODS}
for mid, text, paths in [
    ("M23", "The October 1 configure timeout remains history. October 8 independent review and fresh integration accepted ONLY void, single-instance, unit-axis built-in plane events: 39 models / 208 rows / 154 supported / 54 expected rejections / 460 events. Integration replay matches the review rows and rejects five corrupt oracles. General facets, materials, physical performance and installation ABI remain outside acceptance.", ["stellarcsg-axis-review-20261008/AXIS_REVIEW_RESULT_20261008.json", "stellarcsg-axis-integration-20261008/INTEGRATION_RESULT_20261008.json"]),
    ("M14", "Later ladder gate-03 reports PASS_ROBUST on all three seeds; pooled P00/ring transport ratio 1.104614615471397. This is represented P00 versus fixed 30x30 cm rings, with independent physical/owner/native-event acceptance still open. Earlier 4.797639 failure, oracle conflicts and assembly failures remain. See L06/L10/L11 and R01/R02.", [LRESULT, LADDER + "/runs/gate-03/GATE.json"]),
    ("M04", "Later plasma ceiling variants report large improvements on the original unequal-source workload. More work-matched geometry-specific source diagnostics still give 2.100163 and 2.119799 custom/torus, above 1.25. They are different experiments, not a replacement replay of the 159.7233 failed gate. See L07/L14.", [LRESULT, LADDER + "/plasma/runs/plasma-matched-02/SUMMARY.json"]),
    ("I09", "The later ladder uses actual counting experiments and file rechecks; these are a separate scope from the original unimplemented 18-run census plan. Counting classifications do not independently certify the solver. See L01/L15.", [LRESULT]),
]:
    by_id[mid]["current_addendum"] = text
    by_id[mid]["evidence"].extend(evidence(x) for x in paths)

early = [
    ("H01", "Track B capsule/admissible seed recovery", "PARTIAL; WRONG ROOTS REMAIN", "81211f7b supplied an inside-capsule seed and recovered missed entry; later conditional-seed controls measured 1685.63 ns/query with 3 strict disagreements on the fresh 160 bank.", "Unsafe proxy pruning/completeness remain. Earlier-entry fix is not a first-root proof.", [HISTORY, RECOVERY]),
    ("H02", "Track A floating admissible seed and removal of unsafe proxy pruning", "PARTIAL; NOT COMPLETE", "4e1efc947 retained polynomial bank improved 273 PASS / 88 FAIL / 23 BLOCKED to 361 / 0 / 23; reported distance 2784.93 ns/query.", "Two tangent metamorphisms remain unresolved. Different bank from recovery04. Blocked domain and general native gates remain; prior-A fresh160 control still had 3 disagreements.", [HISTORY, RECOVERY]),
    ("H03", "Exact rational resultant/gcd/Sturm circular reference", "REFERENCE PASS IN RESTRICTED DOMAIN; TOO COSTLY", "da7a5417 exact elimination and nearest-stationary classification: retained 384 replay 256 PASS / 0 FAIL / 128 BLOCKED. Recovery04 exact control costs 14.41848849 ms/query on its separate 160 bank.", "Constant circular binary64 cubics only; elliptic/variable frames unsupported. Reference domain blocks are not enforced by recovered production.", [HISTORY, RECOVERY, p("stellarcsg-neutral-03", "CONTINUATION_20260913.md")]),
    ("H04", "Shared exact-query reuse and exact-work accounting", "PARTIAL REUSE / DIAGNOSTIC", "223ea7a1 reuses common exact query work and exposes exact cost.", "Reuse benefit is not cold-query or native throughput; retain bank and warm/cold distinctions.", [HISTORY]),
    ("H05", "Outward floating BVH and Bernstein sign exclusion before exact solve", "PARTIAL; SPEED INCONCLUSIVE", "0b56166b conservatively retains uncertain intervals before the exact solver.", "Aggregate speed gain inconclusive; distinct from failed original degree-ten solver and later 2-D interval cover.", [HISTORY]),
    ("H06", "Exact-rational monotone isolation before gcd/Sturm", "REFERENCE-CONSISTENT INTERNAL SPEED", "dc76fbd1 / 5ed327ad: 64 mode comparisons identical, 384 replay 256/0/128. Separate 16-ray bank: mode2 2.1309001 ms vs mode0 82.4534045 ms; 1000-history diagnostic 7.05622 histories/s.", "98.213% of instrumented time remains exact work. No arbitrary-precision-free/general fast transport claim.", [HISTORY, p("stellarcsg-neutral-03", "CONTINUATION_20260913.md")]),
    ("H07", "Old plasma source reproduction versus current implementation", "COMPLETED MATCHED DIAGNOSTIC", "Same-workload old source 27.225501 s versus current 28.970192 s; ratio 1.064083. Whitespace-normalized source bodies agree.", "Old boundary handling unsafe; diagnostic is not promotion. Unlike historical workloads cannot establish a 0.36-to-35-second regression.", [p(ASTRA, "plasma-best-time-20260926/METHOD_COMPARISON_REBUILD_010.md"), p(ASTRA, "plasma-best-time-20260926/source-rebuild-010-01/comparison.json")]),
    ("H08", "Adaptive VMEC radial spline fit and single-chart admission", "SAMPLED FIT SELECTED; GENERAL ADMISSION PARTIAL", "Auto-fit errors: 64x32 7.8086% REJECT, 128x64 1.22134% REJECT, 256x128 0.099667% selected under declared 1% sampled target. Independent4608 grid max0.2042205 cm / 0.119736% local radius, RMS0.018439 cm, P95 0.030255 cm.", "Initial separate off-grid64x32 result 11.33767 cm / 8.16553% fails. Geometric-theta folds including held-out ParaStell rejected; sampled radial error is not normal/volume/Hausdorff certificate or periodic navigation.", [PRODUCT, "stellarcsg-neutral-03/dev/stellarcsg/test_data/local_catalog/LOCAL_STELLARATOR_MODEL_CATALOG.md"]),
    ("H09", "Candidate A outward 2-D Bernstein interval-cover exclusion", "CONDITIONALLY APPROVED EXCLUSION; HOT PATH REJECTED", "Executed Product05 bank: 90 ROOT_FREE / 70 UNRESOLVED, no saved-bank false exclusions; approximately106397 ns/query.", "Certifies only stationary-equation exclusion under stated assumptions; no exact fallback, hit ordering or full solver. Too costly/incomplete for production.", [PRODUCT, R07]),
    ("H10", "Final-iterate residual recomputation", "REJECTED AS COMPLETE REPAIR", "Repair07 strict bank1728.125 ns/query,3 wrong/0 blocked; real stress15 discrepancies. Exposes real23 false finite hit0.19916695971482617 cm where exact reports no hit.", "Bookkeeping fix cannot prove a root; no correctness gain over seed control.", [R07]),
    ("H11", "Process all queued nearer unresolved spans", "REJECTED FOR PROMOTION", "Strict3266.25 ns/query,3 wrong/0 blocked; fixes no observed discrepancy;2.8683x old-fast. Stress15 discrepancies.", "Zero-proxy and solved-prefix completeness still open; negative commit retained.", [R07]),
    ("H12", "Broad crossing conditioning", "EXPERIMENTAL OVERBLOCKING", "Strict0 wrong /21 BLOCKED.", "Blocked-query time absent; survivor means cannot be full-bank speed. Regression tests fail with unresolved exceptions.", [R07]),
    ("H13", "Broad crossing conditioning plus outward center/radius bounds", "EXPERIMENTAL OVERBLOCKING", "Strict0 wrong /17 BLOCKED, reduced from21 without a new block. Per-operation outward propagation replaced rejected one-nextafter conversion.", "Whole-span regularity/frame evaluation/pruning coverage unadmitted; bounds are conditionally sound for ideal regular spline, not production proof.", [R07]),
    ("H14", "Narrow acceptance plus ordering and bounds", "REJECTED FOR PROMOTION", "Strict4726.25 ns/query,2 wrong/0 blocked,4.15x old. a15 distance error improves to about1.1e-11 cm. Stress12 wrong plus3 BLOCKED.", "a06 origin and a08 even tangent remain silent wrong no-hits; retained256 admitted replay still2 failures and128 reference blocks.", [R07]),
    ("H15", "Isolated narrow acceptance repair", "EXPERIMENTAL; NOT PROMOTED", "Strict2319.375 ns/query,2 wrong/0 blocked; interleaved confirmation2422.5 ns/query. Old-fast ratio ranges1.89–2.04 across campaigns; a15 improvement retained without ordering/bounds additions.", "2x timing guardrail straddled; correctness independently prevents promotion. Stress12 wrong plus3 BLOCKED, not only12 failures. Native new repair NOT_RUN.", [R07]),
    ("H16", "Recovered-seed clipped one-period native transport versus old and exact", "COMPLETED DIAGNOSTIC; PERIODIC MODEL UNQUALIFIED", "RunCompare06: old8387.7 vs recovered8179.8 histories/s (3x8192); exact8.4200 vs recovered7360.5 histories/s on separate3x256 workload. All24 primary attempts exit0. Seed19 64-history replay234 steps has zero discrete sequence changes.", "90-degree vacuum clipping,16 finite1cm diagnostic members. Tally threshold exceedances25(debug),16(256),4(8192); floating coordinates differ. Strict3/160, retained2/256, stress14/160 persist. No periodic qualification or matched Embree/native-torus ratio.", [p(REPAIR, "RUN_COMPARE_06_CHECKPOINT.md")]),
]
for row in early:
    add(*row, category="Earlier recovery and exact-reference variants")

composite = p("openmc-stellarcsg-composite", "COMPOSITE_BLANKET_INTEROP_FINAL_REPORT.md")
add("B01", "Physical-normal multilayer blanket compiler", "PARTIAL GEOMETRY; WISTELL ENGINEERING CLEARANCE FAIL", "Six layers totaling 135.5 cm, with seven boundaries per model (14 across the exact-torus and WISTELL controls): positive Jacobians, nesting and seam checks reported.", "Minimum coil clearance −37.1463 cm FAIL. Earlier blanket-not-implemented report is an earlier milestone; nonuniform coil-constrained/scaling/full physical qualification NOT_RUN.", [composite, p(ASTRA, "BLANKET_FAMILY_REPORT.md")], "Blanket and composite variants")
add("B02", "Combined native plasma, blanket and coil model with Boolean cutouts", "PARTIAL SMOKE / PARTITION", "7 blanket boundaries and12/48 coils; zero lost particles; native smoke3331.0/2762.19 histories/s, one repetition. TrackA later reproduction3436.33/2440.47 histories/s.", "Cutout partition does not remedy engineering clearance; smoke rates not medians. Multithreading/materialized closure/general physical pack qualification NOT_RUN.", [composite, p("stellarcsg-cont-a", "TRACK_A_LEGACY_V2_REPORT.md")], "Blanket and composite variants")
add("B03", "Native CSG outer fill with fine DAGMC torus hybrid", "PARTIAL INTEROPERABILITY / HISTORICAL VERIFIED EMBREE", "Ordinary DAGMC and genuine DoubleDown hybrid smokes; reported32 interoperability checks. Cached exact swept torus724869 vs690434 histories/s,1.04987x. Exact periodic711268 vs696970,1.02051x with lower bootstrap0.97647 meets3% noninferiority control.", "Forced-general swept path0.09951x FAIL. Rigid payload transforms unsupported. C1 ellipse/C3 racetrack/C4 capsule chains and full WISTELL verified-Embree comparison NOT_RUN.", [composite, p("openmc-stellarcsg-composite", "DOUBLE_DOWN_COMPOSITE_RESULTS.md"), p("openmc-stellarcsg-composite", "EXACT_TORUS_PARITY_FINAL.md")], "Blanket and composite variants")

add("R01", "Exact represented-facet topology and component-AABB certificate", "CONDITIONAL REPRESENTED-SOLID PREMISE; OWNER COUNTEREXAMPLES", "Derived3348 facets/18selectors: exact nonzero triangles, links, orientation and25431 pair predicates support embedded bounded components; derived1944 sampled classifications agree. Mesh-to-mesh displacement bound0.0033287735930590413 cm.", "8 exact cross-component intersection segments in15/16 and17/18; selectors are priority partition, not disjoint physical-coil owners. No continuous CAD/floating operational theorem.", [p(ASTRA, "P00_STEP2_CERTIFICATE_20261001.md")], "P00 geometry and event diagnostics")
add("R02", "Independent rational facet first-event oracle", "COUNTEREXAMPLES_FOUND", "810-query authoritative_03:537 MATCH,116 EXPECTED_UNRESOLVED,154 CONSERVATIVE_UNRESOLVED,3 FAIL. P00 subset738 has495/93/150/0; cube72 has42/23/4/3. Exact equal-time contacts expose facet-order-dependent owner/normal.", "Do not count154 conservative unresolved as successful resolved queries. _01 self-test failure and _02 two-failure800-query run retained. Exit1 means found counterexamples, not failed execution.", [p(ASTRA, "P00_STEP3_REPORT_20261001.md")], "P00 geometry and event diagnostics")
add("R03", "Native assembly and positive-gap localization", "FAILED GENERAL EVENT/SCORING GATE", "680 queries on both libraries:21 first-event discrepancies/library,85 continuation aborts/library (74analytic/11derived). Focused planes show successor skips a real2^-48 cm positive gap.", "Later M23 accepts only a repaired restricted plane slice; these facet/material/general ownership failures are not automatically closed.", [p(ASTRA, "P00_ASSEMBLY_REPORT_20261001.md"), p(ASTRA, "P00_ASSEMBLY_PLANES_FOCUSED_RESULT_20261001.md")], "P00 geometry and event diagnostics")

ladder_rows = [
    ("L01", "Density ladder with collision workload matching", "LADDER01 INCONCLUSIVE; LADDER02 GEOMETRY_BOUND", "Both32-run phases complete. Quiet ladder02 reports236/236 checker results: thin ratio1.658(1.605–1.708), dense1.850(1.758–1.913), workload F1.156; nominal4.06x collision difference.", "Ladder01 noise/CV/drift gates fail; descriptive times cannot be accepted. Geometry/source workload differ; comparison not physical pack qualification.", [LRESULT, LADDER + "/ATTEMPTS.jsonl", LADDER + "/PLAN.md"]),
    ("L02", "Transport stack profiling and plasma workload attribution", "COMPLETED DIAGNOSTIC", "P00 samples: facet distance57%, contains/parity28%, normal10%; nextafter innermost30.9%; physics2–3%. Plasma profile95% distance solver,55% evaluations tangent scan. Original256 source sites all same point inside custom/outside torus:68.4027 vs5.4117 collisions/source.", "Sample percentages overlap and must not be added. Approx12.6x original collision workload is not geometry speed; original quiet plasma ratio199.9856.", [LRESULT]),
    ("L03", "v1 inline nextafter with std::memcpy bit casts", "REJECT_EFFECT", "Reported1.05x; -fno-builtin emits memcpy@plt calls.", "Failed pre-registered effect threshold; preserve failed implementation alongside later repair.", [LRESULT]),
    ("L04", "v2 inline nextafter with __builtin_memcpy bit casts", "REPORTED ACCEPT_SPEEDUP_EVIDENCE", "Reported1.65748x; tested seeds/densities bitwise equal in ab02/xval01.", "Finite output agreement and internal effect evidence; independent physical/native-event acceptance open.", [LRESULT]),
    ("L05", "v3 normal precompute and exact early reject", "UNDECIDED EFFECT", "Reported additional1.07603x, tested outputs bitwise equal.", "Below pre-registered1.10 effect threshold; no acceptance inferred from composition.", [LRESULT]),
    ("L06", "P00 gate01 with v2+v3", "PASS_MEDIAN; ROBUST WORST PAIR FAILS", "Three-seed medians1.212/1.211/1.178, pooled1.20060445.", "Worst pairings1.27–1.28 exceed1.25. This median pass is distinct from later robust pass.", [LRESULT, LADDER + "/runs/gate-01/GATE.json"]),
    ("L07", "v4 opt-in plasma collision-distance ceiling", "REPORTED ACCEPT_SPEEDUP_EVIDENCE", "Reported8.07x(7.86–8.51);12 gate runs bitwise equal; original unequal-source custom/torus195.935→23.833.", "No independent root/exclusion certificate acceptance. Unequal point-source workload; more matched diagnostic still over1.25.", [LRESULT, LADDER + "/plasma/runs/plasma-ab-01/SUMMARY.json"]),
    ("L08", "v5 facet distance ceiling", "FINITE BITWISE CONTROLS PASS", "v5+v6 composition retains equality across12 gate and5 cross-validation runs.", "No isolated individual v5 speed effect established; native event/physical owner caveats remain.", [LRESULT]),
    ("L09", "v6 exact periodic-spline indexing", "FINITE BITWISE CONTROLS PASS", "v5+v6 composition retains equality across12 gate and5 cross-validation runs.", "No isolated individual v6 speed effect established; equality only for tested records.", [LRESULT]),
    ("L10", "P00 gate02 with v2–v6 and ceiling", "INVALID OVERALL", "Seeds1742/1743 PASS_ROBUST; pooled1.108598 descriptive.", "Seed1741 first-run outlier/CV6.8% invalidates overall timing decision. Later warmup replication is a separate attempt.", [LRESULT, LADDER + "/runs/gate-02/GATE.json"]),
    ("L11", "P00 gate03 warmup-discarded replication", "REPORTED PASS_ROBUST TIMING ONLY", "All3 seeds PASS_ROBUST; pooled1.104614615471397; medians1.126/1.117/1.071, worst1.138/1.122/1.087.", "Derived P00 versus fixed30x30 cm rings, all tested tally bits unchanged. Continuous CAD/section/frame fidelity, physical ownership, event semantics and independent Sol physical acceptance remain open.", [LRESULT, LADDER + "/runs/gate-03/GATE.json", LADDER + "/GATE_PLAN.md"]),
    ("L12", "v7 exact value-only plasma evaluation", "UNDECIDED; NO MEASURABLE EFFECT", "Reported1.004x, finite bitwise equality.", "Distinct from rejected M22 normal/sense shortcut; no speed acceptance.", [LRESULT]),
    ("L13", "v8 voxel clearance fast path", "UNDECIDED EFFECT", "Reported1.139x with band1.092–1.216; tested outputs bitwise equal; initialization+0.39 s.", "Band crosses1.10 effect threshold. No independent clearance/root oracle acceptance.", [LRESULT]),
    ("L14", "Plasma geometry-specific uniform-source diagnostics", "IMPROVED; NATIVE 1.25 TARGET STILL MISSED", "51.619 vs60.589 collisions/source: control custom/torus15.8100→v2–v7 2.100163043577142; v2–v8 2.1197992495895623.", "Source banks and solids differ; closer collision workload is not identical physical geometry. Do not overwrite older proxy failure or compare unrelated absolute times.", [LRESULT, LADDER + "/plasma/runs/plasma-matched-01/SUMMARY.json", LADDER + "/plasma/runs/plasma-matched-02/SUMMARY.json"]),
    ("L15", "Plasma ceiling counters and matched profile", "REPORTED DIAGNOSTIC; ORACLE VALIDATION OPEN", "Implementation records92–95% ceiling_certified distance calls; full solver4.4 calls/history≈45% time.", "Counter label is implementation classification, not independent mathematical certification; allocation/profiling coverage does not prove all queries.", [LRESULT]),
]
for row in ladder_rows:
    add(*row, category="Later workload and optimization experiments")

QBASE = "stellarcsg-axis-integration-20261008/dev/stellarcsg/experiments/query_combinations_20261009"
add("Q01", "Exact candidate hierarchy, closed ceiling, query reuse and root scheduling composition", "ACCEPTED_REFERENCE_COMPOSITION_ONLY", "20 supplied controls and120 plane queries pass;12-arm hierarchy/ceiling/reuse ablation replay matches. Independent reviewer200 geometries/2400 exact multi-root resolutions plus malformed/alias/cache challenges pass.", "Caller must certify real-geometry AABBs and callback earliest-root completeness. No native OpenMC solver, physical acceptance or timed speedup. Earlier/equal unresolved preserves UNRESOLVED; provisional contacts not certified owners.", [QBASE + "/README.md", QBASE + "/results.json", QBASE + "/independent_review.json"], "Query composition reference")
KBASE = "stellarcsg-axis-integration-20261008/dev/stellarcsg/experiments/quartic_combinations_20261009"
add("Q02", "Exact rational quartic Sturm root isolation with conservative scalar scheduler", "ACCEPT_SCOPED_REFERENCE", "New degree-at-most-four oracle: 10 supplied controls, 386 independent known-factor cases, 1454 one-sided counts, three irrational cases and 20 scheduler compositions. Separate retained 59-control replay receipt passes and reproduces all three Fourier negative cases; reviewer audited that receipt without rerunning the complete replay.", "COMPLETE means distinct roots of supplied exact represented coefficients on a finite closed interval, not physical HIT. Budget exhaustion/all-zero polynomial remain UNRESOLVED; nonpoint intervals do not become scalar HIT. Coefficient uncertainty, actual-surface equivalence, trims, owner identity, native throughput and real VMEC remain unaccepted.", [KBASE + "/README.md", KBASE + "/replay_results.json", KBASE + "/independent_review.json"], "Query composition reference")

fourier_rows = [
    ("FT-001", "Fourier displacements added to a reference torus", "SYNTHETIC RECONSTRUCTION PASS", "Exact one-harmonic reconstruction control.", "General intersection remains coupled; no production solver."),
    ("FT-002", "Global torus fit, coefficient bounds and quartic candidates", "SCOPED CONTROLS PASS; GENERAL QUERIES UNRESOLVED", "Attempt0001 10 controls; endpoint-sign counterexample(t−.1)(t−.2)(t−.8) preserved and corrected by external single-root contract.", "Requires external exclusion/single-root certificates; candidate is not HIT; no general Fourier certificate generator."),
    ("FT-001-B", "Boolean combinations of complete coaxial torus solids", "RESTRICTED FAMILY COUNTEREXAMPLE; NOT_EXECUTED", "Rotational symmetry prevents representing the proposed nonaxisymmetric target in this restricted family.", "No new Boolean compiler executed; displaced/trimmed constructions are different."),
    ("FT-001-C", "Nonlinear coordinate map to a reference torus", "PROPOSAL NOT_IMPLEMENTED", "Interpretation documented.", "Transformed rays curved; lengths, normals and complete intersection unresolved."),
    ("FT-003", "Fourier-guided osculating torus patch atlas", "APPROXIMATION; NO CLOSED SOLID", "Sampled distance to the full fitted torus 8.927→1.185 mm and sampled projected-neighbor gap 14.326→1.932 mm with refinement; local admitted curvatures matched.", "This is not positional correspondence error or distance to the admitted trim. Projected patches have gaps; no trim-coverage certificate or closed solid/event qualification."),
    ("FT-004", "Constant-weight torus polynomial sums compiled to quartic", "COMPILATION PASS; LIMITED FIT", "Degree remains4; circular-torus coefficient family rank saturates14; tested global candidates radial errors125.96/159.68 mm.", "Finite-dimensional family cannot supply progressively complete Fourier basis; not physical admission."),
    ("FT-005", "Torus plateaus plus localized cubic-Hermite joins in one hierarchy", "C1 SYNTHETIC CONSTRUCTION; QUERIES UNRESOLVED", "N48 errors21.109/16.808/10.970 mm for strip fractions.1/.3/.6.", "Torus interiors inaccurate; narrow strips concentrate normal error. Candidate workload differs from hit frequency."),
    ("FT-006", "All-spline synthetic periodic-radius comparator", "SAMPLED ACCURACY IMPROVES; QUERIES UNRESOLVED", "N48 sampled error0.007575 mm on attempt0002 target; all624 general query rows across attempt0002 methods UNRESOLVED.", "New comparator, not incumbent. Exact tangent missed by sampled search; negative evidence retained."),
    ("FT-007", "Direct radial Fourier versus frozen incumbent bicubic evaluator", "SCOPED SYNTHETIC DIAGNOSTIC; QUERIES UNRESOLVED", "Attempt0003 run00229 controls; 76-ray median Python cost direct.2629 s vs bicubic.8587–.8831 s≈3.3x. Known24 candidates retained; direct maxerror8.88e−16 m vs spline3.276/.1128/.006464 mm. Same-parameter4745-point spline errors3.466/.1452/.008117 mm.", "All304 general query rows UNRESOLVED. Synthetic physical n[0,3,−6], geometric theta not raw VMEC theta. m2048 crossing missed despite78 candidates; tube-axis evaluation singularity preserved; no native speed claim."),
    ("FT-008", "Full35-coefficient local algebraic quartic fits", "APPROXIMATE ATLAS; NO CLOSED SOLID", "96/384patch holdout normal-line errors.3056/.01187 mm; midpoint seams.2045/.01271 mm; rank35, condition4.49e5/2.54e6.", "Periodic seams unassessed; angular trim admits extra quartic sheet(t.730003,target field.7842 m). No complete root/owner certificate."),
]
for row in fourier_rows:
    mid = row[0]
    if mid in {"FT-001", "FT-002", "FT-001-B", "FT-001-C"}:
        extra = [PROTO + "/attempts/0001-initial-20261009/receipt.json"]
    elif mid in {"FT-007", "FT-008"}:
        extra = [PROTO + "/attempts/0003-direct-fourier-algebraic-20261009/run-002/receipt.json", PROTO + "/attempts/0003-direct-fourier-algebraic-20261009/independent_review.json"]
    else:
        extra = [PROTO + "/attempts/0002-patch-hybrid-20261009/run-001/receipt.json", PROTO + "/attempts/0002-patch-hybrid-20261009/independent_review.json"]
    add(*row, paths=[FLEDGER] + extra, category="Fourier, toroidal patch and hybrid trials")

# Improve spacing in compact source-derived numeric notes without changing IDs.
for m in METHODS:
    for key in ["recorded_result", "limitations_or_negative_results", "current_addendum"]:
        if m.get(key):
            text = m[key]
            text = re.sub(r"\b(all|both|inside|outside|approximately|about|ratio|Strict|strict|stress|Stress|cost|mean|additional|reviewer|bank|grid|Independent|independent|and|versus|plus|remain|across|controls|errors|factor|point|derived|raw|subset|cube|query|members|rays|repairs|polynomial|geometry|selected|no|control|control:|native|wrong|PASS|swept|periodic|sampled|degree|coils|models|elapsed|cm|mm)(?=\d)", r"\1 ", text)
            text = re.sub(r"(?<=\d)(?=(?:cm|mm|ms|ns|queries|query|patch|facets|selectors|rows|controls|members|planes|geometries|histories|source|cases|points|gate|BOUND)\b)", " ", text)
            text = re.sub(r"(?<=[:;,])(?=[A-Za-z0-9])", " ", text)
            m[key] = text
assert len(METHODS) == 81, len(METHODS)
assert len({m["id"] for m in METHODS}) == len(METHODS)
dump("METHOD_RESULTS.json", {"review_date": "2026-10-09", "scope": INV["scope"],
     "not_a_count_of_unique_experiments": True, "method_variant_or_proposal_entries": len(METHODS),
     "preserves_historical_ledger_rows": 32, "methods": METHODS})
dump("source_data_manifest.json", list(DATA.values()))


def mdcell(value):
    return value.replace("|", "\\|").replace("\n", " ")


def links(items):
    unique = {x["snapshot"]: x for x in items}
    return ", ".join("[" + Path(x["original_path"]).name + "](" + x["snapshot"] + ")" for x in unique.values())


intro = """# StellarCSG method and result catalog

Reviewed October 9, 2026 from retained local documentation, with a final late capture at 22:11:43 UTC. **81 entries** cover methods, individual repair/optimization variants, references and unexecuted proposals; this is not a count of 81 independent experiments.

The 32 M/I entries preserve the October 8 ledger's original rows in `METHOD_RESULTS.json`. Current addenda qualify later evidence without deleting the earlier outcomes. New H/B/R/L/Q/FT entries expose attempts that were missing or aggregated. All quantitative results below are historical records reviewed here, not new scientific reruns.

Status meanings: **PARTIAL** is useful in the stated domain; **FAILED/REJECTED** records a failed gate; **UNRESOLVED** is not HIT or NO_HIT; **NOT_RUN/NOT_IMPLEMENTED** establishes no execution; **REPORTED** is source-reported evidence, without new independent physical acceptance. A restricted independent acceptance stays restricted.

Navigation: [audit findings](AUDIT_FINDINGS.md), [all 309 distinct Markdown records](DOCUMENTATION_INDEX.md), [machine-readable catalog](METHOD_RESULTS.json), [original October 8 ledger](""" + BY_PATH["ai-review-handoff-20261008/METHODS_AND_FAILURES.md"]["snapshot"] + ").\n"
out = [intro]
out.append("\n## Entry index\n\n| ID | Method or variant | Current status |\n| --- | --- | --- |\n")
for m in METHODS:
    # Explicit stable anchors below avoid renderer-specific Unicode slugs.
    out.append(f"| [{m['id']}](#{m['id'].lower()}) | {mdcell(m['method'])} | {mdcell(m['status'])} |\n")
categories = list(dict.fromkeys(x["category"] for x in METHODS))
for category in categories:
    out.append("\n## " + category + "\n\n")
    for m in METHODS:
        if m["category"] != category:
            continue
        out.append('<a id="' + m["id"].lower() + '"></a>\n\n')
        out.append("### " + m["id"] + " — " + m["method"] + "\n\n")
        out.append("**Status:** " + m["status"] + ".\n\n")
        out.append("**Recorded result:** " + m["recorded_result"] + "\n\n")
        out.append("**Failures and limits:** " + m["limitations_or_negative_results"] + "\n\n")
        if m.get("current_addendum"):
            out.append("**Later evidence (earlier result retained):** " + m["current_addendum"] + "\n\n")
        out.append("**Evidence:** " + links(m["evidence"]) + ".\n")
(HERE / "METHOD_RESULTS.md").write_text("".join(out), encoding="utf-8")

# Index every distinct document, including contextual reports and divergent copies.
refs = {}
for m in METHODS:
    for e in m["evidence"]:
        refs.setdefault(e["sha256"], set()).add(m["id"])
docout = ["# Documentation index\n\nThe initial capture's 1240 Markdown copies resolve to 306 distinct content hashes. A late capture adds three distinct records: two new quartic-composition documents and one changed proposal README version; **309 distinct records total**. The old README is retained. Different content versions are separate rows; byte-identical checkout copies share a row. Full duplicate paths, headings and late provenance are in `document_catalog_with_coverage.json`. Hashes bind captured bytes, not scientific acceptance.\n\n**Reading coverage:** decisive method/outcome documents were read and linked below. Other records were inventoried by title, headings and content searches for context and cross-checks; this is not a claim that every line of every raw log was independently revalidated. Contextual/unlinked documents remain available in full, without being silently discarded. SC48 is an unrelated diagnostic found in this repository and is excluded from StellarCSG method totals.\n\n| # | Document / frozen bytes | Copies | Direct catalog evidence | Original canonical location |\n| --- | --- | ---: | --- | --- |\n"]
for i, d in enumerate(CAT, 1):
    d["direct_method_evidence"] = sorted(refs.get(d["sha256"], set()))
    d["review_use"] = "direct method/outcome evidence" if d["direct_method_evidence"] else "indexed context, plan, handoff or supporting record"
    if "SC48_FOCUSED_FINDINGS" in d["canonical_path"]:
        d["review_use"] = "unrelated SC48 diagnostic; excluded from StellarCSG method count"
    title = d["title"] or Path(d["canonical_path"]).name
    docout.append(f"| {i} | [{mdcell(title)}]({d['snapshot']}) | {len(d['copies'])} | {', '.join(d['direct_method_evidence']) or mdcell(d['review_use'])} | {mdcell(d['canonical_path'])} |\n")
(HERE / "DOCUMENTATION_INDEX.md").write_text("".join(docout), encoding="utf-8")
dump("document_catalog_with_coverage.json", CAT)
print(json.dumps({"entries": len(METHODS), "documents": len(CAT), "raw_evidence_snapshots": len(DATA), "direct_document_hashes": len(refs)}))
