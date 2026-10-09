# StellarCSG method and result catalog

Reviewed October 9, 2026 from retained local documentation, with a final late capture at 22:11:43 UTC. **81 entries** cover methods, individual repair/optimization variants, references and unexecuted proposals; this is not a count of 81 independent experiments.

The 32 M/I entries preserve the October 8 ledger's original rows in `METHOD_RESULTS.json`. Current addenda qualify later evidence without deleting the earlier outcomes. New H/B/R/L/Q/FT entries expose attempts that were missing or aggregated. All quantitative results below are historical records reviewed here, not new scientific reruns.

Status meanings: **PARTIAL** is useful in the stated domain; **FAILED/REJECTED** records a failed gate; **UNRESOLVED** is not HIT or NO_HIT; **NOT_RUN/NOT_IMPLEMENTED** establishes no execution; **REPORTED** is source-reported evidence, without new independent physical acceptance. A restricted independent acceptance stays restricted.

Navigation: [audit findings](AUDIT_FINDINGS.md), [all 309 distinct Markdown records](DOCUMENTATION_INDEX.md), [machine-readable catalog](METHOD_RESULTS.json), [original October 8 ledger](source_snapshots/af1e5df136ac202f17fc10f969bed7b67636dbdd689cf42ed4814a02297a3754.md).

## Entry index

