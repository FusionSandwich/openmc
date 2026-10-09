# Geometry build and transport: elapsed-time evidence

The [project goal](../PROJECT_GOAL.md) and [current coil/plasma method map](../METHOD_MAP.md) select target-specific development routes. The elapsed-time target is complex custom geometry <=1.25 times a similarly sized native flat ring (coils) or torus (plasma), with independent target accuracy and ordinary source/local tally usability.

## Corrected coil fixed-section pair /010

Latest corrected coil control: `coil-profile-20260926/fixed-section-pair-010` records two completed 20k workers. Derived P00 facets transport **5.774115369 s**, fixed30 native rings **1.203532667 s**, ratio **4.79763909 FAIL**. Initialization was 5.276662125 / 5.130763384 s, statepoint output 0.030490800 / 0.024877401 s and native process wall 11.152920394 / 6.440697556 s. This repeats the same P00 implementation; it is not a new measured optimization over the earlier 7.84 s observation. Source/physics/tallies stay frozen; shape-induced initial iron occupancy remains 0/18 versus 4/18 sites. Reused XML preparation was 0.1445532 / 0.156726508 s. Cold geometry build UNKNOWN, no software build. Independent timing/binding review accepted the diagnostic; physical CAD/ownership/normal/local-bin fidelity remains open.

## Matched old/current general-plasma replay /010

Both variants completed 20,000 tally-enabled histories with frozen identical geometry/material/settings/tally XML, source bank, LCFS payload, nuclear data and one CPU affinity. This is a runtime comparison, not a new built-in torus comparison. It rebuilds old source with current GNU14/HDF, not the original archive binary.

| Runtime | Initialization s | Transport s | Statepoint output s | Native process wall s |
|---|---:|---:|---:|---:|
| Old source rebuilt offline | 5.296172 | **27.225501** | 0.240643 | 32.866227 |
| Current retained checked implementation | 6.483235 | **28.970192** | 0.239159 | 35.788988 |

Current/old transport time is **1.064083** in this one ordered pair. This does not establish a large implementation regression, statistical equivalence or portable superiority. Current and old principal generic solver bodies match after whitespace removal; complete runtime/adapter/compiler policies differ. Old unchecked no-hit handling remains diagnostic only. Independent first-root/per-bin geometry/scoring acceptance remains open.

Configure took 25.937595 s and software compilation 764.919447 s; these are not geometry build times. Cold geometry build is UNKNOWN. Source-rebuild block wall was 898.005908 s. Driver and both native workers exited zero, but the outer wrapper exited 1 during lease-directory cleanup; subsequent own empty-directory release and absent-lock evidence are retained. Independent review accepted matched timing/binding/finite-array accounting as a diagnostic, with physical geometry/first-root/scoring accuracy still unresolved. Evidence: `plasma-best-time-20260926/source-rebuild-010-01/comparison.json`, worker/native receipts, `TERMINAL_VALIDATION_REBUILD_010.json`, `LEASE_RELEASE_TERMINAL_010.json`, and `coil-hybrid-accuracy-20260926/PLASMA_TERMINAL_ACCEPTANCE_010.json`.

**Scope correction:** these recent pilots measure particular paths, not the fastest of all developed methods. The [method/branch ranking and rerun audit](FASTEST_METHOD_BRANCH_REVIEW_20260926.md) identifies older faster recorded architectures and preserves their correctness/workload limits.

Report seconds, separately for coils and plasma. The working transport acceptance limit is custom time / built-in time <= 1.25 (10 seconds built-in permits 12.5 seconds custom). Geometry build is a separate measurement. No full-target three-method comparison is yet complete.

## Method replay /010: 20,000 histories per completed method

The finite replay completed five workers and stopped when current legacy surface 10 aborted on an unresolved nearest-boundary query. Full phase timings, branch/runtime identities and eligibility are in the [method review](FASTEST_METHOD_BRANCH_REVIEW_20260926.md). These rows update method selection; they do not replace the /009 receipts below.

| Workload family | Method | Transport s | Native process wall s |
|---|---|---:|---:|
| Near-circle round tube | Certified offset/cache | 165.927178 | 172.083797 |
| Near-circle round tube | Retained composite kernel control | 0.233747 | 6.342860 |
| Near-circle round tube | Retained recovered kernel | 0.228377 | 6.341732 |
| Near-circle round tube | Current legacy rounded-frame | FAILED: unresolved query | 5.940352 until abort |
| Derived periodic winding-pack facets | P00 component CSG | 7.836203 | 13.906716 |
| P00 proxy collection | Built-in PCA ring envelopes | 8.652459 | 14.608073 |

