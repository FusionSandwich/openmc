# StellarCSG best results and continuation

Reviewed September 30, 2026. This brief selects the next development work for complex coil packs and nonaxisymmetric plasma, preserving the strongest historical results and the failures that prevent their unrestricted reuse. The three previous local owners completed their last recorded work; this review found no later result in their terminal turns. No new benchmark or software build was run to prepare this brief.

**Recommended starting points:** P00 native facet/priority-component CSG for actual winding-pack development; local periodic spline patch/BVH with the checked OpenMC adapter for general plasma. Recover the older shared-coil/span BVH as a correctness-gated alternative. Neither target has a qualified winner meeting all accuracy, usability and native-proxy speed requirements.

## Goal and timing rule

Reproduce complex stellarator plasma boundaries and actual coil winding-pack shapes while achieving transport elapsed time **at most 1.25 times** similarly sized simplified built-in OpenMC CSG: a torus for plasma and flat rings for coils. This expresses the user's goal of at least 80% as fast. A 10 s proxy permits 12.5 s custom transport. Report seconds, with geometry build, initialization, output and process wall separate. Compilation is not geometry construction. UNKNOWN is not zero.

Acceptance requires at least 20,000 completed histories per run, matched physics/source/data/hardware/threads/tallies/output, sufficient duration and repetitions, and independent geometric and scoring validation. Deliberately simpler proxies are allowed; declare occupancy and material-path differences. Keep the custom target complex. Current pinned inputs are WISTELL-D; the user's W7-D wording has not been resolved to a different dataset. MAKEGRID filaments alone do not determine the winding-pack section and frame.

## Best current target candidates

| Target and comparison | Histories each | Custom transport s | Reference transport s | Custom/reference time | Decision |
|---|---:|---:|---:|---:|---|
| Derived P00 periodic pack facets versus fixed 30 by 30 cm built-in rings | 20,000 | **5.774115369** | **1.203532667** | **4.797639** | Best executed pack candidate; speed gate fails |
| General WISTELL plasma versus similarly sized built-in torus | 20,000 | **34.819716296** | **0.218000213** | **159.723313** | Selected general architecture; speed gate fails |
| General plasma runtime replay, checked current versus rebuilt old source | 20,000 | **28.970192386** | **27.225501160** | **1.064083** | Runtime diagnostic only; reference here is old CSG, not a torus |

The old plasma rebuild is the fastest variant in its two-runtime replay. Its unchecked unresolved-boundary handling makes it ineligible for production promotion. The selected checked implementation preserves failure handling. Do not divide replay times by the earlier torus timer and call it a new matched comparison.

The coil pair repeats the same P00 implementation, not an optimization from its earlier 7.836203 s observation. All 1,016 retained raw custom tally values were identical across those observations. This supports reproducibility of those serialized scores, not a portable timing improvement or physical accuracy proof.

| Matched proxy pair phase | Coil custom s | Flat rings s | Plasma custom s | Torus s |
|---|---:|---:|---:|---:|
| Cold geometry construction | UNKNOWN | UNKNOWN | UNKNOWN | 0.026043402 primitive/model/export |
| Reused preparation/export | 0.1445532 | 0.156726508 | 0.0227205 | n/a |
| Initialization | 5.276662125 | 5.130763384 | 8.908987740 | 7.985720082 |
| Transport | 5.774115369 | 1.203532667 | 34.819716296 | 0.218000213 |
| Statepoint output | 0.030490800 | 0.024877401 | 0.318504214 | 0.348096621 |
| Native process wall | 11.152920394 | 6.440697556 | 44.185278351 | 8.643225121 |

The coil pair uses a frozen 18-site, 1 MeV entry bank and Fe56. Initially all custom sites are void; four fixed-ring sites are iron. The plasma pair uses a frozen 256-site, 14.1 MeV bank and solid Fe56, not physical plasma composition. Proxy shapes change trajectories and work. These measured gaps cannot yet be assigned entirely to geometry-query overhead. Summed tally estimators are not actual collision or crossing counters.

