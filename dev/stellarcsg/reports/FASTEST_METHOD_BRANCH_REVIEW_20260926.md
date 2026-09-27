# Fastest methods, branches and apparent regression

For the selected complex-target development routes, start with the [project goal](../PROJECT_GOAL.md) and [current coil/plasma method map](../METHOD_MAP.md). Those select P00 facet/component CSG for pack development and local periodic patch/BVH with the checked adapter for stellarator plasma; historical analytic fixtures are not target winners.

## Direct answer

**No: the recent coil benchmark did not demonstrate use of our fastest developed method.** It measured the restricted certified global-offset path with its accepted interval cache. Earlier local/span and shared-coil BVH implementations recorded far shorter elapsed transport. The latest benchmark report must not be read as a ranking of all available methods.

For plasma, the current and preserved generic patch solver bodies are textually identical after whitespace removal. The new frozen 20k pair recorded old-source-rebuilt 27.225501 s versus current-retained 28.970192 s: current/old 1.064083 in this single diagnostic pair. The adapter/compiler policies differ; old unchecked misses cannot be promoted. This pair does not reproduce the archival binary or establish portable equivalence. The 34.82 s versus 0.218 s native-torus comparison remains a serious target-speed failure; the new pair is not a replacement torus comparison.

Three questions must remain separate: fastest recorded result within a declared workload; fastest runnable implementation on the current common workload; and fastest correct representation of the intended physical geometry. We currently have historical leaders, not a qualified universal winner.

## Recomputed elapsed records

Root read the raw records again and generated [HISTORICAL_ELAPSED_METHODS_010.json](HISTORICAL_ELAPSED_METHODS_010.json): 15 rows from nine SHA-bound artifacts. Warmups are excluded from measured medians. Times come directly from recorded timers; no inverse rates or history-count extrapolations are used. History counts and shapes differ across groups, so the following rows do not form one sortable speed league.

| Workload | Method | Histories/run; observations | Recorded transport s | Qualification |
|---|---|---:|---:|---|
| Exact circular coil C0 | Composite exact native torus dispatch | 1,000,000; 7 | **1.3670** | Best paired analytic coil result; built-in 1.4343 s |
| Same C0 solid | Forced-general span solver | 1,000,000; 7 | 14.5390 | Slower than exact dispatch; general correctness limits |
| 48 WISTELL circular 1 cm tubes | Local span + shared coil BVH | 100,000; 7 | **0.33282** | Strongest preserved set-level CSG record; not physical rectangular packs |
| Same 48-tube target | Fine ordinary DAGMC | 100,000; 7 | 2.01730 | Embree not used |
| Representative WISTELL coil031 | Local span/BVH CSG | 100,000; 7 | 0.21899 | Fine ordinary DAGMC was faster: 0.096937 s |
| General WISTELL plasma, archival workload | Local periodic patch/BVH CSG | 10,000; 5 | **0.36314** | Strongest preserved general-plasma record; leakage closure unresolved |
| Same archival plasma study | Fine ordinary DAGMC | 10,000; 5 | 0.45281 | Not a built-in torus comparison; below new history minimum |
| Derived periodic P00 winding-pack facets | Priority component CSG | 360; 1 | 0.37243 | Pack mesh candidate; material-entry/track validation, not production speed gate |
| Same P00 entry bank | Common-material union CSG | 360; 1 | 0.72726 | One observation; continuous CAD/per-coil ownership still open |
| Current near-circle round tube | Certified offset + cache | 20,000; 1 | **167.48994** | Current costly path; flat-ring control 0.104744 s |
| Current WISTELL plasma, solid Fe56 workload | Periodic patch/BVH CSG | 20,000; 1 | **34.81972** | Current costly workload; built-in torus 0.218000 s |

The older exact periodic-torus studies supported near-native performance, but their compact records do not retain complete elapsed timers. They remain analytic fast-path evidence, not invented time values or a generic-plasma ranking.

For the 48-tube study, median process wall was 2.45968 s CSG versus 12.27502 s fine ordinary DAGMC, with initialization 1.4192 / 9.4735 s. These are actual separately recorded medians. The new coil process wall was 174.09847 s versus 6.69494 s for its flat ring; initialization 6.49220 / 6.44644 s. Cold build time is missing in both reused-input campaigns. Transport dominates the new custom cost, so faster XML export cannot close the gap.