Source-gate reconstruction predicts averaged analytic torus dispatch for the old near-circle runtimes; their times cannot be attributed to generic BVH performance. Known generic wrong-root defects and moving-frame/constant-metric solid differences remain. P00 ratio 0.90566 is an **envelope-sizing diagnostic**: some proxy sections are much thicker than the nominal 30x30 cm pack. The corrected fixed-section control completed with a failed 4.797639 time ratio, as recorded above. The periodic facet candidate has vertex displacement <=0.003328773593059 cm from seam repair; continuous CAD and comprehensive tally-bin accuracy remain open. Separate frozen source banks are used for the round and P00 families. Cold geometry build remains unknown.

## New coil diagnostic: 20,000 histories per method

One seed, one CPU, tallies on. Accepted-cache round-tube CSG versus the built-in flat-ring proxy; the full complex winding pack remains NOT_ADMITTED. Each native worker exited zero and completed 20,000 histories. Recorded lost/fatal/unresolved diagnostics are empty; this is not an independent universal first-root or physical fidelity proof.

| Method | Cold geometry build s | Reused input/export s | Initialization s | Transport s | Recorded statepoint output s | Native process wall s |
|---|---:|---:|---:|---:|---:|---:|
| Accepted-cache round-tube CSG | UNKNOWN | 0.1506007 | 6.4921978 | **167.4899387** | 0.0291610 | 174.0984736 |
| Built-in OpenMC flat ring | UNKNOWN (XML reused) | 0.1733471 | 6.4464359 | **0.1047436** | 0.0287714 | 6.6949411 |
| Same-target DAGMC with Embree | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

The custom transport time is about **1,599.05 times** the flat-ring control: FAIL against 1.25. The allowed time at this denominator would be 0.1309295 s. End-to-end reused-input-to-validated-result times were 174.3038389 / 6.9258970 s, measured separately. This one-seed diagnostic is not a full winding-pack benchmark or an uncertainty-qualified portable ratio. Background host activity was recorded.

Evidence: coil-profile-20260926/meaningful-coil-009/{SUMMARY.json,TERMINAL.json,cache/receipt.json,flat_ring/receipt.json} and process receipts. Shared materials/settings/tally XML hashes match. No software build occurred; the accepted complete cache DSO is individually identified in the experiment, while the production library remains unchanged.

## New general-shaped plasma pilot: 20,000 histories

One seed, one CPU, tally-enabled controlled solid-Fe56 boundary workload using the WISTELL LCFS (512x192 coefficients, four periods). This is not physical plasma material composition. Both native workers completed and exited zero. Geometry-to-CAD correspondence and independent first-root/per-bin scoring acceptance remain UNRESOLVED.

| Method | Cold geometry build s | Reused input/model export s | Initialization s | Transport s | Recorded statepoint output s | Native process wall s |
|---|---:|---:|---:|---:|---:|---:|
| Current WISTELL periodic CSG | UNKNOWN | 0.0227205 | 8.9089877 | **34.8197163** | 0.3185042 | 44.1852784 |
| Similarly sized built-in OpenMC torus | 0.0260434 primitive/model/export | n/a | 7.9857201 | **0.2180002** | 0.3480966 | 8.6432251 |
| Same-target DAGMC with Embree | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

**Transport ratio: 159.7233; FAIL against 1.25.** Maximum custom transport at this built-in time would be 0.2725003 s. The earlier analytic torus fixture below must not stand in for this general-shaped result. The existing f301... library has DAGMC disabled; the historical Embree executable's dependency closure is presently unverified. The outer wrapper reported a missing silent-driver log after both successful native runs; actual benchmark receipts remain intact. Worker-invocation walls (including Python overhead) were 47.8914784 / 12.2510634 s, separately from native process walls above.

Evidence: plasma-best-time-20260926/RESULTS.md and transport-009-01 block/worker receipts; materials/settings/tally XML match and no duplicate filters were found. The owner's FINAL_VALIDATION_009.json `lease_released=false` snapshot was taken while a subsequent coil owner held the shared lock; it does not establish that the plasma owner retained its own lease. Its own lease release is recorded separately. No repeat has been launched to replace this single pilot.

## Recent coil diagnostic: 200 histories per run

Three-seed medians from the transport-proxy-20260926 receipts. The custom solid is a near-circular axis with a round tube, not the full complex winding pack. These receipts predate the newly integrated cache.