| ID | Method or variant | Current status |
| --- | --- | --- |
| [M01](#m01) | Broad reference/global searches | REFERENCE / INCOMPLETE GENERAL ROOT COVERAGE |
| [M02](#m02) | Exact torus and circular-coil specialization | PARTIAL: EXACT ANALYTIC INPUTS |
| [M03](#m03) | Shaped axisymmetric and synthetic helical paths | PARTIAL; NATIVE SHAPED/HELICAL GATES NOT_RUN |
| [M04](#m04) | Local periodic plasma patches and BVH | FAILED HISTORICAL GATE; LATER OPTIMIZATION DIAGNOSTICS |
| [M05](#m05) | Local swept spans and shared 48-coil BVH | PARTIAL ROUND-TUBE SPEED; PHYSICAL PACK UNQUALIFIED |
| [M06](#m06) | Legacy projected Newton/sign scans and fast recovery | FAILED GENERAL SOLVER |
| [M07](#m07) | Original Bernstein degree-ten coil solver | FAILED; FINAL PATCH UNRECOVERED |
| [M08](#m08) | Candidate B torus-arc quartics | BLOCKED / APPROXIMATION ONLY |
| [M09](#m09) | Bézier Cartesian plasma atlas | NOT ADMITTED; FINAL ARTIFACT UNRECOVERED |
| [M10](#m10) | Candidate D hierarchy/solver | REJECTED AUTHORITATIVE SOLVER |
| [M11](#m11) | Exact-control constant-metric offset with certified Bernstein prefix | ACCEPTED RESTRICTED SCALAR CORRECTNESS / INTERNAL SPEED |
| [M12](#m12) | Immutable full-span interval cache | ACCEPTED NARROW CACHE PATCH / PARTIAL SPEED |
| [M13](#m13) | Conservative hierarchy/bounds proposals | PROPOSAL; REAL COMPILED AUDIT NOT_RUN |
| [M14](#m14) | P00 native facets with priority components | HISTORICAL FAIL; LATER REPORTED TIMING PASS; PHYSICAL GATE OPEN |
| [M15](#m15) | P00 component-AABB exterior classification | PARTIAL FINITE CLASSIFICATION / CONFOUNDED TRANSPORT EFFECT |
| [M16](#m16) | Offline normal ownership/reach certificates | PRO-REPORTED PROTOTYPE / PHYSICAL BINDING OPEN |
| [M17](#m17) | Direct ruled cubic/rational rectangular faces | PRO-REPORTED SYNTHETIC REFERENCE; GENERAL NATIVE NOT_RUN |
| [M18](#m18) | Canonical cardinal-spline/Krawczyk swept alternative | PRO-REPORTED STANDALONE; PROOF UNACCEPTED |
| [M19](#m19) | General radical-free polynomial elimination | PROPOSAL NOT_IMPLEMENTED |
| [M20](#m20) | Interval Newton/Krawczyk across joined patches | PARTIAL PROOF INGREDIENT |
| [M21](#m21) | Conservative analytic sandwiches and planar-normal specialization | PROPOSAL / UNMEASURED |
| [M22](#m22) | Plasma direct evaluate/normal shortcut and cache-only proposal | REJECTED NORMAL/SENSE SHORTCUT; CACHE PROPOSAL UNBUILT |
| [M23](#m23) | Native exact event handling with dyadic arithmetic | ACCEPTED RESTRICTED DETERMINISTIC NATIVE EVENT SLICE |
| [I01](#i01) | Ordinary DAGMC coarse/fine references | PARTIAL MESH REFERENCES / DEBUG NEGATIVES |
| [I02](#i02) | Double Down/Embree backend | HISTORICAL VERIFIED BACKEND; CURRENT TARGET NOT_RUN |
| [I03](#i03) | Period import and coil frames | PARTIAL IMPORT; HELD-OUT FIT REJECTED |
| [I04](#i04) | Source model and source binding | PARTIAL INTERFACES; PHYSICAL PREDICTIONS FAILED |
| [I05](#i05) | Native tally/source integration | PARTIAL FINITE NATIVE INTEGRATION |
| [I06](#i06) | Spherical mesh equator and short-flight traversal | PARTIAL EQUATOR REPAIR; TINY-TRACK NATIVE OPEN |
| [I07](#i07) | MeshFilter identity and HDF5 rotation | ACCEPTED NARROW IDENTITY/HDF REPAIR |
| [I08](#i08) | Portable runner and adapter repair | PARTIAL VALIDATOR/ADAPTER REPAIR |
| [I09](#i09) | Counter census and same-build performance protocol | OFFLINE PREPARATION PASS; ORIGINAL NATIVE MATRIX NOT_RUN |
| [H01](#h01) | Track B capsule/admissible seed recovery | PARTIAL; WRONG ROOTS REMAIN |
| [H02](#h02) | Track A floating admissible seed and removal of unsafe proxy pruning | PARTIAL; NOT COMPLETE |
| [H03](#h03) | Exact rational resultant/gcd/Sturm circular reference | REFERENCE PASS IN RESTRICTED DOMAIN; TOO COSTLY |
| [H04](#h04) | Shared exact-query reuse and exact-work accounting | PARTIAL REUSE / DIAGNOSTIC |
| [H05](#h05) | Outward floating BVH and Bernstein sign exclusion before exact solve | PARTIAL; SPEED INCONCLUSIVE |
| [H06](#h06) | Exact-rational monotone isolation before gcd/Sturm | REFERENCE-CONSISTENT INTERNAL SPEED |
| [H07](#h07) | Old plasma source reproduction versus current implementation | COMPLETED MATCHED DIAGNOSTIC |
| [H08](#h08) | Adaptive VMEC radial spline fit and single-chart admission | SAMPLED FIT SELECTED; GENERAL ADMISSION PARTIAL |
| [H09](#h09) | Candidate A outward 2-D Bernstein interval-cover exclusion | CONDITIONALLY APPROVED EXCLUSION; HOT PATH REJECTED |
| [H10](#h10) | Final-iterate residual recomputation | REJECTED AS COMPLETE REPAIR |
| [H11](#h11) | Process all queued nearer unresolved spans | REJECTED FOR PROMOTION |
| [H12](#h12) | Broad crossing conditioning | EXPERIMENTAL OVERBLOCKING |
| [H13](#h13) | Broad crossing conditioning plus outward center/radius bounds | EXPERIMENTAL OVERBLOCKING |
| [H14](#h14) | Narrow acceptance plus ordering and bounds | REJECTED FOR PROMOTION |
| [H15](#h15) | Isolated narrow acceptance repair | EXPERIMENTAL; NOT PROMOTED |
| [H16](#h16) | Recovered-seed clipped one-period native transport versus old and exact | COMPLETED DIAGNOSTIC; PERIODIC MODEL UNQUALIFIED |
| [B01](#b01) | Physical-normal multilayer blanket compiler | PARTIAL GEOMETRY; WISTELL ENGINEERING CLEARANCE FAIL |
| [B02](#b02) | Combined native plasma, blanket and coil model with Boolean cutouts | PARTIAL SMOKE / PARTITION |
| [B03](#b03) | Native CSG outer fill with fine DAGMC torus hybrid | PARTIAL INTEROPERABILITY / HISTORICAL VERIFIED EMBREE |
| [R01](#r01) | Exact represented-facet topology and component-AABB certificate | CONDITIONAL REPRESENTED-SOLID PREMISE; OWNER COUNTEREXAMPLES |
| [R02](#r02) | Independent rational facet first-event oracle | COUNTEREXAMPLES_FOUND |
| [R03](#r03) | Native assembly and positive-gap localization | FAILED GENERAL EVENT/SCORING GATE |
| [L01](#l01) | Density ladder with collision workload matching | LADDER01 INCONCLUSIVE; LADDER02 GEOMETRY_BOUND |
| [L02](#l02) | Transport stack profiling and plasma workload attribution | COMPLETED DIAGNOSTIC |
| [L03](#l03) | v1 inline nextafter with std::memcpy bit casts | REJECT_EFFECT |
| [L04](#l04) | v2 inline nextafter with __builtin_memcpy bit casts | REPORTED ACCEPT_SPEEDUP_EVIDENCE |
| [L05](#l05) | v3 normal precompute and exact early reject | UNDECIDED EFFECT |
| [L06](#l06) | P00 gate01 with v2+v3 | PASS_MEDIAN; ROBUST WORST PAIR FAILS |
| [L07](#l07) | v4 opt-in plasma collision-distance ceiling | REPORTED ACCEPT_SPEEDUP_EVIDENCE |
| [L08](#l08) | v5 facet distance ceiling | FINITE BITWISE CONTROLS PASS |
| [L09](#l09) | v6 exact periodic-spline indexing | FINITE BITWISE CONTROLS PASS |
| [L10](#l10) | P00 gate02 with v2–v6 and ceiling | INVALID OVERALL |
| [L11](#l11) | P00 gate03 warmup-discarded replication | REPORTED PASS_ROBUST TIMING ONLY |
| [L12](#l12) | v7 exact value-only plasma evaluation | UNDECIDED; NO MEASURABLE EFFECT |
| [L13](#l13) | v8 voxel clearance fast path | UNDECIDED EFFECT |
| [L14](#l14) | Plasma geometry-specific uniform-source diagnostics | IMPROVED; NATIVE 1.25 TARGET STILL MISSED |
| [L15](#l15) | Plasma ceiling counters and matched profile | REPORTED DIAGNOSTIC; ORACLE VALIDATION OPEN |
| [Q01](#q01) | Exact candidate hierarchy, closed ceiling, query reuse and root scheduling composition | ACCEPTED_REFERENCE_COMPOSITION_ONLY |
| [Q02](#q02) | Exact rational quartic Sturm root isolation with conservative scalar scheduler | ACCEPT_SCOPED_REFERENCE |
| [FT-001](#ft-001) | Fourier displacements added to a reference torus | SYNTHETIC RECONSTRUCTION PASS |
| [FT-002](#ft-002) | Global torus fit, coefficient bounds and quartic candidates | SCOPED CONTROLS PASS; GENERAL QUERIES UNRESOLVED |
| [FT-001-B](#ft-001-b) | Boolean combinations of complete coaxial torus solids | RESTRICTED FAMILY COUNTEREXAMPLE; NOT_EXECUTED |
| [FT-001-C](#ft-001-c) | Nonlinear coordinate map to a reference torus | PROPOSAL NOT_IMPLEMENTED |
| [FT-003](#ft-003) | Fourier-guided osculating torus patch atlas | APPROXIMATION; NO CLOSED SOLID |
| [FT-004](#ft-004) | Constant-weight torus polynomial sums compiled to quartic | COMPILATION PASS; LIMITED FIT |
| [FT-005](#ft-005) | Torus plateaus plus localized cubic-Hermite joins in one hierarchy | C1 SYNTHETIC CONSTRUCTION; QUERIES UNRESOLVED |
| [FT-006](#ft-006) | All-spline synthetic periodic-radius comparator | SAMPLED ACCURACY IMPROVES; QUERIES UNRESOLVED |
| [FT-007](#ft-007) | Direct radial Fourier versus frozen incumbent bicubic evaluator | SCOPED SYNTHETIC DIAGNOSTIC; QUERIES UNRESOLVED |
| [FT-008](#ft-008) | Full35-coefficient local algebraic quartic fits | APPROXIMATE ATLAS; NO CLOSED SOLID |

## Historical geometry

<a id="m01"></a>

### M01 — Broad reference/global searches

**Status:** REFERENCE / INCOMPLETE GENERAL ROOT COVERAGE.

**Recorded result:** Independent reference machinery and general periodic/swept evaluation supplied correctness controls.

**Failures and limits:** Expensive dense/global refinement; old swept implementation lacked complete first-root certification.

**Evidence:** [PERFORMANCE_REDESIGN_FINAL_REPORT.md](source_snapshots/a4ca91c1f0e40f58d93f4c092f55213b59f475017838a45ff294eb2ec3f93772.md), [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md), [APPROACH_REGISTRY.md](source_snapshots/63dc9726784b3048549dc949a1175f58ef57b3928985f5f19219c0b8ef2906ae.md).
<a id="m02"></a>

### M02 — Exact torus and circular-coil specialization

**Status:** PARTIAL: EXACT ANALYTIC INPUTS.

**Recorded result:** C0 exact dispatch: 1.3670 s versus native 1.4343 s, seven 1M-history observations. Native torus helpers can avoid generic solving.

**Failures and limits:** Analytic controls do not reproduce nonaxisymmetric plasma or physical packs. Near-constant recognition previously admitted inappropriate specialization and was repaired.

**Evidence:** [FASTEST_METHOD_BRANCH_REVIEW_20260926.md](source_snapshots/c344b2767132815999f82ee29a2550555b985c20b1e3a27d0eb19e7a0425eb20.md), [HISTORICAL_ELAPSED_METHODS_010.json](source_data/c731a0de005e6618c5db75a6038825532a0778dd0df2301c97249a1c81946b00.json), [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md).
<a id="m03"></a>

### M03 — Shaped axisymmetric and synthetic helical paths

**Status:** PARTIAL; NATIVE SHAPED/HELICAL GATES NOT_RUN.

**Recorded result:** Detection/evaluate/normal and some correctness machinery exist in early reports.

**Failures and limits:** Shaped/helical OpenMC performance gates were NOT_RUN; exact-torus ray campaigns were sometimes broader than their actual shape scope.

**Evidence:** [PERFORMANCE_REDESIGN_FINAL_REPORT.md](source_snapshots/a4ca91c1f0e40f58d93f4c092f55213b59f475017838a45ff294eb2ec3f93772.md), [FINAL_TECHNICAL_BOUNDARIES.md](source_snapshots/29bf0886741598de0cf45553d24b2c5a8148eb7809f815c9864dc89964c8e7b5.md).
<a id="m04"></a>

### M04 — Local periodic plasma patches and BVH

**Status:** FAILED HISTORICAL GATE; LATER OPTIMIZATION DIAGNOSTICS.

**Recorded result:** Conservative local patches, proxy proposals, damped Newton and local recovery. Historical 0.36314 s/10k versus ordinary DAGMC 0.45281 s.

**Failures and limits:** Historical leakage mismatch; current solid-Fe56 torus-proxy ratio 159.7233 FAIL. Generic Newton failure is not a no-hit proof.

**Later evidence (earlier result retained):** Later plasma ceiling variants report large improvements on the original unequal-source workload. More work-matched geometry-specific source diagnostics still give 2.100163 and 2.119799 custom/torus, above 1.25. They are different experiments, not a replacement replay of the 159.7233 failed gate. See L07/L14.

**Evidence:** [METHOD_MAP.md](source_snapshots/0c0f4398c44da682a5c87546bd2c9799d949a9e82f8b5f7d21c950e389da3952.md), [FASTEST_METHOD_BRANCH_REVIEW_20260926.md](source_snapshots/c344b2767132815999f82ee29a2550555b985c20b1e3a27d0eb19e7a0425eb20.md), [PERFORMANCE_REDESIGN_FINAL_REPORT.md](source_snapshots/a4ca91c1f0e40f58d93f4c092f55213b59f475017838a45ff294eb2ec3f93772.md), [SOURCE_REVIEW.md](source_snapshots/90fa80d698137a49024982bdc255f9b29ed3d2e85cd531c156ab5ab527edc221.md), [CALL_PATH_AUDIT_009.md](source_snapshots/3888cef808f5a6daec92dd336a759e8540621590978b0a54d97b4fc1acf60902.md), [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md), [SUMMARY.json](source_data/979d45a5f1fc68268d17d1c5d2e080acd903b4b260488a64f4487009a80a56c0.json).
<a id="m05"></a>

### M05 — Local swept spans and shared 48-coil BVH

**Status:** PARTIAL ROUND-TUBE SPEED; PHYSICAL PACK UNQUALIFIED.

**Recorded result:** Cubic control hulls, conservative boxes, local narrow phases; 48-tube set 0.33282 s/100k versus 2.01730 s fine ordinary DAGMC.

**Failures and limits:** Single-coil native slower than mesh. Round 1 cm tubes/near-vacuum/no tallies, not actual packs. Later a03/a06/a08/a15 root failures block unchanged reuse.

**Evidence:** [FASTEST_METHOD_BRANCH_REVIEW_20260926.md](source_snapshots/c344b2767132815999f82ee29a2550555b985c20b1e3a27d0eb19e7a0425eb20.md), [HISTORICAL_ELAPSED_METHODS_010.json](source_data/c731a0de005e6618c5db75a6038825532a0778dd0df2301c97249a1c81946b00.json), [PERFORMANCE_REDESIGN_FINAL_REPORT.md](source_snapshots/a4ca91c1f0e40f58d93f4c092f55213b59f475017838a45ff294eb2ec3f93772.md), [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md).
<a id="m06"></a>

### M06 — Legacy projected Newton/sign scans and fast recovery

**Status:** FAILED GENERAL SOLVER.

**Recorded result:** Recovered/compiled fast source; strict failures reproducible; later earlier-entry repair supplied useful witnesses.

**Failures and limits:** Wrong first entry around 0.502 cm instead of 0.002 cm; saved strict result 73 unresolved/87 no-hit. Increasing seeds/residual changes did not close completeness and could slow it. Current legacy native replay aborted unresolved, exit -6.

**Evidence:** [FASTEST_METHOD_BRANCH_REVIEW_20260926.md](source_snapshots/c344b2767132815999f82ee29a2550555b985c20b1e3a27d0eb19e7a0425eb20.md), [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md), [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md), [APPROACH_REGISTRY.md](source_snapshots/63dc9726784b3048549dc949a1175f58ef57b3928985f5f19219c0b8ef2906ae.md).
<a id="m07"></a>

### M07 — Original Bernstein degree-ten coil solver

**Status:** FAILED; FINAL PATCH UNRECOVERED.

**Recorded result:** Constructive algebraic elimination and root isolation ideas.

**Failures and limits:** Reported stress bank 32 wrong/160; apparent strict success used 12 sampled fallbacks, and every stress ray used fallback. Roughly 90% strict cost was fallback; candidate cost about 253 times old. Final fail-closed patch was not applied before disconnection.

**Evidence:** [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md).
<a id="m08"></a>

### M08 — Candidate B torus-arc quartics

**Status:** BLOCKED / APPROXIMATION ONLY.

**Recorded result:** Opt-in fitting and quartic candidate prototype.

**Failures and limits:** 160/160 blocked strict and stress; C0 rather than intended G1 chain; tangent mismatch 0.002010197 rad; continuous fidelity and owner/root proof absent.

**Evidence:** [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md).
<a id="m09"></a>

### M09 — Bézier Cartesian plasma atlas

**Status:** NOT ADMITTED; FINAL ARTIFACT UNRECOVERED.

**Recorded result:** Atlas-local classification and interval/Newton framework.

**Failures and limits:** Inclusion returned Boolean and discarded parameter enclosure; point-estimated ray distance drove pruning. Grazing residual cannot bound longitudinal error. Final patch unavailable in retained review.

**Evidence:** [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md).
<a id="m10"></a>

### M10 — Candidate D hierarchy/solver

**Status:** REJECTED AUTHORITATIVE SOLVER.

**Recorded result:** Useful candidate-generation/hierarchy diagnostics.

**Failures and limits:** All strict/stress unresolved. Near-parallel false exclusion, clipped leads, radius bounds, heuristic padding and deduplication were unsafe. Candidate-only timings omitted completion cost.

**Evidence:** [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md).
<a id="m11"></a>

### M11 — Exact-control constant-metric offset with certified Bernstein prefix

**Status:** ACCEPTED RESTRICTED SCALAR CORRECTNESS / INTERNAL SPEED.

**Recorded result:** Native shaped seam entry/exit; frozen 160 scalar queries independently certified, 69 hits/91 misses in both modes. Same-binary prefix on/off summed-distance gain 4.052; child-wall gain 2.605. Exact positive tiny contact and even-contact mechanisms retained.

**Failures and limits:** Restricted circular or constant planar-ellipse metric, different from legacy varying frames/rectangular packs. Nine normal/projection gaps; imported scalar coil rows all misses. No full physical target qualification.

**Evidence:** [APPROACH_REGISTRY.md](source_snapshots/63dc9726784b3048549dc949a1175f58ef57b3928985f5f19219c0b8ef2906ae.md), [PERFORMANCE_REVIEW.md](source_snapshots/701bc7b22a2ad14ed1a9c391cf113373932914a8cb53ceba3b55cd9ff28f4d5f.md), [final-acceptance.json](source_data/8210d88c008055ea8e948e463c5aac7bf4f0461ebebcdfd2d2cc76878fecc8be.json), [ALGORITHM_CONTRACT.md](source_snapshots/6c09a0d3b43d124e6350ea9264db61eb4652213f47b80bec60ac6d764a1f0de2.md).
<a id="m12"></a>

### M12 — Immutable full-span interval cache

**Status:** ACCEPTED NARROW CACHE PATCH / PARTIAL SPEED.

**Recorded result:** Reuses identical outward interval expressions; finite scalar outputs unchanged, original nine normal errors retained. About 1.993 times complete primitive-workload improvement; later independent cache review accepted a narrow patch.

**Failures and limits:** Primitive workload only; 0.01761% of its analytic native control is not native transport throughput. Cached 20k round-offset transport still about 166–167 s and fails native proxy badly.

**Evidence:** [RESULTS.md](source_snapshots/c39272e8051ce21599e3bb9e164c27b448fc0fde03a48a7825e0e9fc69bf8aad.md), [CACHE_ACCEPTANCE_003.md](source_snapshots/b538912ccdc251d431b44c3e8f604976fad32606230a31eb6b59c60e33f0b75e.md), [FASTEST_METHOD_BRANCH_REVIEW_20260926.md](source_snapshots/c344b2767132815999f82ee29a2550555b985c20b1e3a27d0eb19e7a0425eb20.md).
<a id="m13"></a>

### M13 — Conservative hierarchy/bounds proposals

**Status:** PROPOSAL; REAL COMPILED AUDIT NOT_RUN.

**Recorded result:** Exact control hulls support conservative exclusion; compile-once bounds can avoid repeated expensive interval construction.

**Failures and limits:** Proposed global-offset BVH uncompiled/untimed; PR4 real compiled 640-span audit NOT_RUN in retained review. A topology pass cannot prove correct traversal or roots.

**Evidence:** [APPROACH_REGISTRY.md](source_snapshots/63dc9726784b3048549dc949a1175f58ef57b3928985f5f19219c0b8ef2906ae.md), [CACHE_ACCEPTANCE_003.md](source_snapshots/b538912ccdc251d431b44c3e8f604976fad32606230a31eb6b59c60e33f0b75e.md), [EMBREE_AND_METHOD_REVIEW_009.md](source_snapshots/c238d382c1b0bbd18fccc71421c8656164a2b972f678a35b8514a99402dac07c.md), [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md).
<a id="m14"></a>

### M14 — P00 native facets with priority components

**Status:** HISTORICAL FAIL; LATER REPORTED TIMING PASS; PHYSICAL GATE OPEN.

**Recorded result:** Directly relevant derived pack mesh; same 360-history bank 0.37243 s priority versus 0.72726 s union. Corrected 20k fixed-ring pair completed. Boolean occupancy test covered 262, 144 sign assignments.

**Failures and limits:** Seam-repaired payload differs from accepted CAD; max cap-vertex move 0.003328774 cm is not a continuous fidelity certificate. 18 selectors not proven physical owners. Corrected speed ratio 4.797639 FAIL; later native contact/score failures.

**Later evidence (earlier result retained):** Later ladder gate-03 reports PASS_ROBUST on all three seeds; pooled P00/ring transport ratio 1.104614615471397. This is represented P00 versus fixed 30x30 cm rings, with independent physical/owner/native-event acceptance still open. Earlier 4.797639 failure, oracle conflicts and assembly failures remain. See L06/L10/L11 and R01/R02.

**Evidence:** [BEST_METHOD_CONTINUATION_20260930.md](source_snapshots/cfe640ee70cb056f197e3c6ecbb9526dc9e0b30e8478a86077a8aeb596a9b263.md), [FASTEST_METHOD_BRANCH_REVIEW_20260926.md](source_snapshots/c344b2767132815999f82ee29a2550555b985c20b1e3a27d0eb19e7a0425eb20.md), [SUMMARY.json](source_data/04d373bd12ec1f6ad8bc611f3635a88dd8e2ede7bfce9fd4d90f6a28f4f8030d.json), [P00_STEPS_1_TO_4_INTEGRATION_20261001.md](source_snapshots/bbe83368ae33ae5ac88f86e9c613a34672dd1de22f5040aa23c8305c3ab56170.md), [P00_ASSEMBLY_REPORT_20261001.md](source_snapshots/74b46871795458cc7cb271ab08edfc8b067a85b9117af6dfaa880341e6328472.md), [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md), [GATE.json](source_data/c88e910a8056d1042fd01fb6a3d9ceb65911fa5fdc40669ed65788c7aa9daea8.json).
<a id="m15"></a>

### M15 — P00 component-AABB exterior classification

**Status:** PARTIAL FINITE CLASSIFICATION / CONFOUNDED TRANSPORT EFFECT.

**Recorded result:** Avoids three parity rays on distant points. Same-command classification loops improve; all 1, 944 derived-payload sampled classifications agree. Two 100k seed pairs retain exact production raw sums/squares.

**Failures and limits:** Initial one-ULP exclusion rejected; repaired margin used instead. Observed 37–41% transport reduction is compiler/runtime-confounded. Candidate/ring 2.368/2.608 FAIL. Same-build stochastic matrix not run.

**Evidence:** [P00_BOUNDING_CLASSIFICATION_20260930.md](source_snapshots/1afdcf95fb9c70a3efb592b52a439a29d4aeea1a13ceef74e5e26481f041647b.md), [SUMMARY.json](source_data/d493059174eee35690a2ac86135e30fb36333574fe015d36197da01aba8961a4.json), [P00_STEPS_1_TO_4_INTEGRATION_20261001.md](source_snapshots/bbe83368ae33ae5ac88f86e9c613a34672dd1de22f5040aa23c8305c3ab56170.md).
<a id="m16"></a>

### M16 — Offline normal ownership/reach certificates

**Status:** PRO-REPORTED PROTOTYPE / PHYSICAL BINDING OPEN.

**Recorded result:** Pro-reported member-2 all-pairs admission: 256 spans, 65, 536 ordered pairs, transformed reach bound 1.25. Independent checker reported; useful compile-time invariant can remove one post-root owner recheck.

**Failures and limits:** Actual loader/frame/physical pack binding open. Whole diagnostic bank barely improves (about 0.99–1.02 times); thin crossing remains unresolved at roughly 216k system evaluations. Five nonvertical accepted hits lacked independent reference.

**Evidence:** [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md).
<a id="m17"></a>

### M17 — Direct ruled cubic/rational rectangular faces

**Status:** PRO-REPORTED SYNTHETIC REFERENCE; GENERAL NATIVE NOT_RUN.

**Recorded result:** Pro-reported complete synthetic reference; determinant polynomial degree at most six, complete event ledger/endcaps and six-crossing witness. 72 reported Python tests.

**Failures and limits:** General cubic C++/OpenMC backend absent. Annular standalone control only 6.099% median native-primitive query ratio; physical pack edge/frame/trims missing. Creases challenge one-normal whole-solid sense.

**Evidence:** [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md).
<a id="m18"></a>

### M18 — Canonical cardinal-spline/Krawczyk swept alternative

**Status:** PRO-REPORTED STANDALONE; PROOF UNACCEPTED.

**Recorded result:** Recovered Pro final reports standalone GCC/Clang/sanitizer controls, 48 high-precision comparisons and 15, 027 enclosure checks; shaped seam and consistent local predicates.

**Failures and limits:** Proof independently unaccepted; tangent/near-tangent unresolved. Original four failure IDs and frozen 160 not replayed. Adapter uncompiled.

**Evidence:** [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md).
<a id="m19"></a>

### M19 — General radical-free polynomial elimination

**Status:** PROPOSAL NOT_IMPLEMENTED.

**Recorded result:** Constructive H/Q equations; degree at most 26, planar constant ellipse at most 10. Exact root-isolation reference is possible.

**Failures and limits:** Not implemented in the local registry; B=0/A=0 exceptional branches, spurious solutions, endpoint rounding and global owner switches remain.

**Evidence:** [APPROACH_REGISTRY.md](source_snapshots/63dc9726784b3048549dc949a1175f58ef57b3928985f5f19219c0b8ef2906ae.md).
<a id="m20"></a>

### M20 — Interval Newton/Krawczyk across joined patches

**Status:** PARTIAL PROOF INGREDIENT.

**Recorded result:** Exact-control C2 seam contracts support joined derivative enclosures and local proof arcs.

**Failures and limits:** General variable-frame classifier and complete prefix coverage not established. Larger proof arcs initially rejected a rounded-square projection conservatively.

**Evidence:** [APPROACH_REGISTRY.md](source_snapshots/63dc9726784b3048549dc949a1175f58ef57b3928985f5f19219c0b8ef2906ae.md).
<a id="m21"></a>

### M21 — Conservative analytic sandwiches and planar-normal specialization

**Status:** PROPOSAL / UNMEASURED.

**Recorded result:** Inner/outer offset bounds can supply certain inside/outside tests. Exact orthogonality may simplify a specific thin pair.

**Failures and limits:** Positional fit alone cannot preserve tangency or hit count; qualifying direction fraction unmeasured; broad native timing absent.

**Evidence:** [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md), [CACHE_ACCEPTANCE_003.md](source_snapshots/b538912ccdc251d431b44c3e8f604976fad32606230a31eb6b59c60e33f0b75e.md).
<a id="m22"></a>

### M22 — Plasma direct evaluate/normal shortcut and cache-only proposal

**Status:** REJECTED NORMAL/SENSE SHORTCUT; CACHE PROPOSAL UNBUILT.

**Recorded result:** Isolated renamed-class build completed; eleven printed distance records agreed.

**Failures and limits:** Probe failed Boolean sense equivalence; exact point/direction absent. Later controls/timing stopped. Cache-only proposal unbuilt.

**Evidence:** [SOURCE_REVIEW.md](source_snapshots/90fa80d698137a49024982bdc255f9b29ed3d2e85cd531c156ab5ab527edc221.md).
<a id="m23"></a>

### M23 — Native exact event handling with dyadic arithmetic

**Status:** ACCEPTED RESTRICTED DETERMINISTIC NATIVE EVENT SLICE.

**Recorded result:** 33-word exact binary64 difference/order/rounding foundation passed directed controls and 5, 520 Fraction differential rows. Addresses a concrete positive-gap failure.

**Failures and limits:** Native functional repair was subsequently wired only in source; configure exit 124 before any build/native rows. Known fixture restoration issue. Narrow void axis-plane scope, no general facets/materials qualification.

**Later evidence (earlier result retained):** The October 1 configure timeout remains history. October 8 independent review and fresh integration accepted ONLY void, single-instance, unit-axis built-in plane events: 39 models / 208 rows / 154 supported / 54 expected rejections / 460 events. Integration replay matches the review rows and rejects five corrupt oracles. General facets, materials, physical performance and installation ABI remain outside acceptance.

**Evidence:** [P00_ASSEMBLY_REPAIR_DESIGN_20261001.md](source_snapshots/9d024e491107dd302073540e478ac4647fe3eb785249e5022c88b60d22154b10.md), [P00_DYADIC_AXIS_CHECKPOINT_20261001.md](source_snapshots/241d79a7adc95be2ae689112fc18fa3a52a6bbd5ff63fcffbacb8ebabcc599ea.md), [P00_ASSEMBLY_PLANES_FOCUSED_RESULT_20261001.md](source_snapshots/a82224df51ea4381b9c655a61f858654a17b5cd9087557a400ced7ef26533693.md), [P00_NATIVE_AXIS_CHECKPOINT_20261001.md](source_snapshots/6fe7566e7f3a168a9945f05a5fdafd03b968330aa83f535a27a46148d9d8458b.md), [failure.json](source_data/62c0c3ce982113053944eaa6c92bfb5485f2d7fdfe745322bccf13c75e8b8405.json), [AXIS_REVIEW_RESULT_20261008.json](source_data/934ff02007923a225f82e00ffac5677dc2c78cbf2ac32b8fd316a66c3fb97f6a.json), [INTEGRATION_RESULT_20261008.json](source_data/b7285d4180c90180e45e6762900bfef34c1ec3e309527bcf95b4bf7cd60e4bfc.json).

## Reference and integration

<a id="i01"></a>

### I01 — Ordinary DAGMC coarse/fine references

**Status:** PARTIAL MESH REFERENCES / DEBUG NEGATIVES.

**Recorded result:** Same-target historical mesh approximations and separately measured elapsed/initialization records.

**Failures and limits:** Single-coil versus full-set outcomes differ; mesh sampled deviations not two-sided Hausdorff certificates. Geometry-debug explicit-volume/implicit-complement complaint remains.

**Evidence:** [PERFORMANCE_REDESIGN_FINAL_REPORT.md](source_snapshots/a4ca91c1f0e40f58d93f4c092f55213b59f475017838a45ff294eb2ec3f93772.md), [FASTEST_METHOD_BRANCH_REVIEW_20260926.md](source_snapshots/c344b2767132815999f82ee29a2550555b985c20b1e3a27d0eb19e7a0425eb20.md).
<a id="i02"></a>

### I02 — Double Down/Embree backend

**Status:** HISTORICAL VERIFIED BACKEND; CURRENT TARGET NOT_RUN.

**Recorded result:** Genuine historical linkage/banner for a 10k hybrid torus; binary hash retained.

**Failures and limits:** Current runnable historical dependencies not established; current experimental runtime DAGMC OFF. Same-target WISTELL pack/plasma verified-Embree run absent.

**Evidence:** [EMBREE_AND_METHOD_REVIEW_009.md](source_snapshots/c238d382c1b0bbd18fccc71421c8656164a2b972f678a35b8514a99402dac07c.md), [FASTEST_METHOD_BRANCH_REVIEW_20260926.md](source_snapshots/c344b2767132815999f82ee29a2550555b985c20b1e3a27d0eb19e7a0425eb20.md).
<a id="i03"></a>

### I03 — Period import and coil frames

**Status:** PARTIAL IMPORT; HELD-OUT FIT REJECTED.

**Recorded result:** NFP=4 import, exact quarter-turn derived images, provenance repairs.

**Failures and limits:** 1 cm circular diagnostic envelope; physical clearance unknown. Held-out ParaStell fidelity 2.39627% rejected. Derived canonicalization changes geometry.

**Evidence:** [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md), [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md).
<a id="i04"></a>

### I04 — Source model and source binding

**Status:** PARTIAL INTERFACES; PHYSICAL PREDICTIONS FAILED.

**Recorded result:** Normalized PDF separated from rate; shutdown zero-rate handling; bank contracts, named-hash validation and analytic birth controls.

**Failures and limits:** Held-out source-rate errors +347.018%/+220.553%, ion-temperature profile error 60%. Analytic births not physical WISTELL source support/rate/clearance.

**Evidence:** [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md), [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md).
<a id="i05"></a>

### I05 — Native tally/source integration

**Status:** PARTIAL FINITE NATIVE INTEGRATION.

**Recorded result:** Six repaired finite proxy runs, 37 plasma and 18 approximate-coil comparisons; selected cell/material/mesh/current/energy/damage combinations.

**Failures and limits:** Sparse bins and instance-zero tests; not universal filters, transforms, parallel, photon or physics qualification.

**Evidence:** [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md), [RESULTS.md](source_snapshots/1fc917f7146cac9a486bfad186ffb624d8e0bc694d0c82d08be62158c92d6e93.md).
<a id="i06"></a>

### I06 — Spherical mesh equator and short-flight traversal

**Status:** PARTIAL EQUATOR REPAIR; TINY-TRACK NATIVE OPEN.

**Recorded result:** Native exact-equator/sign-height repair plus partial-grid indexing controls caught a defect that preserved integrated totals.

**Failures and limits:** A separate <2*TINY_BIT branch can assign a crossing track to one bin; retained counterexample was scaffold/extracted, native acceptance remains open.

**Evidence:** [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md).
<a id="i07"></a>

### I07 — MeshFilter identity and HDF5 rotation

**Status:** ACCEPTED NARROW IDENTITY/HDF REPAIR.

**Recorded result:** Transform-aware equality/hash; native 9/12-value matrix decoding. 13 targeted WSL Python tests, later independent review/publication.

**Failures and limits:** First Windows test could not collect against Unix DSO (WinError 193). Targeted tests not broad native transformed-statepoint transport.

**Evidence:** [RESULTS.md](source_snapshots/171aeb53648793647538f7a3f2ef7ec96ac966f670ecd20957605c92f43b866e.md), [ACCEPTED_PATCH_PUBLICATION_20260926.md](source_snapshots/ade2ef3666a2742e24398a100e6039f9044c90bb97da7ed5d497ab21d6e396d3.md).
<a id="i08"></a>

### I08 — Portable runner and adapter repair

**Status:** PARTIAL VALIDATOR/ADAPTER REPAIR.

**Recorded result:** Reported 76/76 validator mocks; child exit 7 propagation; duplicates rejected; controlled adapter pass counts improved.

**Failures and limits:** Mock versus native distinction; unresolved propagation, unions, identity ties, hidden NaNs and serialization retained.

**Evidence:** [CHAT_SYNTHESIS_20260926.md](source_snapshots/8b385cd81cf6ba6e5c1730bcd465b69907d611c8f50cd134e8842740f5d9dc3a.md), [USABILITY_METHOD_REVIEW_20260926.md](source_snapshots/9b48f90a94996393353a5b463be06122f45aef58f84238410a24b629d135a785.md), [comparison.json](source_data/4d3ab2737d821a24c8ce65f4a4d561998d2d9b3529c87826a3da172582993f4b.json).
<a id="i09"></a>

### I09 — Counter census and same-build performance protocol

**Status:** OFFLINE PREPARATION PASS; ORIGINAL NATIVE MATRIX NOT_RUN.

**Recorded result:** Matched libraries prepared; offline worker-epoch/uint64 checker and 65 rejection controls passed.

**Failures and limits:** Native hooks/checked increments not implemented; 18-run matrix NOT_RUN. Checker cannot detect unflagged producer wrap or missing instrumentation.

**Later evidence (earlier result retained):** The later ladder uses actual counting experiments and file rechecks; these are a separate scope from the original unimplemented 18-run census plan. Counting classifications do not independently certify the solver. See L01/L15.

**Evidence:** [P00_STEPS_1_TO_4_INTEGRATION_20261001.md](source_snapshots/bbe83368ae33ae5ac88f86e9c613a34672dd1de22f5040aa23c8305c3ab56170.md), [P00_COUNTER_CHECKER_ROOT_REVIEW_20261001.md](source_snapshots/e34a19837d721f4985e2e643ebd2331a10a24e0fa3e753c4257917d5d7a8df8f.md), [P00_COUNTER_CHECKER_CHANGE_20261001.md](source_snapshots/ad792cb0d08f6516cfd8fb8a6803ad4d2a21b69485c444edcf1831c5d38c51f4.md), [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).

## Earlier recovery and exact-reference variants

<a id="h01"></a>

### H01 — Track B capsule/admissible seed recovery

**Status:** PARTIAL; WRONG ROOTS REMAIN.

**Recorded result:** 81211f7b supplied an inside-capsule seed and recovered missed entry; later conditional-seed controls measured 1685.63 ns/query with 3 strict disagreements on the fresh 160 bank.

**Failures and limits:** Unsafe proxy pruning/completeness remain. Earlier-entry fix is not a first-root proof.

**Evidence:** [FAST_RECOVERY_04_HISTORY.md](source_snapshots/e62fbd2e5ff944a78427e740e5d84797950fef8ae60e14254b25d0018bfffa73.md), [FAST_RECOVERY_04_CHECKPOINT.md](source_snapshots/ff08ac2ef24d6c487504f1da83d66264eb618f7d50ba79c95baf3deb87a26f7a.md).
<a id="h02"></a>

### H02 — Track A floating admissible seed and removal of unsafe proxy pruning

**Status:** PARTIAL; NOT COMPLETE.

**Recorded result:** 4e1efc947 retained polynomial bank improved 273 PASS / 88 FAIL / 23 BLOCKED to 361 / 0 / 23; reported distance 2784.93 ns/query.

**Failures and limits:** Two tangent metamorphisms remain unresolved. Different bank from recovery04. Blocked domain and general native gates remain; prior-A fresh160 control still had 3 disagreements.

**Evidence:** [FAST_RECOVERY_04_HISTORY.md](source_snapshots/e62fbd2e5ff944a78427e740e5d84797950fef8ae60e14254b25d0018bfffa73.md), [FAST_RECOVERY_04_CHECKPOINT.md](source_snapshots/ff08ac2ef24d6c487504f1da83d66264eb618f7d50ba79c95baf3deb87a26f7a.md).
<a id="h03"></a>

### H03 — Exact rational resultant/gcd/Sturm circular reference

**Status:** REFERENCE PASS IN RESTRICTED DOMAIN; TOO COSTLY.

**Recorded result:** da7a5417 exact elimination and nearest-stationary classification: retained 384 replay 256 PASS / 0 FAIL / 128 BLOCKED. Recovery04 exact control costs 14.41848849 ms/query on its separate 160 bank.

**Failures and limits:** Constant circular binary64 cubics only; elliptic/variable frames unsupported. Reference domain blocks are not enforced by recovered production.

**Evidence:** [FAST_RECOVERY_04_HISTORY.md](source_snapshots/e62fbd2e5ff944a78427e740e5d84797950fef8ae60e14254b25d0018bfffa73.md), [FAST_RECOVERY_04_CHECKPOINT.md](source_snapshots/ff08ac2ef24d6c487504f1da83d66264eb618f7d50ba79c95baf3deb87a26f7a.md), [CONTINUATION_20260913.md](source_snapshots/ef4cb450359e243ffd2c86b877e069ebe85f7e1e5a1798866dc879ed114f12f8.md).
<a id="h04"></a>

### H04 — Shared exact-query reuse and exact-work accounting

**Status:** PARTIAL REUSE / DIAGNOSTIC.

**Recorded result:** 223ea7a1 reuses common exact query work and exposes exact cost.

**Failures and limits:** Reuse benefit is not cold-query or native throughput; retain bank and warm/cold distinctions.

**Evidence:** [FAST_RECOVERY_04_HISTORY.md](source_snapshots/e62fbd2e5ff944a78427e740e5d84797950fef8ae60e14254b25d0018bfffa73.md).
<a id="h05"></a>

### H05 — Outward floating BVH and Bernstein sign exclusion before exact solve

**Status:** PARTIAL; SPEED INCONCLUSIVE.

**Recorded result:** 0b56166b conservatively retains uncertain intervals before the exact solver.

**Failures and limits:** Aggregate speed gain inconclusive; distinct from failed original degree-ten solver and later 2-D interval cover.

**Evidence:** [FAST_RECOVERY_04_HISTORY.md](source_snapshots/e62fbd2e5ff944a78427e740e5d84797950fef8ae60e14254b25d0018bfffa73.md).
<a id="h06"></a>

### H06 — Exact-rational monotone isolation before gcd/Sturm

**Status:** REFERENCE-CONSISTENT INTERNAL SPEED.

**Recorded result:** dc76fbd1 / 5ed327ad: 64 mode comparisons identical, 384 replay 256/0/128. Separate 16-ray bank: mode2 2.1309001 ms vs mode0 82.4534045 ms; 1000-history diagnostic 7.05622 histories/s.

**Failures and limits:** 98.213% of instrumented time remains exact work. No arbitrary-precision-free/general fast transport claim.

**Evidence:** [FAST_RECOVERY_04_HISTORY.md](source_snapshots/e62fbd2e5ff944a78427e740e5d84797950fef8ae60e14254b25d0018bfffa73.md), [CONTINUATION_20260913.md](source_snapshots/ef4cb450359e243ffd2c86b877e069ebe85f7e1e5a1798866dc879ed114f12f8.md).
<a id="h07"></a>

### H07 — Old plasma source reproduction versus current implementation

**Status:** COMPLETED MATCHED DIAGNOSTIC.

**Recorded result:** Same-workload old source 27.225501 s versus current 28.970192 s; ratio 1.064083. Whitespace-normalized source bodies agree.

**Failures and limits:** Old boundary handling unsafe; diagnostic is not promotion. Unlike historical workloads cannot establish a 0.36-to-35-second regression.

**Evidence:** [METHOD_COMPARISON_REBUILD_010.md](source_snapshots/b6ba027053fd15b70598b46d50582e66235c9f834e65c82c95496165962d0d71.md), [comparison.json](source_data/4d3ab2737d821a24c8ce65f4a4d561998d2d9b3529c87826a3da172582993f4b.json).
<a id="h08"></a>

### H08 — Adaptive VMEC radial spline fit and single-chart admission

**Status:** SAMPLED FIT SELECTED; GENERAL ADMISSION PARTIAL.

**Recorded result:** Auto-fit errors: 64x32 7.8086% REJECT, 128x64 1.22134% REJECT, 256x128 0.099667% selected under declared 1% sampled target. Independent 4608 grid max0.2042205 cm / 0.119736% local radius, RMS0.018439 cm, P95 0.030255 cm.

**Failures and limits:** Initial separate off-grid 64x32 result 11.33767 cm / 8.16553% fails. Geometric-theta folds including held-out ParaStell rejected; sampled radial error is not normal/volume/Hausdorff certificate or periodic navigation.

**Evidence:** [PRODUCT_05_CHECKPOINT.md](source_snapshots/9878de2f0313e4a6aca5587f7f2a4e35cba2de4700fcf457c002815ffda83de3.md), [LOCAL_STELLARATOR_MODEL_CATALOG.md](source_snapshots/c2c770b1836508ca242fbff671e4e7aff8e22fee425df458f7f47e368b209d7a.md).
<a id="h09"></a>

### H09 — Candidate A outward 2-D Bernstein interval-cover exclusion

**Status:** CONDITIONALLY APPROVED EXCLUSION; HOT PATH REJECTED.

**Recorded result:** Executed Product05 bank: 90 ROOT_FREE / 70 UNRESOLVED, no saved-bank false exclusions; approximately 106397 ns/query.

**Failures and limits:** Certifies only stationary-equation exclusion under stated assumptions; no exact fallback, hit ordering or full solver. Too costly/incomplete for production.

**Evidence:** [PRODUCT_05_CHECKPOINT.md](source_snapshots/9878de2f0313e4a6aca5587f7f2a4e35cba2de4700fcf457c002815ffda83de3.md), [REPAIR_07_CHECKPOINT.md](source_snapshots/8f10e5f6e185eddfee3b1ae46ec52be25af0ae96b2469c44c971c0bfeb6446d5.md).
<a id="h10"></a>

### H10 — Final-iterate residual recomputation

**Status:** REJECTED AS COMPLETE REPAIR.

**Recorded result:** Repair07 strict bank 1728.125 ns/query, 3 wrong/0 blocked; real stress 15 discrepancies. Exposes real23 false finite hit0.19916695971482617 cm where exact reports no hit.

**Failures and limits:** Bookkeeping fix cannot prove a root; no correctness gain over seed control.

**Evidence:** [REPAIR_07_CHECKPOINT.md](source_snapshots/8f10e5f6e185eddfee3b1ae46ec52be25af0ae96b2469c44c971c0bfeb6446d5.md).
<a id="h11"></a>

### H11 — Process all queued nearer unresolved spans

**Status:** REJECTED FOR PROMOTION.

**Recorded result:** Strict 3266.25 ns/query, 3 wrong/0 blocked; fixes no observed discrepancy; 2.8683x old-fast. Stress 15 discrepancies.

**Failures and limits:** Zero-proxy and solved-prefix completeness still open; negative commit retained.

**Evidence:** [REPAIR_07_CHECKPOINT.md](source_snapshots/8f10e5f6e185eddfee3b1ae46ec52be25af0ae96b2469c44c971c0bfeb6446d5.md).
<a id="h12"></a>

### H12 — Broad crossing conditioning

**Status:** EXPERIMENTAL OVERBLOCKING.

**Recorded result:** Strict 0 wrong /21 BLOCKED.

**Failures and limits:** Blocked-query time absent; survivor means cannot be full-bank speed. Regression tests fail with unresolved exceptions.

**Evidence:** [REPAIR_07_CHECKPOINT.md](source_snapshots/8f10e5f6e185eddfee3b1ae46ec52be25af0ae96b2469c44c971c0bfeb6446d5.md).
<a id="h13"></a>

### H13 — Broad crossing conditioning plus outward center/radius bounds

**Status:** EXPERIMENTAL OVERBLOCKING.

**Recorded result:** Strict 0 wrong /17 BLOCKED, reduced from21 without a new block. Per-operation outward propagation replaced rejected one-nextafter conversion.

**Failures and limits:** Whole-span regularity/frame evaluation/pruning coverage unadmitted; bounds are conditionally sound for ideal regular spline, not production proof.

**Evidence:** [REPAIR_07_CHECKPOINT.md](source_snapshots/8f10e5f6e185eddfee3b1ae46ec52be25af0ae96b2469c44c971c0bfeb6446d5.md).
<a id="h14"></a>

### H14 — Narrow acceptance plus ordering and bounds

**Status:** REJECTED FOR PROMOTION.

**Recorded result:** Strict 4726.25 ns/query, 2 wrong/0 blocked, 4.15x old. a15 distance error improves to about 1.1e-11 cm. Stress 12 wrong plus 3 BLOCKED.

**Failures and limits:** a06 origin and a08 even tangent remain silent wrong no-hits; retained256 admitted replay still2 failures and 128 reference blocks.

**Evidence:** [REPAIR_07_CHECKPOINT.md](source_snapshots/8f10e5f6e185eddfee3b1ae46ec52be25af0ae96b2469c44c971c0bfeb6446d5.md).
<a id="h15"></a>

### H15 — Isolated narrow acceptance repair

**Status:** EXPERIMENTAL; NOT PROMOTED.

**Recorded result:** Strict 2319.375 ns/query, 2 wrong/0 blocked; interleaved confirmation2422.5 ns/query. Old-fast ratio ranges1.89–2.04 across campaigns; a15 improvement retained without ordering/bounds additions.

**Failures and limits:** 2x timing guardrail straddled; correctness independently prevents promotion. Stress 12 wrong plus 3 BLOCKED, not only12 failures. Native new repair NOT_RUN.

**Evidence:** [REPAIR_07_CHECKPOINT.md](source_snapshots/8f10e5f6e185eddfee3b1ae46ec52be25af0ae96b2469c44c971c0bfeb6446d5.md).
<a id="h16"></a>

### H16 — Recovered-seed clipped one-period native transport versus old and exact

**Status:** COMPLETED DIAGNOSTIC; PERIODIC MODEL UNQUALIFIED.

**Recorded result:** RunCompare06: old8387.7 vs recovered8179.8 histories/s (3x8192); exact8.4200 vs recovered7360.5 histories/s on separate3x256 workload. All24 primary attempts exit0. Seed19 64-history replay234 steps has zero discrete sequence changes.

**Failures and limits:** 90-degree vacuum clipping, 16 finite1 cm diagnostic members. Tally threshold exceedances25(debug), 16(256), 4(8192); floating coordinates differ. Strict 3/160, retained2/256, stress 14/160 persist. No periodic qualification or matched Embree/native-torus ratio.

**Evidence:** [RUN_COMPARE_06_CHECKPOINT.md](source_snapshots/d6b5450bccb8ac9bf61b7125135c1a1d26bf7933fcb409f5d9d0d7f718501531.md).

## Blanket and composite variants

<a id="b01"></a>

### B01 — Physical-normal multilayer blanket compiler

**Status:** PARTIAL GEOMETRY; WISTELL ENGINEERING CLEARANCE FAIL.

**Recorded result:** Six layers totaling 135.5 cm, with seven boundaries per model (14 across the exact-torus and WISTELL controls): positive Jacobians, nesting and seam checks reported.

**Failures and limits:** Minimum coil clearance −37.1463 cm FAIL. Earlier blanket-not-implemented report is an earlier milestone; nonuniform coil-constrained/scaling/full physical qualification NOT_RUN.

**Evidence:** [COMPOSITE_BLANKET_INTEROP_FINAL_REPORT.md](source_snapshots/3fcccb773c42d639bdd93786d634f4d5c3bf80a001325be619f2cc51c4f9d61d.md), [BLANKET_FAMILY_REPORT.md](source_snapshots/fdf2a5f948d4882be856948db67597db6ef3f289dcf9e011448b5cd244efa416.md).
<a id="b02"></a>

### B02 — Combined native plasma, blanket and coil model with Boolean cutouts

**Status:** PARTIAL SMOKE / PARTITION.

**Recorded result:** 7 blanket boundaries and 12/48 coils; zero lost particles; native smoke3331.0/2762.19 histories/s, one repetition. TrackA later reproduction3436.33/2440.47 histories/s.

**Failures and limits:** Cutout partition does not remedy engineering clearance; smoke rates not medians. Multithreading/materialized closure/general physical pack qualification NOT_RUN.

**Evidence:** [COMPOSITE_BLANKET_INTEROP_FINAL_REPORT.md](source_snapshots/3fcccb773c42d639bdd93786d634f4d5c3bf80a001325be619f2cc51c4f9d61d.md), [TRACK_A_LEGACY_V2_REPORT.md](source_snapshots/9eb83eb10602c51f28cd83ec18c0a3a4ece32682a4e588bf0f86eefef8850f02.md).
<a id="b03"></a>

### B03 — Native CSG outer fill with fine DAGMC torus hybrid

**Status:** PARTIAL INTEROPERABILITY / HISTORICAL VERIFIED EMBREE.

**Recorded result:** Ordinary DAGMC and genuine DoubleDown hybrid smokes; reported32 interoperability checks. Cached exact swept torus724869 vs690434 histories/s, 1.04987x. Exact periodic 711268 vs696970, 1.02051x with lower bootstrap0.97647 meets3% noninferiority control.

**Failures and limits:** Forced-general swept path0.09951x FAIL. Rigid payload transforms unsupported. C1 ellipse/C3 racetrack/C4 capsule chains and full WISTELL verified-Embree comparison NOT_RUN.

**Evidence:** [COMPOSITE_BLANKET_INTEROP_FINAL_REPORT.md](source_snapshots/3fcccb773c42d639bdd93786d634f4d5c3bf80a001325be619f2cc51c4f9d61d.md), [DOUBLE_DOWN_COMPOSITE_RESULTS.md](source_snapshots/44bd386e782bfb35e5e5e44d0576d54978ac28e363360560909ad0312fb2b1e2.md), [EXACT_TORUS_PARITY_FINAL.md](source_snapshots/0cf2fe88c746a38288ef09dd44785227dc653248981cfcda16846f820f9a7a95.md).

## P00 geometry and event diagnostics

<a id="r01"></a>

### R01 — Exact represented-facet topology and component-AABB certificate

**Status:** CONDITIONAL REPRESENTED-SOLID PREMISE; OWNER COUNTEREXAMPLES.

**Recorded result:** Derived3348 facets/18 selectors: exact nonzero triangles, links, orientation and 25431 pair predicates support embedded bounded components; derived 1944 sampled classifications agree. Mesh-to-mesh displacement bound0.0033287735930590413 cm.

**Failures and limits:** 8 exact cross-component intersection segments in15/16 and 17/18; selectors are priority partition, not disjoint physical-coil owners. No continuous CAD/floating operational theorem.

**Evidence:** [P00_STEP2_CERTIFICATE_20261001.md](source_snapshots/1f04a5645e60e326811136941ff8c4cd4732b738b99b315c5ee188e76f9a9884.md).
<a id="r02"></a>

### R02 — Independent rational facet first-event oracle

**Status:** COUNTEREXAMPLES_FOUND.

**Recorded result:** 810-query authoritative_03: 537 MATCH, 116 EXPECTED_UNRESOLVED, 154 CONSERVATIVE_UNRESOLVED, 3 FAIL. P00 subset 738 has495/93/150/0; cube 72 has42/23/4/3. Exact equal-time contacts expose facet-order-dependent owner/normal.

**Failures and limits:** Do not count154 conservative unresolved as successful resolved queries. _01 self-test failure and _02 two-failure800-query run retained. Exit1 means found counterexamples, not failed execution.

**Evidence:** [P00_STEP3_REPORT_20261001.md](source_snapshots/c015d468ffe21d8081b195f61a24611986f097c069825cee0dbec9b50c6da22a.md).
<a id="r03"></a>

### R03 — Native assembly and positive-gap localization

**Status:** FAILED GENERAL EVENT/SCORING GATE.

**Recorded result:** 680 queries on both libraries: 21 first-event discrepancies/library, 85 continuation aborts/library (74analytic/11derived). Focused planes show successor skips a real2^-48 cm positive gap.

**Failures and limits:** Later M23 accepts only a repaired restricted plane slice; these facet/material/general ownership failures are not automatically closed.

**Evidence:** [P00_ASSEMBLY_REPORT_20261001.md](source_snapshots/74b46871795458cc7cb271ab08edfc8b067a85b9117af6dfaa880341e6328472.md), [P00_ASSEMBLY_PLANES_FOCUSED_RESULT_20261001.md](source_snapshots/a82224df51ea4381b9c655a61f858654a17b5cd9087557a400ced7ef26533693.md).

## Later workload and optimization experiments

<a id="l01"></a>

### L01 — Density ladder with collision workload matching

**Status:** LADDER01 INCONCLUSIVE; LADDER02 GEOMETRY_BOUND.

**Recorded result:** Both32-run phases complete. Quiet ladder02 reports236/236 checker results: thin ratio 1.658(1.605–1.708), dense1.850(1.758–1.913), workload F1.156; nominal4.06x collision difference.

**Failures and limits:** Ladder01 noise/CV/drift gates fail; descriptive times cannot be accepted. Geometry/source workload differ; comparison not physical pack qualification.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md), [ATTEMPTS.jsonl](source_data/29a6388777d391ed80eca4abbcfd0387484033b4560bacce42bfb04cd21b1dda.jsonl), [PLAN.md](source_snapshots/44e49e065e371401030b07bbdfdacff41a85c8cc307222edc53019f38da8a0cc.md).
<a id="l02"></a>

### L02 — Transport stack profiling and plasma workload attribution

**Status:** COMPLETED DIAGNOSTIC.

**Recorded result:** P00 samples: facet distance57%, contains/parity28%, normal10%; nextafter innermost30.9%; physics2–3%. Plasma profile95% distance solver, 55% evaluations tangent scan. Original256 source sites all same point inside custom/outside torus: 68.4027 vs5.4117 collisions/source.

**Failures and limits:** Sample percentages overlap and must not be added. Approx12.6x original collision workload is not geometry speed; original quiet plasma ratio 199.9856.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).
<a id="l03"></a>

### L03 — v1 inline nextafter with std::memcpy bit casts

**Status:** REJECT_EFFECT.

**Recorded result:** Reported1.05x; -fno-builtin emits memcpy@plt calls.

**Failures and limits:** Failed pre-registered effect threshold; preserve failed implementation alongside later repair.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).
<a id="l04"></a>

### L04 — v2 inline nextafter with __builtin_memcpy bit casts

**Status:** REPORTED ACCEPT_SPEEDUP_EVIDENCE.

**Recorded result:** Reported1.65748x; tested seeds/densities bitwise equal in ab02/xval01.

**Failures and limits:** Finite output agreement and internal effect evidence; independent physical/native-event acceptance open.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).
<a id="l05"></a>

### L05 — v3 normal precompute and exact early reject

**Status:** UNDECIDED EFFECT.

**Recorded result:** Reported additional 1.07603x, tested outputs bitwise equal.

**Failures and limits:** Below pre-registered1.10 effect threshold; no acceptance inferred from composition.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).
<a id="l06"></a>

### L06 — P00 gate01 with v2+v3

**Status:** PASS_MEDIAN; ROBUST WORST PAIR FAILS.

**Recorded result:** Three-seed medians1.212/1.211/1.178, pooled1.20060445.

**Failures and limits:** Worst pairings1.27–1.28 exceed1.25. This median pass is distinct from later robust pass.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md), [GATE.json](source_data/ad65b2eb61c2644d7cb0fe83399add7d70531efeb1456fbe6bc8a05b7b0b70c3.json).
<a id="l07"></a>

### L07 — v4 opt-in plasma collision-distance ceiling

**Status:** REPORTED ACCEPT_SPEEDUP_EVIDENCE.

**Recorded result:** Reported8.07x(7.86–8.51); 12 gate runs bitwise equal; original unequal-source custom/torus195.935→23.833.

**Failures and limits:** No independent root/exclusion certificate acceptance. Unequal point-source workload; more matched diagnostic still over1.25.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md), [SUMMARY.json](source_data/2f38005c7a3dd56b9cd7076048d276f1117aea473d42af1d1e63d34c90b9ef05.json).
<a id="l08"></a>

### L08 — v5 facet distance ceiling

**Status:** FINITE BITWISE CONTROLS PASS.

**Recorded result:** v5+v6 composition retains equality across 12 gate and 5 cross-validation runs.

**Failures and limits:** No isolated individual v5 speed effect established; native event/physical owner caveats remain.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).
<a id="l09"></a>

### L09 — v6 exact periodic-spline indexing

**Status:** FINITE BITWISE CONTROLS PASS.

**Recorded result:** v5+v6 composition retains equality across 12 gate and 5 cross-validation runs.

**Failures and limits:** No isolated individual v6 speed effect established; equality only for tested records.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).
<a id="l10"></a>

### L10 — P00 gate02 with v2–v6 and ceiling

**Status:** INVALID OVERALL.

**Recorded result:** Seeds1742/1743 PASS_ROBUST; pooled1.108598 descriptive.

**Failures and limits:** Seed1741 first-run outlier/CV6.8% invalidates overall timing decision. Later warmup replication is a separate attempt.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md), [GATE.json](source_data/aaec8dcb1dfda63ba571d583effdbb38139394520c79f413816334b316208a25.json).
<a id="l11"></a>

### L11 — P00 gate03 warmup-discarded replication

**Status:** REPORTED PASS_ROBUST TIMING ONLY.

**Recorded result:** All3 seeds PASS_ROBUST; pooled1.104614615471397; medians1.126/1.117/1.071, worst1.138/1.122/1.087.

**Failures and limits:** Derived P00 versus fixed30x30 cm rings, all tested tally bits unchanged. Continuous CAD/section/frame fidelity, physical ownership, event semantics and independent Sol physical acceptance remain open.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md), [GATE.json](source_data/c88e910a8056d1042fd01fb6a3d9ceb65911fa5fdc40669ed65788c7aa9daea8.json), [GATE_PLAN.md](source_snapshots/02a27cfb8eaf304901246a5008de79d6361a78853a4de0506e98e075c620bf46.md).
<a id="l12"></a>

### L12 — v7 exact value-only plasma evaluation

**Status:** UNDECIDED; NO MEASURABLE EFFECT.

**Recorded result:** Reported1.004x, finite bitwise equality.

**Failures and limits:** Distinct from rejected M22 normal/sense shortcut; no speed acceptance.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).
<a id="l13"></a>

### L13 — v8 voxel clearance fast path

**Status:** UNDECIDED EFFECT.

**Recorded result:** Reported1.139x with band1.092–1.216; tested outputs bitwise equal; initialization+0.39 s.

**Failures and limits:** Band crosses1.10 effect threshold. No independent clearance/root oracle acceptance.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).
<a id="l14"></a>

### L14 — Plasma geometry-specific uniform-source diagnostics

**Status:** IMPROVED; NATIVE 1.25 TARGET STILL MISSED.

**Recorded result:** 51.619 vs60.589 collisions/source: control custom/torus15.8100→v2–v7 2.100163043577142; v2–v8 2.1197992495895623.

**Failures and limits:** Source banks and solids differ; closer collision workload is not identical physical geometry. Do not overwrite older proxy failure or compare unrelated absolute times.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md), [SUMMARY.json](source_data/eae402c34a19a286af6f5d1cecdee9986ee0d967e148ae26a53c066cbaff610c.json), [SUMMARY.json](source_data/979d45a5f1fc68268d17d1c5d2e080acd903b4b260488a64f4487009a80a56c0.json).
<a id="l15"></a>

### L15 — Plasma ceiling counters and matched profile

**Status:** REPORTED DIAGNOSTIC; ORACLE VALIDATION OPEN.

**Recorded result:** Implementation records92–95% ceiling_certified distance calls; full solver4.4 calls/history≈45% time.

**Failures and limits:** Counter label is implementation classification, not independent mathematical certification; allocation/profiling coverage does not prove all queries.

**Evidence:** [RESULTS.md](source_snapshots/01066c6c7ace075e14b50fa7b4e5cb36e13e01bb115d22a38f7b70cf9324b438.md).

## Query composition reference

<a id="q01"></a>

### Q01 — Exact candidate hierarchy, closed ceiling, query reuse and root scheduling composition

**Status:** ACCEPTED_REFERENCE_COMPOSITION_ONLY.

**Recorded result:** 20 supplied controls and 120 plane queries pass; 12-arm hierarchy/ceiling/reuse ablation replay matches. Independent reviewer 200 geometries/2400 exact multi-root resolutions plus malformed/alias/cache challenges pass.

**Failures and limits:** Caller must certify real-geometry AABBs and callback earliest-root completeness. No native OpenMC solver, physical acceptance or timed speedup. Earlier/equal unresolved preserves UNRESOLVED; provisional contacts not certified owners.

**Evidence:** [README.md](source_snapshots/d627172eace19e4cc215b4da0ee8e15f118ab69b5ecc89e9c869c02397ac6930.md), [results.json](source_data/f90bec30e0b30826469275958620c8cf3e096eabe8f8b80d571ff266b11b4c9c.json), [independent_review.json](source_data/dced0394c8d034bf75027f7c879cbda59fb52a9d73afee1f7630230247df0957.json).
<a id="q02"></a>

### Q02 — Exact rational quartic Sturm root isolation with conservative scalar scheduler

**Status:** ACCEPT_SCOPED_REFERENCE.

**Recorded result:** New degree-at-most-four oracle: 10 supplied controls, 386 independent known-factor cases, 1454 one-sided counts, three irrational cases and 20 scheduler compositions. Separate retained 59-control replay receipt passes and reproduces all three Fourier negative cases; reviewer audited that receipt without rerunning the complete replay.

**Failures and limits:** COMPLETE means distinct roots of supplied exact represented coefficients on a finite closed interval, not physical HIT. Budget exhaustion/all-zero polynomial remain UNRESOLVED; nonpoint intervals do not become scalar HIT. Coefficient uncertainty, actual-surface equivalence, trims, owner identity, native throughput and real VMEC remain unaccepted.

**Evidence:** [README.md](source_snapshots/d683ec08b167bdac4f18a09ceb4ad237e375b0faa7f817e0f771e6b398ff7bda.md), [replay_results.json](source_data/4c9e3ae6d638b56298c8294a79848aa9dba3821e30371b45093f52980d909f59.json), [independent_review.json](source_data/1083a1e49b803113491d8c133a67e4829b8211a12164b9bee4449797c1667942.json).

## Fourier, toroidal patch and hybrid trials

<a id="ft-001"></a>

### FT-001 — Fourier displacements added to a reference torus

**Status:** SYNTHETIC RECONSTRUCTION PASS.

**Recorded result:** Exact one-harmonic reconstruction control.

**Failures and limits:** General intersection remains coupled; no production solver.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/0fcfc09cb820f4ad001b4428a76b46e1d1a2ba5c76505c831080c935fc013919.json).
<a id="ft-002"></a>

### FT-002 — Global torus fit, coefficient bounds and quartic candidates

**Status:** SCOPED CONTROLS PASS; GENERAL QUERIES UNRESOLVED.

**Recorded result:** Attempt0001 10 controls; endpoint-sign counterexample(t−.1)(t−.2)(t−.8) preserved and corrected by external single-root contract.

**Failures and limits:** Requires external exclusion/single-root certificates; candidate is not HIT; no general Fourier certificate generator.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/0fcfc09cb820f4ad001b4428a76b46e1d1a2ba5c76505c831080c935fc013919.json).
<a id="ft-001-b"></a>

### FT-001-B — Boolean combinations of complete coaxial torus solids

**Status:** RESTRICTED FAMILY COUNTEREXAMPLE; NOT_EXECUTED.

**Recorded result:** Rotational symmetry prevents representing the proposed nonaxisymmetric target in this restricted family.

**Failures and limits:** No new Boolean compiler executed; displaced/trimmed constructions are different.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/0fcfc09cb820f4ad001b4428a76b46e1d1a2ba5c76505c831080c935fc013919.json).
<a id="ft-001-c"></a>

### FT-001-C — Nonlinear coordinate map to a reference torus

**Status:** PROPOSAL NOT_IMPLEMENTED.

**Recorded result:** Interpretation documented.

**Failures and limits:** Transformed rays curved; lengths, normals and complete intersection unresolved.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/0fcfc09cb820f4ad001b4428a76b46e1d1a2ba5c76505c831080c935fc013919.json).
<a id="ft-003"></a>

### FT-003 — Fourier-guided osculating torus patch atlas

**Status:** APPROXIMATION; NO CLOSED SOLID.

**Recorded result:** Sampled distance to the full fitted torus 8.927→1.185 mm and sampled projected-neighbor gap 14.326→1.932 mm with refinement; local admitted curvatures matched.

**Failures and limits:** This is not positional correspondence error or distance to the admitted trim. Projected patches have gaps; no trim-coverage certificate or closed solid/event qualification.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/0b9a8543fc3058f82c3a588f221ef9031ba9653a55737811e85bd40c5898742b.json), [independent_review.json](source_data/f095db3affa2a6f2b7955271e45964c0c78eb51f9af0b3d72504d7a12b5b3762.json).
<a id="ft-004"></a>

### FT-004 — Constant-weight torus polynomial sums compiled to quartic

**Status:** COMPILATION PASS; LIMITED FIT.

**Recorded result:** Degree remains4; circular-torus coefficient family rank saturates14; tested global candidates radial errors 125.96/159.68 mm.

**Failures and limits:** Finite-dimensional family cannot supply progressively complete Fourier basis; not physical admission.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/0b9a8543fc3058f82c3a588f221ef9031ba9653a55737811e85bd40c5898742b.json), [independent_review.json](source_data/f095db3affa2a6f2b7955271e45964c0c78eb51f9af0b3d72504d7a12b5b3762.json).
<a id="ft-005"></a>

### FT-005 — Torus plateaus plus localized cubic-Hermite joins in one hierarchy

**Status:** C1 SYNTHETIC CONSTRUCTION; QUERIES UNRESOLVED.

**Recorded result:** N48 errors 21.109/16.808/10.970 mm for strip fractions.1/.3/.6.

**Failures and limits:** Torus interiors inaccurate; narrow strips concentrate normal error. Candidate workload differs from hit frequency.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/0b9a8543fc3058f82c3a588f221ef9031ba9653a55737811e85bd40c5898742b.json), [independent_review.json](source_data/f095db3affa2a6f2b7955271e45964c0c78eb51f9af0b3d72504d7a12b5b3762.json).
<a id="ft-006"></a>

### FT-006 — All-spline synthetic periodic-radius comparator

**Status:** SAMPLED ACCURACY IMPROVES; QUERIES UNRESOLVED.

**Recorded result:** N48 sampled error0.007575 mm on attempt0002 target; all 624 general query rows across attempt0002 methods UNRESOLVED.

**Failures and limits:** New comparator, not incumbent. Exact tangent missed by sampled search; negative evidence retained.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/0b9a8543fc3058f82c3a588f221ef9031ba9653a55737811e85bd40c5898742b.json), [independent_review.json](source_data/f095db3affa2a6f2b7955271e45964c0c78eb51f9af0b3d72504d7a12b5b3762.json).
<a id="ft-007"></a>

### FT-007 — Direct radial Fourier versus frozen incumbent bicubic evaluator

**Status:** SCOPED SYNTHETIC DIAGNOSTIC; QUERIES UNRESOLVED.

**Recorded result:** Attempt0003 run00229 controls; 76-ray median Python cost direct.2629 s vs bicubic.8587–.8831 s≈3.3x. Known24 candidates retained; direct maxerror8.88e−16 m vs spline3.276/.1128/.006464 mm. Same-parameter4745-point spline errors 3.466/.1452/.008117 mm.

**Failures and limits:** All304 general query rows UNRESOLVED. Synthetic physical n[0, 3,−6], geometric theta not raw VMEC theta. m2048 crossing missed despite78 candidates; tube-axis evaluation singularity preserved; no native speed claim.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/3d819278f22c27a29ba3514057fdb8e2c476d1f85d0e213ac58d3fff3c949e0d.json), [independent_review.json](source_data/3adc6ac3c55b4a607cd628b9f9bbe84237a2624e270dbd5abe2a96e827dfb049.json).
<a id="ft-008"></a>

### FT-008 — Full35-coefficient local algebraic quartic fits

**Status:** APPROXIMATE ATLAS; NO CLOSED SOLID.

**Recorded result:** 96/384 patch holdout normal-line errors.3056/.01187 mm; midpoint seams.2045/.01271 mm; rank35, condition4.49e5/2.54e6.

**Failures and limits:** Periodic seams unassessed; angular trim admits extra quartic sheet(t.730003, target field.7842 m). No complete root/owner certificate.

**Evidence:** [METHOD_LEDGER.md](source_snapshots/2f07f1bd278119e591f4dcdc5a5a93748966f8077e3598766928fd7eb1ecd66a.md), [receipt.json](source_data/3d819278f22c27a29ba3514057fdb8e2c476d1f85d0e213ac58d3fff3c949e0d.json), [independent_review.json](source_data/3adc6ac3c55b4a607cd628b9f9bbe84237a2624e270dbd5abe2a96e827dfb049.json).