**Concrete workload difference recovered:** the original `run_wistell_coil_set_openmc.py` at record commit 1353d0ae5 uses H1 at 1e-30 atom/b-cm for both materials, a source 1.5 cm outside the 1 cm coil tube, one batch and no tallies. The raw record retains that source contract and all seven measured native leakage fractions are 1.0. The recent test uses solid Fe56, a file source and tally scoring. The near-vacuum study largely measures boundary tracking; the solid-material study includes scattering and repeated geometry queries. They are not a measured regression pair. Builder local SHA256: c3218c41863869c114724723a65a60f39f3d9c7a9a79a4bd4c774b88f170556d. This difference does not establish that the certified-offset algorithm is fast; its own matched native proxy result remains very poor.

## Branch and source map

| Method/source | Branch | Checkpoint / record commit | What this identity means |
|---|---|---|---|
| Original periodic patch and swept span/set BVHs | `codex/stellarcsg-native-csg-foundation-20260828` | Checkout 5faf87421d5d2066278c7ae02e38138fc22ec894; plasma record 4e97b2480489e27c1939554bbab1750ebcf551a5; 48-coil record 1353d0ae5d2d64422cc7dd8a6f144cdabfa0d000 | Git commits introducing recorded evidence; not proof that every archived binary was built from that exact tree |
| Exact torus adapter fast path | `codex/stellarcsg-torus-class-fastpath-20260901` | c0290b257e879d16762b072e0b6ee3e43a519e8e | Native helper dispatch for truly analytic torus input |
| Exact circular-coil dispatch and interoperability | `codex/stellarcsg-composite-blanket-interoperability-20260901` | Checkout 3041a938c3fb0bc349654f37b0b3ebcd3cd5a9bb; C0 record 1f2d53a537337616f4e87bc48ad573cc4f0bc509 | Best paired analytic coil record and preserved old source/build artifacts |
| Recovered fast kernel | `JS/stellarcsg-fast-20260913-03` / `JS/stellarcsg-fast-recovery-20260913-04` | 5ed327ade33b31ecdb5e3b4b4111c55f321991fd / 57cb1fbf75a54a0fa75e70386922ad9cfecf06b1 | Diagnostic older solver; strict replay exposes four discrepant cases |
| Later root repairs | `JS/stellarcsg-local-repair-20260915-07` | 48c65bf0ce2d2c41ab1c7e3f19b84b4f67bc9bfc | Earlier-entry repair does not establish complete tangent/prefix handling |
| P00 faceted/component CSG and correctness continuation | `JS/stellarcsg-local-continuation-20260925` | 3b61ee47fa498e2b4171756e5352f57de80de2a4 | Facet occupancy/material tracking; source checkpoint is distinct from a runtime library hash |
| Certified offset/cache and current periodic adapter | `JS/stellarcsg-astra-kernel-20260926` | Published c5144ea552d34c3749de17a96e17c0a3c2a5fed2; old current library f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6 | Source includes cache/filter updates; production library was not rebuilt. Coil used separately pinned complete cache DSO |

Repeated copies of the same report in later checkouts count as one campaign. No branch rename or checkout replacement is needed to preserve the leaders.

## Which direction to keep

**Analytic shapes:** keep genuine exact torus/circular-coil native dispatch. It has the strongest paired native-speed evidence. The new direct analytic evaluate/normal proposal failed a sense-equivalence probe; that mismatch needs diagnosis, and does not automatically invalidate the historically tested specialization or establish which normal is physically correct.

**General coils:** the older span/shared-coil BVH has the strongest preserved set-level timing and is a priority architecture to repair. The current certified global path is a verifier/fallback candidate, not the selected fast production implementation. Do not restore its predecessor's wrong-first-root behavior: an adversarial ray returned about 0.502 cm instead of 0.002 cm. Repairing acceleration and verifying local candidates must refer to the same solid. A fast near-circle run through an old library does not by itself establish generic BVH performance: that library can specialize an approximately circular centreline to an averaged analytic torus.

**Physical winding packs:** prioritize P00 faceted priority/component CSG in the new measurements. The periodic candidate is derived from the accepted pack mesh by shared cap-vertex midpoint repair, with maximum vertex displacement 0.003328773593059 cm. It is more directly relevant than a round-tube offset, but is not the unchanged accepted H5M or a continuous CAD certificate. Continuous CAD accuracy, seams/overlap and coil-specific scoring remain separate gates. Ruled faces remain a promising unqualified formulation; no native full-pack timing exists.