The P00 fixture is derived by periodic seam repair with maximum recorded cap-vertex movement 0.003328773593059 cm. That is not a continuous CAD error certificate. Eighteen component selectors do not establish eighteen distinct physical-coil owners. First-root, normal, continuous fidelity and per-coil/local-bin acceptance remain open.

## Faster historical evidence to preserve

These groups have different workloads and are not one sortable league. Seconds are measured elapsed records, not inverted throughput or extrapolated history counts.

| Geometry and workload | Histories per run and repetitions | CSG transport s | Reference transport s | What it establishes |
|---|---|---:|---:|---|
| Exact circular coil C0 | 1,000,000; 7 | **1.3670** exact native dispatch | **1.4343** built-in ZTorus | Genuine analytic success; forced-general same-solid path took 14.5390 s |
| 48 WISTELL centerlines with 1 cm round tubes | 100,000; 7 | **0.33282** local spans/shared BVH | **1.4176** coarse, **2.0173** fine ordinary DAGMC | Strongest preserved set-level architecture; near-vacuum H1, no tallies, leakage 1.0; not physical packs |
| Representative round-tube coil 031 | 100,000; 7 | **0.21899** local spans | **0.096937** fine ordinary DAGMC | DAGMC was faster for this single-coil case |
| Historical general WISTELL plasma | 10,000; 5 | **0.36314** local patches | **0.45281** fine ordinary DAGMC | Useful general architecture; below new history minimum, leakage 0.9955 versus 1.0 unresolved |
| Same P00 material-entry bank | 360; 1 | **0.37243** priority components | **0.72726** common-material union | Supports priority variant first; insufficient production timing or continuous-target proof |

Historical 48-tube process-wall medians were 2.45968 s CSG versus 12.27502 s fine ordinary DAGMC; initialization was 1.4192 versus 9.4735 s. Historical cold build times were not retained. Ordinary DAGMC results must not be labeled Embree. The currently verified comparisons do not include a runnable same-target Embree pack benchmark.

## Source and runtime identities

