# StellarCSG: goal, evidence and next work

**Start here:** [project goal](../PROJECT_GOAL.md) and [current coil/plasma method map](../METHOD_MAP.md). The selected complex-pack candidate is P00 native facet/component CSG; the selected nonaxisymmetric plasma architecture is periodic patch/BVH with the checked adapter. Simplified built-in flat rings and torus are speed references, not substitutes for our complex target shapes. Full-target qualification remains open.

**Method-selection correction:** the recent certified-offset coil pilot is not our fastest historically measured implementation. See [fastest-method/branch review](FASTEST_METHOD_BRANCH_REVIEW_20260926.md) for recomputed elapsed records, source/branch identities, P00 faceted alternatives and matched rerun status. The older local span/shared-coil BVH remains the performance architecture to repair; current-workload winners are not established by comparing different historical workloads.

## 1. Goal and benchmark contract

Develop OpenMC CSG representations of WISTELL-D and other stellarator/tokamak coil and plasma geometry with accuracy approaching the intended CAD/DAGMC boundary, ordinary OpenMC tally/source integration, and transport nearly as fast as built-in CSG.

**Primary performance gate:** custom transport elapsed time <= 1.25 times built-in transport elapsed time for the same completed histories and declared workload. This is the working interpretation of "at least 80% as fast." Report seconds and time ratios, not throughput. Geometry generation may take longer; record it separately because it is paid per geometry rather than per transported history.

**Minimum:** 20,000 histories per acceptance run, with sufficient native duration and repeated interleaved observations before a precise speed claim. Earlier 200/1,000-history coil runs are diagnostic attribution only. A 20,000-history pilot does not establish production tally statistics.

| Family | Custom geometry to qualify | Built-in cost control | Mesh reference |
|---|---|---|---|
| Coils | Full complex centerline, winding-pack section/frame, corners, seams and trims | Similar-size flat rings made with cylinders/planes; comparable count/placement | Same intended target, DAGMC with verified Double Down / Embree |
| Plasma | Nonaxisymmetric WISTELL-D plasma, then other admitted configurations | Similar-size built-in OpenMC torus | Same intended target, DAGMC with verified Double Down / Embree |

Simple built-in proxies may differ in shape. They are cost controls. Custom accuracy is checked independently against the intended boundary, not by demanding equal tallies from unlike shapes. User-confirmed MAKEGRID filaments establish a trusted centerline source; a physical pack also needs section/frame/CAD identity. A round diagnostic tube is not the full winding pack.

Freeze source/energy, materials/nuclear data, completed histories/seeds, threads/hardware, world, tally and output settings within each comparison. Measure cold geometry preparation/export, runtime initialization/loading, transport, output and external process wall. Cached-input reuse and software compilation are distinct costs. Never sum nested OpenMC timers or substitute inverse calculation rates for elapsed timers.

The detailed [benchmark contract](BENCHMARK_CONTRACT_BUILD_TRANSPORT_20260926.md) and [timing evidence](BUILD_TRANSPORT_RESULTS_20260926.md) retain missing fields explicitly.

## 2. What has actually worked

| Method / work | Supported result | Limitation / decision |
|---|---|---|
| Exact analytic circular-coil dispatch | Historical 1M-history transport: 1.3670 s custom versus 1.4343 s built-in torus | Meets time target for the analytic fixture; cannot qualify complex coils |
| Exact periodic plasma torus dispatch | Historical studies supported near-native performance; current 20k proxy records 0.0935142 s custom versus 0.0586434 s built-in | Different versions/contracts; current proxy fails 1.25 time gate; generic plasma not qualified |
| Old local/span and shared-coil BVHs | 48 WISTELL circular 1 cm tubes, 100k histories: custom transport 0.33282 s versus fine ordinary DAGMC 2.0173 s; wall 2.45968 versus 12.27502 s | No matched built-in collection or Embree result; later wrong-first-root cases prevent accepting old generic solver unchanged |
| Old plasma local-patch path | 10k histories: 0.36314 s custom versus 0.45281 s fine ordinary DAGMC | Below new minimum; startup/wall missing and leakage difference unresolved |
| New restricted constant-metric offset | Native integration and finite 160-ray bank; retained earlier-root, tangent, failure and admission checks | Accurate for declared offset solid, not arbitrary rectangular/varying-frame pack; full-device speed target unmet |
| Immutable full-span interval cache | Independent source acceptance; isolated native 1k-history tally-on transport fell from 12.262501 to 6.648469 s; raw original/cache tally arrays identical | Diagnostic only; built-in torus 0.006410 s in that block; production library not rebuilt |
| Native scoring/source integration | Prior finite proxy campaigns exercised ordinary scoring and source contracts; spherical equator mesh defect repaired | Sparse bins and universal ecosystem compatibility remain unqualified |
| Transformed mesh filter repair | Actual Python/XML/HDF5-layout tests: 13 passed on final hash-bound source; independent Sol acceptance | No fresh native-generated rotated statepoint or tiny-track C++ qualification |