## Current rerun: five completed 20k workers and one retained failure

The finite `matched-replay-010` block completed five workers (100,000 total histories), then stopped at the first native failure. These are separate P00 and round-tube workload families, not one interchangeable ranking.

| Family / method | Initialization s | Transport s | Native process wall s | Interpretation |
|---|---:|---:|---:|---|
| P00 derived periodic facets, 18 components | 5.946362 | **7.836203** | 13.906716 | Actual winding-pack mesh candidate; accuracy gates open |
| P00 native flat-ring PCA envelopes, 18 components | 5.847027 | **8.652459** | 14.608073 | Whole-coil envelopes; some sections substantially exceed nominal 30x30 cm |
| Round tube certified offset/cache | 6.008041 | **165.927178** | 172.083797 | Repeats the recent costly path |
| Retained composite kernel control | 5.993003 | **0.233747** | 6.342860 | Near-circle analytic specialization possible; unchecked generic misses remain |
| Retained recovered kernel | 6.010795 | **0.228377** | 6.341732 | Same specialization concern; not generic correctness acceptance |
| Current legacy rounded-frame lane | n/a | **FAILED** | 5.940352 until abort | Surface 10 unresolved nearest-boundary query; native exit -6 |

Evidence: `coil-profile-20260926/matched-replay-010/PARTIAL_RESULTS.json`, individual receipt/process files and `TERMINAL.json`. Each successful worker completed 1000 particles x 20 batches, seed 1741, one CPU and tally scoring. Round lanes reuse the same coefficient file, but moving-frame and constant-metric solids are not proved identical. Old-control library is a coherent controlled kernel replacement in a retained runtime, not a pristine rebuild of the entire old branch. A zero exit does not erase its known first-root defects.

The owner's `OLD_SAMPLED_TORUS_GATE_AUDIT.json` reconstructs the retained constructor gate: 64 sampled checks pass the 0.000628319 cm tolerance, and the adapter defaults to `force_general_solver=false`. It therefore predicts analytic torus dispatch for both fast old lanes. This is source-gate reconstruction, not fresh dynamic branch telemetry; finite off-knot sampling is not a continuous fidelity bound. The 0.23 s runs must not be advertised as generic span/BVH timings.

P00 uses a separate frozen 18-site, 1 MeV bank and controlled Fe56 material. Its transport ratio to the PCA envelopes is 0.90566. **This is an envelope-sizing diagnostic, not an accepted 80% speed claim.** The preparation/review audit found PCA sections 64-260 cm wide radially and 13-408 cm high axially, versus nominal 30x30 cm. All 18 bank sites start in iron in those envelopes, versus four in the fixed-section rings and none in the facet fixture (an entry bank starts just outside it). These are substantial material-path/occupancy differences. A separate fixed 30x30 cm ring-control pair is authorized, keeping source coordinates and physics unchanged and reporting source occupancy differences. Its concrete plan requires independent review before execution. Cold CAD/coefficient build time remains UNKNOWN; reused export was 0.076623 s for facets. Tallies were written, but comprehensive local-bin accuracy/ownership remains open. A later source bank in common exterior space is a useful additional control; it has not been run or used to claim success here.

**General plasma:** retain local patch/BVH solving, but obtain matched current-workload measurements and query counts before choosing a new implementation. Identical function bodies cannot explain a claimed algorithm change. The historical source-bank/material/tally/compiler omissions prevent declaring a regression factor by dividing the old and new seconds.

## Matched rerun scope and current status

Existing coil and plasma owners are preparing finite >=20k comparisons with matched source bank, nuclear data/materials, settings, tally/output policy, world, CPU and declared geometry. Accuracy/status is reported next to speed. Different represented solids are labeled explicitly. All numerical workers use the shared exclusive lease; failed/unresolved runs are retained rather than discarded from a timing average.