| Method | Geometry build s | Initialization s | Transport s | Process wall s | Transport time / flat ring |
|---|---:|---:|---:|---:|---:|
| Built-in cylinders/planes flat ring | UNKNOWN | 5.19405 | 0.0026353 | 5.83968 | 1.00 |
| Built-in OpenMC torus, round section | UNKNOWN | 5.40610 | 0.0031956 | 6.09091 | 1.21 |
| Custom certified CSG, accelerated | UNKNOWN | 5.31340 | 2.3485188 | 8.35202 | 891.18 |
| Same custom CSG, acceleration off | UNKNOWN | 5.12584 | 5.8250855 | 11.90556 | 2210.41 |
| DAGMC of this fixture | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

The custom diagnostic fails the transport time target by a large margin. Millisecond native timings make these ratios diagnostic, not a precise production performance estimate. Startup dominates process wall and hides much of the transport penalty in this small run.

## Recent plasma torus diagnostic: 20,000 histories per run

Three-seed medians, exact torus specialization with R100/r20 cm and the same Fe56 shell. This tests an analytic plasma torus, not the nonaxisymmetric stellarator target.

| Method | Geometry build s | Initialization s | Transport s | Process wall s | Transport time / built-in torus |
|---|---:|---:|---:|---:|---:|
| Built-in OpenMC ZTorus | UNKNOWN | 5.25357 | 0.0586434 | 5.93812 | 1.00 |
| Custom periodic spline CSG | UNKNOWN | 5.26166 | 0.0935142 | 5.98824 | 1.595 |
| DAGMC of this fixture | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

Custom transport takes about 59.5% longer than the built-in plasma torus in this receipt set. The 1.25 limit allows at most 0.0733043 seconds here; this version fails. The nearly equal process wall times do not establish transport parity.

## Historical target-shape comparisons with DAGMC

Build times were not retained. No matched built-in flat-ring collection or plasma torus transport control exists in these records. Each row is a median of that recorded metric; do not sum separate medians as an observed total.

| Family / method | Histories | Geometry build s | Initialization s | Transport s | Process wall s |
|---|---:|---:|---:|---:|---:|
| 48 WISTELL coils, old custom CSG, circular 1 cm tubes | 100,000 | UNKNOWN | 1.4192 | 0.33282 | 2.45968 |
| Same coil tube target, coarse DAGMC | 100,000 | UNKNOWN | 1.4780 | 1.4176 | 3.57823 |
| Same coil tube target, fine DAGMC | 100,000 | UNKNOWN | 9.4735 | 2.0173 | 12.27502 |
| WISTELL plasma, old local-patch CSG | 10,000 | UNKNOWN | UNKNOWN | 0.36314 | UNKNOWN |
| WISTELL plasma, fine DAGMC | 10,000 | UNKNOWN | UNKNOWN | 0.45281 | UNKNOWN |

The old coil tube method is promising for speed but does not qualify the intended full winding-pack section. Later adversarial cases exposed first-root correctness gaps in older general solvers, so the fastest historical numbers cannot alone select an accepted implementation. The plasma comparison also has an unresolved leakage difference (0.9955 versus 1.0).

## Historical exact circular-coil control

Seven measured repetitions, one million histories each: built-in torus transport median 1.4343 seconds; exact custom circular-coil dispatch 1.3670 seconds; forced-general custom path 14.539 seconds. Build and external wall were not recorded. Exact native dispatch meets the transport time target on this analytic fixture; it does not qualify complex coils.

## Evidence locations and remaining measurements

- Recent raw receipts: `stellarcsg-astra-kernel-20260926/dev/stellarcsg/reports/transport-proxy-20260926/*/receipt.json` (`wall_s`, `runtime_s.transport`, `runtime_s.total initialization`). Historical library SHA256: `7fa3dbf5bef055aa2227842800e54a2daa84537a1ba6730e97f4fb6cd25d317e`.
- Historical coil collection: `openmc-stellarcsg-composite/dev/stellarcsg/benchmarks/raw/wistell_coil_set_openmc_20260831.json`.
- Historical plasma: `openmc-stellarcsg-composite/dev/stellarcsg/benchmarks/raw/wistell_openmc_patch_vs_fine_mesh_20260831.json`; provenance retained in `HISTORICAL_CSG_COMPARISON_20260926.md`.
- Exact circular control: `benchmarks/raw/composite_blanket_interop/c0_coil_controls.json` in the historical checkout.

Next measurements: cold geometry preparation/export for all three methods; full complex coil CSG versus built-in flat rings and target DAGMC; nonaxisymmetric plasma CSG versus built-in OpenMC torus and target DAGMC. Preserve matched histories, source, materials/data, hardware/threads, tally and output policy. Record loading separately and retain actual process wall. Validate custom target fidelity, first intersections and scoring alongside speed. Existing coil and plasma owners have these requirements; no new compute was launched to prepare this report.