These are elapsed times read from retained raw/report records, not new independent reruns. No complete >=20k full-target, three-method coil/plasma matrix currently exists.

**Most recent native-torus plasma comparison (/009):** both methods completed 20,000 tally-enabled histories. Current WISTELL periodic CSG transport took **34.8197163 s**, versus **0.2180002 s** for the similarly sized built-in torus: **159.7233 times longer**, failing the 1.25 gate. Native process wall was 44.1852784 / 8.6432251 s. Custom cold coefficient preparation is UNKNOWN; reused model export took 0.0227205 s, and built-in primitive/model/export took 0.0260434 s. This is one controlled Fe56 boundary workload; independent target-CAD and first-root/per-bin acceptance remain UNRESOLVED. The historical fast plasma path and this current path need a matched call-path/workload audit before choosing a winner. The owner retained an administrative wrapper log error after successful native workers; the native timing receipts are intact.

**Restricted round-coil comparison (/009):** both methods completed 20,000 tally-enabled histories. Accepted-cache round-tube CSG transport took **167.4899387 s**, versus **0.1047436 s** for the built-in flat ring: about **1,599.05 times longer**, failing the 1.25 gate. Native process wall was 174.0984736 / 6.6949411 s. Cold geometry build is UNKNOWN for both reused-input paths. This is a diagnostic round section, not an admitted physical winding pack; recorded empty error logs do not establish full-target fidelity. The two single-seed pilots show transport, rather than XML export or initialization, is the immediate performance problem.

## 3. Why the new coil path is slow

**Latest complex-pack control (/010):** derived P00 facet/priority-component CSG took **5.774115 s** transport versus **1.203533 s** for fixed 30x30 cm native rings, 20k histories each. Ratio **4.797639 FAIL**, with allowed custom time 1.504416 s. Native process walls were 11.152920 / 6.440698 s. Independent timing/binding review accepted the diagnostic; physical target and local-scoring qualification remain open. This repeats the same P00 method and does not demonstrate a kernel optimization from the earlier 7.84 s observation. See the method map for why this is the selected pack candidate and what to profile next. The profile below describes the restricted global-offset path, not P00.

The measured native coil diagnostic profile assigns 67.19% of exclusive geometry-service time to global minimum queries, 20.18% to projection, and 10.09% to candidate proposals. Minimum scanned all 64 spans: 831,936 span visits across 12,999 calls, while only about 4.35 insertions and one heap node per call survived. Projection incurred about 68 allocations per call.

This supports accelerating conservative span exclusion and reusing immutable geometry bounds. It does not support deleting earlier-root or global-domain proof obligations. The accepted cache helps, but is far too small an improvement to close the native gap. The previously quoted 0.0176% belongs to a standalone complete geometry-service workload, not OpenMC transport or total wall. It should not appear as the headline transport result.

The old general solver has concrete incorrect roots: one adversarial case returned about 0.502 cm instead of the first root near 0.002 cm. Random passing rays did not expose this. Preserve that counterexample in every proposed replacement.

## 4. Other methods tried and research routes

The earlier synthesis accounts for seventeen dispatched repository Pro conversations, two unsent briefs, and the local implementation session. This review refreshed the latest local owners and the five relevant Pro result chats; earlier work is reviewed through the retained synthesis, not claimed rerun. Pro executions below are destination-reported prototypes. Their advertised sandbox bundles have not been independently imported or executed here.