The three preserved complete composite runtime pairs have been inventoried. The experimental ordinary-DAGMC and Double Down libraries cannot currently resolve their historical HDF5/DAGMC/MOAB dependencies; the default-OFF binary lacks StellarCSG. Therefore a historical executable rerun has not yet occurred. A separately inventoried, reviewed offline experimental-ON/DAGMC-OFF source build against already-local dependencies is being evaluated. It would be a source reproduction under the current compiler, not reproduction of the archived binary. No downloads/installation or dependency substitution is hidden in this plan.

The coil owner is also checking current runtime selectors for legacy rounded-frame and P00 faceted methods to avoid unnecessary builds. Unsupported/admission failures produce FAILED/NOT_RUN entries. Uncompiled BVH proposals, Pro-only ruled/ownership prototypes, known incorrect candidate B/D/atlas/arc solvers and absent Embree dependencies cannot be treated as successful transport competitors.

Independent review accepted the fixed-section geometry construction, but rejected the first execution packet for missing enforcement of frozen review/input identities, resource observations and outer failure/lease cleanup. It also rejected the first plasma source-build launch packet for path conversion, fresh inventory and manifest/XML binding gaps. Owners are correcting these finite launch packets. These are execution-admission blockers, not negative numerical results or a demonstration that the mathematical formulations fail. Neither pending comparison is counted as completed here.

**Admission update:** both corrected frozen launch packets subsequently passed independent review: `P00_FIXED_SECTION_EXECUTION_ADMISSION_010.json` and `PLASMA_PREBUILD_ADMISSION_010.json` in the reviewer directory. Each permits exactly one bounded diagnostic block, no acquisition/retry/production mutation. The plasma block has started fresh preflight inventory; the fixed-section block must wait for the shared lease. Admission does not count as a successful build, completed transport or accuracy acceptance. Terminal evidence remains pending.

**Execution handoff snapshot:** the plasma owner recorded fresh inventory/binding PASS, configure PASS and compile 12/137 units at its startup observation. See [REBUILD_RUN_HANDOFF_010.md](plasma-best-time-20260926/REBUILD_RUN_HANDOFF_010.md) for exact run/session identity, finite deadlines and terminal collection/acceptance. Compilation runs asynchronously; there are no new plasma timing results. The fixed-section block is deferred behind the known plasma lease, without repeated lease attempts. Never start a duplicate block or remove that lease to obtain a comparison.

Final current-workload winners remain **NOT_FULL_TARGET_QUALIFIED**. The completed diagnostic already establishes that the certified-offset path is not the fastest retained implementation for the tested near-circle. General coil performance, fixed-section P00 timing, matched old/current plasma and full geometry/tally accuracy remain unresolved. This report does not promote old inaccurate answers because they are fast.

## Continuation decision and remaining evidence

1. **Keep analytic native dispatch for truly admitted analytic geometry.** Best complete paired C0 time is 1.3670 s versus built-in 1.4343 s. Preserve exact admission; a sampled approximation is a distinct geometry simplification.
2. **Prioritize physical-pack facet/component CSG and repaired local span/shared BVHs.** P00 offers a directly relevant physical-pack candidate; the older BVH offers strong historical general-tube timing. Select between these using fixed-section native controls and same-target accuracy, rather than near-circle specialization timings.
3. **Treat the certified global offset as a restricted reference/fallback.** The repeated 165.93 s transport confirms its cost on this test. Its cache improved an earlier A/B workload but did not make it a competitive native-cost production lane. A source-only conservative BVH proposal remains uncompiled/untimed.
4. **Resolve plasma attribution with a frozen old-source/current-runtime pair.** If the source rebuild is admitted and completes, compare actual seconds and first-root/scoring behavior. If it cannot run, retain the dependency/build failure and do not assert a regression factor. Next useful attribution is geometry queries, crossings, candidate patches and iterative work per history.
5. **Close accuracy and integration independently.** Repaired earlier roots are insufficient without prefix/tangent/normal/seam coverage. Writing a statepoint is insufficient without useful local tally bins, source support, coil ownership and comparison to an independent same-target reference.

This is currently an implementation, workload and correctness-admission problem; the evidence does not demonstrate that new mathematics is necessary. Complete earliest-hit exclusion may require a proof/certificate, but no impossibility result or adequate proof that the available local methods cannot meet the target exists. Verified Double Down/Embree on the same target, cold build measurements, repeated sufficiently long transport and production-scale uncertainty are still missing. Do not turn an unavailable comparison into a zero-second result or a failure of the underlying mathematical method.