The publication checkout is `stellarcsg-astra-kernel-20260926`, branch `JS/stellarcsg-astra-kernel-20260926`, evidence baseline commit `ecd66adf7885d0f6e49c6f6dec7ad3e70df8c278`. Remote is `FusionSandwich/openmc`, draft [PR 5](https://github.com/FusionSandwich/openmc/pull/5). A later documentation commit does not change the identities of historical timed binaries.

| Route | Bound source or runtime |
|---|---|
| P00 pack candidate | Branch `JS/stellarcsg-local-continuation-20260925`; source checkpoint `3b61ee47fa498e2b4171756e5352f57de80de2a4`; library SHA256 `fbc38dedc17e20342a56dd50e2d56f86330238dae00b95ab3e4602864967cba4` |
| P00 repaired periodic fixture | External sibling `stellarcsg-local-continuation-20260925/dev/stellarcsg/reports/local-cont-20260925/p00-periodic-facet-candidate-02.h5`; SHA256 `3db1723d250319d7e6e3d0a4cbbba7b88a68c830fba4214d001a8c2c2545c2d4` |
| General plasma checked runtime | Current Astra lineage; retained library SHA256 `f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6` |
| Old plasma source replay | Composite checkpoint `3041a938c3fb0bc349654f37b0b3ebcd3cd5a9bb`; rebuilt library SHA256 `67afbe7df15dd677fd63ba8c9d8fda45824f46c0abd6579832bcec453a092ff8`; diagnostic only |
| Historical shared-coil/span BVH | Branch `codex/stellarcsg-native-csg-foundation-20260828`; checkpoint `5faf87421d5d2066278c7ae02e38138fc22ec894`; original campaign evidence `1353d0ae5d2d64422cc7dd8a6f144cdabfa0d000` |

Runtime and payload hashes, not a branch name alone, bind measurements. Raw HDF5, CAD, libraries and nuclear data are local artifacts and are not all available from GitHub text receipts.

## Failed attempts and conditions for revisiting them

| Attempt | Why it did not qualify | Required change before another campaign |
|---|---|---|
| Old generic swept first-root solver | Retained a03/a06/a08/a15 counterexamples; one returned about 0.502 cm instead of first entry near 0.002 cm | Demonstrate repaired earliest-root and tangent/prefix coverage on the frozen same-solid bank |
| Current legacy rounded-frame replay | Surface 10 unresolved nearest-boundary abort, exit -6 | Resolve the specific query; preserve an explicit failure, not infinity or silent retry |
| Old near-circle runs around 0.23 s | Source gate predicts approximate circle dispatch to averaged analytic torus | Prove genuinely analytic admission, or explicitly force general and validate it; no generic-speed claim from this run |
| Candidate B/D, Bernstein, Bezier atlas and torus-arc routes | Earlier roots, even contacts, incomplete domains or blocked budget remained | Identify and fix a concrete retained counterexample or supply a new completeness argument before rerunning |
| Certified global round offset/cache | 20k transport 167.48994 s, repeat 165.927178 s; restricted shape and costly global work | Use as a narrow reference; do not select it for full packs without new architecture and shape admission |
| Conservative BVH proposal | Source design only, not compiled native performance | Prove enclosure, touching-box retention, rounding, domain coverage and stack behavior; retain uncertain nodes |
| Plasma direct analytic evaluate/normal proposal | Isolated Boolean-sense probe failed | Diagnose and fix the failure; passing self-tests or fewer checks do not qualify promotion |
| Generic Newton failure treated as no hit | Seed failure is not complete no-hit evidence; exclusion counters can describe dropped candidates | Audit earliest-root/no-hit coverage independently; keep explicit unresolved results |
| Ruled polynomial/rational faces | Useful degree-at-most-six reference and synthetic sweeps; native general-ruled NOT_RUN, annulus speed failed | Import and audit actual pack framing/trims/seams, then implement bounded native tracking |
| Offline owner certificates or removed owner rechecks | Restricted offset proof; removing checks helped completed hits but barely whole bank; thin case remained unresolved | Bind to actual shape/domain; resolve the thin-pair case, preserve ownership and earlier-root checks |
| Inflated PCA ring envelopes | Apparent 7.836/8.652 s pass used widths 64–260 cm and heights 13–408 cm | Use corrected fixed-section controls; never count envelope sizing as target-speed success |
| Union versus priority Boolean occupancy | Agreement on 262,144 sign assignments and finite tracks is not continuous CAD or distinct per-coil ownership | Validate actual spatial ownership and local tally bins independently |
| Total-only tally closure | Hid spherical-mesh equator bin redistribution; tiny-track shortcut also remains unqualified | Check individual bins, transforms, overlapping filters and partition ownership, not only sums |
| Historical Embree executable | Present hash does not provide currently runnable HDF/DAGMC/MOAB dependencies; current runtime has DAGMC off | Verify a runnable existing backend and same-target mesh before benchmark; follow inventory gate before acquisition |

The old 67% number was a fraction of exclusive geometry-service profile time. The 0.0176% number came from a standalone geometry-service workload, not native OpenMC elapsed transport. Neither belongs in the transport winner table. Earlier random-ray passes do not override subsequently retained adversarial failures. Pro-chat prototype bundles remain destination-reported until independently imported and checked.

No evidence establishes mathematical impossibility or a need for a new general theorem. Current blockers are costly complete queries, incomplete earliest-boundary/ownership semantics, target binding and native usability. A new containment or completeness proof can justify a specific acceleration; it must cover the actual executed domains.

## Work for the new local chat

1. Read the goal, method map, this brief and linked raw receipts. Verify current working state and exact source/runtime/payload bindings. Use the actual Astra subrepository, not the parent workspace repository. Identify the P00 code path and retained facet/component profile support before proposing changes.
2. Diagnose P00 first because it is the executed pack candidate closer to the proxy gate. Count actual collisions, boundary crossings, distance/classification/normal calls and work per call. Separate facet/component traversal and ownership cost from physics and tally cost. Record profile overhead separately; acceptance remains uninstrumented elapsed transport seconds. Summed scores cannot substitute for event counts.
3. Freeze an independent same-solid correctness bank: misses, earliest entries/exits, tangencies, thin chords, cap/seam events, competing components, normals and physical ownership. Reuse strict-old counterexamples when applicable; distinguish the represented facet solid from an unsupported continuous CAD assertion.
4. Make one conservative acceleration change justified by measured cost. First hypotheses: immutable component/facet bounds, front-to-back pruning against an admitted nearer hit, query reuse with exact state keys, and cheaper certain-inside/outside tests. Combine methods only when their contracts compose. No arbitrary truncated candidate lists or removal of unresolved/ownership checks.
5. Validate the changed logic independently, then run one bounded matched before/after campaign on existing local capabilities, with at least 20k histories, useful native durations and ordinary cell/material/local mesh tallies. Repeat or increase histories to resolve a concrete timing uncertainty, not as an indiscriminate rerun of every failed route. Preserve baseline runtime and failure artifacts.
6. For plasma, journal the checked patch/BVH call path and candidate/Newton/tangent work before selecting a delta. Do not restore the diagnostic unchecked adapter. Rerun a matched torus pair only after a correctness-accepted change or a specific workload question warrants it.
7. Report cold construction, reuse/export, loading, transport, output and process wall independently. Audit physical target/frame/section identity, source births and per-bin tally conservation. Keep same-target verified Embree comparison explicitly NOT_RUN until runnable and bound.
8. Publish the focused change, tests, exact timings, unsupported scope and next action. Change the selected method only when new evidence supports it. Update the method map and failure registry so another chat can continue without repeating discovery.

Before any compilation, dependency environment change or software acquisition, follow the user-wide live machine inventory and acquisition rules. Initial scope is read-only inspection and existing local capabilities. Do not fetch/install speculatively. Heavy local work uses the shared atomic lease `../local-coil-wave-20260926/compute.lock`, one CPU initially, finite time/memory limits and terminal receipts. Do not reclaim a lease from age alone, run broad overlapping campaigns, continuously poll healthy jobs or launch automatic successors. This brief does not authorize new SSH jobs or remote spending. Follow `C:/HTS_transport/AGENT_DELEGATION.md`; obtain separate Sol acceptance of consequential changed logic and scientific claims. Read repository `AGENTS.md` and its OpenMC code-review skill before code review or changes.

## Decisive evidence

- [Current method map](../METHOD_MAP.md) and [project goal](../PROJECT_GOAL.md).
- [Build and transport accounting](BUILD_TRANSPORT_RESULTS_20260926.md).
- [Historical measured seconds and artifact pins](HISTORICAL_ELAPSED_METHODS_010.json), [branch review](FASTEST_METHOD_BRANCH_REVIEW_20260926.md), and [development synthesis](CONSOLIDATED_DEVELOPMENT_20260926.md).
- [Corrected P00 pair](coil-profile-20260926/fixed-section-pair-010/SUMMARY.json), [independent terminal acceptance](coil-hybrid-accuracy-20260926/P00_FIXED_SECTION_TERMINAL_ACCEPTANCE_010.md), and [estimator limits](coil-hybrid-accuracy-20260926/P00_FIXED_SECTION_ESTIMATOR_ADDENDUM_010.md).
- [Matched plasma proxy result](plasma-best-time-20260926/RESULTS.md), [old/current replay](plasma-best-time-20260926/source-rebuild-010-01/comparison.json), and [independent replay acceptance](coil-hybrid-accuracy-20260926/PLASMA_TERMINAL_ACCEPTANCE_010.md).
- [Plasma final handoff](plasma-best-time-20260926/FINAL_TERMINAL_HANDOFF_010.md) preserves driver/native success and the separate wrapper cleanup failure plus documented lease release. Do not restart that completed build.

Some older reports retain historical milestone language. The current method map and this continuation brief govern the next development choice; historical claims retain their original workload and subsequent failure qualifications.