| Route | What worked / failed | Next useful action |
|---|---|---|
| Fast kernel, Bernstein, candidate B/D, Bezier atlas and torus-arc routes | Useful bounds/fixtures; wrong earlier roots, sampled fallback, even contacts, incomplete coverage or all-blocked results prevented admission | Retain counterexamples; no silent fallback to approximate misses |
| Ruled rational/polynomial coil faces | Pro exact reference handles degree-at-most-six determinant roots and complete synthetic rectangular-sweep events; standalone annulus sizing test failed target; native general-ruled tracking NOT_RUN | Port one actual CAD-matched pack and complete trimmed, shared-edge/seam event ownership; then profile compiled queries |
| Offline normal-ownership certificate | Pro reports all 65,536 span pairs admitted for one 256-span restricted offset member; compiler/checker roughly 0.49/0.46 s | Independently audit/import certificate and binding; this is an offset, not physical rectangular CAD |
| Removing redundant owner recheck | Pro completed-hit cost improved about 3.6x, but whole-bank cost barely improved | Thin pair still unresolved after roughly 216k evaluations; repair before claiming speed |
| Planar-normal algebraic specialization | Constructive stationary-root and two-quadratic-branch route for a retained thin case | Correctness experiment for an exactly admitted family; qualifying frequency in general transport unknown |
| Conservative analytic inner/outer bounds | Potential cheap certain-inside/outside tests and refinement windows | Unimplemented for target; require proven containment and exact handling in uncertain/tangent regions |
| Period import and source prototypes | Provenance/contract improvements and reported analytic sampler tests | Reconcile current named-hash loader repair; general stellarator births, clearance and native source interoperability need testing |
| P00 faceted/component CSG | Earlier accepted facets expose eight transverse component intersections; union/priority occupancy agreed on 262,144 resolved sign assignments and 360 sampled material entries | Finite faceted occupancy does not qualify continuous CAD or distinct per-coil tally ownership; no current >=20k three-method transport gate |
| New plasma direct analytic adapter | Compiled isolated proposal but probe failed Boolean sense comparison | Retain failure; diagnose tangent normal/tie-break behavior, avoid unchecked promotion |

No evidence currently establishes that a new general mathematical theorem is required. The immediate blockers are algorithm cost, complete first-boundary/event semantics, native implementation, and target geometry binding. A specialized proof may justify a specific optimization; it must not stand in for a runtime completeness check it does not cover.

## 5. Selected development direction

**Coils:** start with P00 native facet/priority-component CSG, the best currently executed pack candidate. Profile component/facet traversal and ownership, then test conservative acceleration against the same represented solid. Recover conservative immutable span/shared-coil BVHs as an alternative with strict same-solid checks; the concrete minimum/projection proposal is not yet compiled or accepted. Independently test hull enclosure, touching boxes, masked-domain coverage, bounds arithmetic and stack limits; retain uncertain nodes. Restoring the older unchecked hit solver is disallowed by retained counterexamples. Ruled faces remain a formulation candidate for actual rectangular packs. Offline ownership can complement an admitted offset, but cannot convert an ellipse into rectangular CAD. The [September 30 continuation](BEST_METHOD_CONTINUATION_20260930.md) records the completed comparisons and bounded next work.

**Plasma:** retain periodic local-patch/BVH architecture and genuine analytic fast paths, while fixing the failed sense proposal before promotion. Compare a correctly admitted nonaxisymmetric payload with a built-in torus and its target mesh. An analytic torus success alone is insufficient.

Source-only audit now finds the current and preserved old generic solver, patch builder/evaluator, shaped solver and exact solver identical after whitespace removal. This does not bind the historical executable to that source, but it means an algorithm regression has not been established. The old short WISTELL record lacks a matching source/material/data/tally/collision workload. The current solid Fe56 run is a much heavier transport contract. Do not scale historical seconds by history count and call the difference a solver regression. The next plasma experiment should journal a bounded complete-query bank and count all classification/distance/normal, candidate/Newton/tangent operations per history before selecting a performance patch. Generic Newton failures and the misleadingly named exclusion counter also need independent first-root/no-hit coverage auditing; absence of lost-particle messages is insufficient. See CALL_PATH_AUDIT_009.md.

**Hybrid:** compile immutable bounds/certificates once, use cheap conservative exclusion at runtime, refine only eligible domains, and keep exact/fail-closed fallback. Compare complete workload and worst cases; a fast common hit with an expensive unresolved tail is not a solution.

## 6. Embree status

Historical composite reports record genuine Double Down / Embree linkage and the runtime banner `Using the DOUBLE-DOWN interface to Embree.` Versions were Embree 4.3.0, Double Down 1.1.0, DAGMC 3.2.4 and MOAB 5.5.1. The recorded hybrid torus run completed only 10,000 histories. This establishes historical availability, not current local availability or a WISTELL-D benchmark.

The historical 48-coil and plasma mesh timings above are ordinary DAGMC (`nompi_nodoubledown`). Do not label them Embree. Independent current inventory is assigned; next target-mesh runs require named artifact hashes, tolerance/triangle count, runtime backend evidence, and geometry/overlap checks. A historical DAGMC geometry-debug explicit-volume/implicit-complement overlap complaint remains visible even where ordinary transport completed.

Current inventory update: the historical Embree executable is present and matches its recorded hash, but its named dependency prefix is empty and Docker is unavailable in the review session. A runnable Embree backend is therefore not established. Both historical target mesh files are present and hash-verified; the coil mesh is the standardized 1 cm round tube, and manifest errors are sampled rather than certified tolerances. The current experimental OpenMC build has DAGMC disabled. Restoring a runnable existing backend and binding an actual winding-pack mesh are specific remaining tasks; no installation has been attempted.

## 7. Infrastructure acceptance still needed

- Preserve ordinary CellFilter/material/instance identity and MeshFilter flight fractions. Use local mesh overlays, optionally masked by parent cells, so local tallies do not add unnecessary transport boundaries.
- Keep `assume_separate=false` for overlapping parent/local observations. Ancestor and descendant cell bins are not automatically a disjoint partition.
- Test spatial-bin conservation AND individual bin ownership. Total-only closure previously hid a polar redistribution defect. The separate tiny-track mesh shortcut counterexample remains unqualified in actual C++.
- Extend native-generated rotated-statepoint roundtrips, repeated instances/transforms, normals/surface current, boundary conditions, plotting/volume, restart, MPI/OpenMP and declared score/filter combinations. The 13 Python tests qualify only the narrow repair.
- Bind source births to the same geometry/version/units and proper Jacobian, physical clearance, period accounting, weights and neutron rate. Analytic diagnostic banks do not establish physical WISTELL source predictions.
- Record physical occupied volumes and atom counts for normalized flux/DPA. Per-source damage energy is not automatically DPA per second. Sparse spectral bins remain statistically unqualified.

## 8. Current execution and continuation

The earlier coil/plasma /009 phase comprised two bounded local blocks and 80,000 completed histories across four workers. Subsequent /010 fixed-section coil and old/current plasma blocks also completed and passed independent timing-diagnostic review, as summarized in the [September 30 continuation](BEST_METHOD_CONTINUATION_20260930.md). One exclusive shared compute lease serialized heavy execution; one CPU, finite worker timeouts and memory limits were retained. No new remote job, dependency acquisition or schedule was authorized or launched by this consolidation.

Latest owner observations: independent Sol review accepts the completed fixed-section coil and plasma runtime-replay timing/input accounting. The corrected coil transport gate fails; the plasma replay has no new built-in denominator, and the earlier plasma proxy gate also fails. Full-target fidelity and scoring accuracy remain open. The existing review accepts the conservative BVH source design provisionally and rejects plasma direct-evaluate/normal promotion after its failed sense probe. Neither untested proposal is incorporated into production source.

Next decisive deliverables:

1. >=20k elapsed-time receipts: valid custom versus built-in ring/torus; label any analytic diagnostic separately from full target.
2. Same-target WISTELL-D DAGMC with verified Embree; if unavailable, state the exact missing capability rather than relabel ordinary DAGMC.
3. Cold geometry preparation and runtime load timings for each method, with original artifacts/cached reuse separated.
4. Independent acceptance of one acceleration delta and one full physical coil/plasma fidelity test; only then broaden production timing.
5. Publish a refreshed matrix and supported tally/source capability list. Choose winners separately for coil and plasma after correctness gates, using actual transport seconds.

Public continuation starts with this report, the detailed timing/contract files, [PR #5](https://github.com/FusionSandwich/openmc/pull/5), and the earlier synthesis on [PR #3](https://github.com/FusionSandwich/openmc/pull/3). [PR #4](https://github.com/FusionSandwich/openmc/pull/4) remains a diagnostic proposal. Preserve raw local HDF5/statepoints, CAD and nuclear data: public text receipts do not replace those inputs. Earlier source snapshots remain fixed evidence and must not be rebound silently to later binaries.
