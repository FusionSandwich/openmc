# StellarCSG: review of repository chats, implementation, and next experiments

**Review date:** 2026-09-26. **Evidence cutoff:** 21:44 UTC. A subsequent local-session status observation at 21:51 UTC is explicitly identified below.

**Read this page first.** It updates the earlier [state diagnosis](STATE_DIAGNOSIS_20260926.md) and [handoff](PRO_HANDOFF_20260925.md). Those documents retain useful negative evidence, but their statement that no nontrivial native crossing has been admitted is superseded **for the new, explicitly restricted offset representation**.

## 1. The short version

We have made a real correctness advance. Draft [PR #5](https://github.com/FusionSandwich/openmc/pull/5) implements an explicit exact-control offset representation, admits a shaped periodic-seam crossing through OpenMC, and has independent scalar certificates for all 160 frozen queries. Its Bernstein accelerator reduces summed distance time by **4.05 times** compared with the same final binary with acceleration disabled.

We have **not** demonstrated nearly built-in CSG speed for general stellarator plasma or physical winding packs. The 4.05-times result is an internal accelerator comparison. The physically intended rectangular pack, imported-coil hit/normal coverage, matched native throughput, complete transport semantics, source clearance, and upstream integration still need work.

The local Astra session finished its first milestone and is actively addressing your later request for plasma/coil proxies, spectra, damage-energy scoring, and native speed comparisons. Its latest startup controls and new adversarial tests are encouraging. The expanded assignment is incomplete at this review cutoff.

The mathematics Pro chat completed a useful review. Its two strongest proposals are:

1. Compile and intersect the physical rectangular pack's **ruled CAD faces** directly.
2. For the restricted offset model, prove **global normal ownership during compilation**, so every query need not repeat the global proof.

Both have concrete deciding experiments. Neither has a demonstrated production speed result.

**Recommendation:** finish the existing matched proxy study, then run one bounded ruled-face pilot and one bounded ownership-certificate pilot. Obtain the actual accepted rectangular CAD in parallel. These experiments will tell us more than another broad solver rewrite or a large reactor run.

## 2. What was reviewed, and how strong the review is

The dispatch records identify **13 repository conversations**: six older Work conversations, four older ordinary Pro chats, and three newer ordinary Pro chats. They also identify two briefs that were prepared but **never submitted**. The local Astra Codex session is a separate implementation attempt.

I inspected prompts, available final messages, the local session's later user prompt and work records, published reports, and selected receipts. Ten conversation records were freshly available through the app, including nine with final responses; three older Work reviews were read from saved follow-up responses. The newer computer-science Pro attempt has no verifiable final response available to this review. Its browser page could not load; its app record exposes the submitted prompt, not a completed result.

The mathematics final response is available through the app, but its final tail is truncated and the browser could not load the conversation. Its advertised research ZIP, full report, and executable prototype were **not retrieved or rerun** here. Its “52 checks passed” is therefore a reported prototype result. The central reach theorem and real-root-isolation reference were checked separately against primary sources.

This review freshly rehashed **22 PR #5 evidence artifacts**; all match the published acceptance record. It also reconciled the frozen CSV identities below. An independent Sol reviewer separately checked the report against the decisive receipts, reproduced the 22 matching hashes, and confirmed the scalar counts and internal timing ratios. That is a consistency review, not a new proof execution. This review did not rebuild OpenMC, rerun the 160-query verifier, execute transport, SSH, submit jobs, change schedules, or message/interrupt the other sessions. The active implementation checkout was preserved.

Private conversation URLs and prompt records are retained in a companion local ledger outside Git. Public scientific evidence and PR links are provided here.

## 3. Conversation-by-conversation accounting

“Reported” below means the conversation's result, unless a separate retained local receipt is named.

### Earlier six Work conversations

These were originally Work conversations; their requested Pro identity was not verified. They should not be counted as six completed ordinary Pro experiments.

| Current conversation title | What worked or was learned | What failed or remains unproved | Disposition |
| --- | --- | --- | --- |
| **Optimize Fast Kernel** | Compiled the recovered fast solver; reproduced four strict failures; explored seed, residual and origin controls. | Seed/acceptance variants still had wrong roots and were slower. Execution disconnected before final three-state repair; exact final artifacts were not published. Its interpretation of tiny a06 as zero is superseded by the new exact positive-contact certificate. | Negative evidence; no qualified solver. |
| **Bernstein Coil Solver Progress** | Constructed circular-tube degree-ten elimination and Bernstein exclusion/isolation machinery. | Apparent strict zero-wrong result depended on 12 sampled fallbacks. Stress bank had **32 wrong / 160**, with fallback on every ray. About 90% of strict cost was fallback; reported candidate cost was about 253 times old. Final fail-closed change was not applied before disconnection. | Reject the sampled fallback; retain the algebraic mechanism as research. |
| **Implemented Candidate B Validation** | Built an opt-in torus-arc fitting and quartic candidate prototype. | **160/160 blocked** in both strict and stress banks. Provisional disagreements remained. Chain was C0, not the intended G1 construction; tangent mismatch reached 0.002010197 rad. Continuous fidelity and complete root/ownership proof absent. | Explicit approximation research, not a correct admitted kernel. |
| **Implemented Bezier Atlas** | Cartesian plasma atlas and interval/Newton machinery; classification uses its own atlas. | Review showed inclusion returned only Boolean, discarding its parameter enclosure. Point-estimated ray distance then controlled pruning; residual tolerance does not bound longitudinal error near grazing. Exact final patch became unavailable. Sampled synthetic torus error was not a Hausdorff or WISTELL bound. | Reopen only with certified ray-distance intervals and seam/topology handling. |
| **Reject Candidate D Solver** | Useful candidate-generation cost and hierarchy diagnostics; negative artifacts were retained/recovered. | All strict/stress queries unresolved. Near-parallel false exclusion, clipped leads, radius enclosures, heuristic padding and branch deduplication remain unsafe. Candidate-only timing is not distance-solver timing. | Rejected as an authoritative solver. |
| **Implemented Period Import Repair** | NFP=4 import, exact quarter-turn derived images, stable finite neighboring members and provenance distinctions. | Uses a 1 cm circular diagnostic envelope; physical pack clearance remains null. Held-out ParaStell comparison **2.39627%** was rejected. Canonicalization changes derived geometry; it is not byte-identical raw-source geometry. | Useful import/provenance work, narrow geometric qualification. |

The saved follow-up reviews explicitly corrected earlier overstated performance interpretations. Several original cloud workspaces disappeared or disconnected. A remembered local commit or checksum does not make its implementation recoverable; request an actual patch before reuse.

### Older four ordinary Pro chats

| Current conversation title | Result | Practical interpretation |
| --- | --- | --- |
| **Develop Neutron Source Model** | Reported 61 passing tests; separated normalized birth PDF from neutron rate; shutdown has rate zero and no sampling bank. Prescribed source model and portable prototype recovered. Independent held-out phases overpredicted neutron rate by **347.018% and 220.553%**, with 60% ion-temperature profile error. | Useful source interfaces and retained failure. Sparse hot/vacuum snapshots do not establish a physical startup/shutdown history. Source-generation timings are not transport timings. |
| **Audit repository brief** | Found prefix/pruning loopholes, missed even contacts and narrow crossing pairs, and a binary64 underflow/frame-bound counterexample. Audit remained NOT QUALIFIED. | Valuable adversarial evidence. It diagnosed unsafe assumptions; it did not supply a production completeness proof. |
| **Implement Portable Runner Validator** | Reported **76/76** mock/validator checks; reproduced a child exit 7 being normalized to wrapper success and silently discarded duplicate lanes. Added portable, hash-bound failure propagation. | Good measurement infrastructure. Mock success does not qualify kernel performance or physics. |
| **Repository Access Brief** | Adapter/serialization repairs improved controlled C++ checks from **33/47 to 40/47** and Python isolation from **15/20 to 18/20**; 16 exact synthetic ownership checks passed. | Remaining failures include unresolved propagation, overlapping-union boundaries, identity ties, hidden NaN member results, and collection serialization. Controlled backends were not real spline transport. |

The [local continuation log](LOCAL_CONTINUATION_20260925.md) records which recovered changes were integrated and subsequently tested. The older mock result counts should not be presented as current native OpenMC acceptance.

### Newer three ordinary Pro chats

| Current conversation title | Result and current availability | Assessment |
| --- | --- | --- |
| **BVH Audit Proposal** | Draft [PR #4](https://github.com/FusionSandwich/openmc/pull/4), commit 11f8941057ab1500c6e1fd69f59dce39fde8b510. Adds read-only span indices, a real compiled-BVH dumper, and topology/box/provenance audit. Reported synthetic valid/corrupt-box tests pass. **C++ build, actual 640-span dump, and real provenance audit NOT_RUN.** | Useful narrow diagnostic proposal; not integrated or accepted. Topology alone cannot establish safe traversal or nearest surface roots. |
| **Inspect Repository Code** | Same computer-science brief as local Astra. UI dispatch recorded Latest at highest available effort; Astra identity unverified, as authorized. Earlier progress concerned repository access and seam/root isolation. Current browser unavailable; app has no final artifact. | Outcome unknown. There is no basis to compare its completed performance with local Astra or call it a failed mathematical attempt. Recover its result before deciding whether to restart. |
| **Mathematical methods review** | Completed final recommending ruled-face compilation, offline reach/ownership certification, and conservative approximation sandwiches. Reports **52 exact/symbolic toy checks** and repeat-identical results. No native build, frozen-bank rerun, real-coil qualification or transport. Full downloadable bundle unavailable to this review. | Constructive research direction with explicit counterexamples; needs artifact recovery and independent reproduction. Its older 236 ms hit-median snapshot is superseded by PR #5's final accelerator results. |

The prepared **frozen-oracle** and **source-binding** Pro briefs were never sent. Local PR #5 later repaired the comparator it uses. The separately reproduced swapped source/mesh sampling-key false pass remains an open source-contract task.

## 4. Did local Codex do what was requested?

Session title: **Solve StellarCSG certified intersections…**. The recorded dispatch used local GPT-6 Astra with Ultra effort. Its immutable starting point was checkpoint commit 63359cb83d36b419a7e9ba60c45f867073703c21.

### Original brief versus achieved result

The brief asked for an executable admitted geometry class, consistent distance/classification/normal semantics, complete earlier-root exclusion, explicit unresolved behavior, OpenMC integration, independent acceptance, and a plausible route to near-native speed. Its first milestone was a nontrivial native shaped seam crossing followed by the unchanged 160-ray bank.

| Requested outcome | Observed result | Acceptance |
| --- | --- | --- |
| Correct nontrivial native seam crossing | Actual SurfaceSweptSpline and Region entry distance **16.000000000001382 cm**; the subsequent exit distance from the coincident entry is **27.999999999997744 cm**, with directional sense and normal controls. Exact rational distance errors bounded below 2e-12 cm. | First milestone achieved for the explicit representation. |
| Frozen 160-ray scalar bank | Both accelerator modes have **69 hits, 91 no-hits, zero unresolved/wrong scalar results**, independently certified at 1e-11 cm. | Achieved for the represented scalar queries; finite-bank evidence, not universal certification. |
| Consistent geometry contract | Explicit exact_control_offset mode in C++, Python, XML/HDF5; legacy remains default. Constant circular offset or constant planar ellipse subset. | Constructive restricted formulation. No claimed equivalence to legacy varying-frame geometry. |
| Full normals and imported-coil hits | Nine blocked normal queries and missing normal timings remain: a00 and w0–w7. Distance and evaluate timings are complete. All eight imported-coil scalar rows are misses. | Incomplete; imported crossing usability not established. |
| Accelerator correctness | Complete prefix exclusion and sign/derivative/projection gates before accepting a numerical proposal; bounded fallback; on/off scalar results independently checked. Tiny a06 root remains positive. | Strong subset evidence. General tracking and adversarial family coverage remain open. |
| Near-native speed | Three clean on/off process pairs show 4.05-times lower summed distance time. No completed matched native transport study at cutoff. | Optimization progress, target unproved. |
| Physical stellarator/magnet geometry | No authoritative accepted rectangular CAD equivalence, complete source clearance, or reactor run. | Open. |
| Reviewable GitHub result | Draft PR #5 at **0098a5e9577a23c48bb2b00d7f4f2f5ea6437817**, including evidence and continuation notes. | Delivered. Not merge-ready upstream qualification. |

This session delivered the executable first milestone. It has not completed the larger physical/performance objective.

See the immutable [PR #5 result report](https://github.com/FusionSandwich/openmc/blob/0098a5e9577a23c48bb2b00d7f4f2f5ea6437817/dev/stellarcsg/reports/astra-20260926/RESULTS.md), [acceptance receipt](https://github.com/FusionSandwich/openmc/blob/0098a5e9577a23c48bb2b00d7f4f2f5ea6437817/dev/stellarcsg/reports/astra-20260926/final-acceptance.json), and [continuation handoff](https://github.com/FusionSandwich/openmc/blob/0098a5e9577a23c48bb2b00d7f4f2f5ea6437817/dev/stellarcsg/reports/astra-20260926/CONTINUATION_HANDOFF.md).

### Your later prompt and its current work

Your subsequent prompt asked whether this works for both plasma and magnets, demanded accelerator correctness controls, requested same-size/same-material native torus and coil proxies, and asked for spectra, DPA, tallies, hidden issues, and an upstream-quality burden.

The session correctly expanded the scope. It has:

- Distinguished an **exact constant-coefficient plasma torus specialization** from a cubic near-circle coil offset and from general stellarator plasma.
- Added an equal-volume annulus using cylinders/planes as an additional coil shape/cost control.
- Found and repaired an “almost constant” coefficient recognition bug that could incorrectly label geometry exact.
- Found a valid crossing too close to box entry to establish the initial sign; preserved unresolved, then repaired the starting interval. New exact-root and thin-crossing controls now pass.
- Added an acceptance plan before paired runs, including spectra, integral and cell/material closure, paired statistics and sparse-bin rejection.
- Built fixture/harness work using existing local Fe56 data with MT444 damage-energy support.
- Completed a **20-history native plasma pilot** and a **4-history spline-coil pilot**, with successful exits, finite retained tallies and reported closure. The later plasma-spline startup also completed according to its command record.
- Added comparison-parser negative controls; seven tests pass.

These are startup/regression observations. The pilot counts are insufficient for spectral equivalence or stable throughput; they use different history counts and are excluded from timing acceptance. The planned paired runs remain in progress. The active checkout has uncommitted source/harness changes, so the published PR #5 certificates bind the published snapshot, not every subsequent edit.

Its NRT conversion uses **40 eV as a test convention**, per source particle. The coil uses a declared native reference atom count until actual spline volume is qualified. This is a reference-normalized damage index, not certified physical coil DPA, DPA/s, or DPA/year.

**Assessment:** the session is on track with the later request. Let it finish the bounded paired study and inspect its final receipts before changing direction.

**21:51 UTC status update:** the local session reports that both coil modes completed startup histories and that the planned **18-run paired comparison is running sequentially**. It also reports an independent radial-deviation bound of about 0.24 micrometres for the near-circle coil versus its torus proxy. That newer geometric bound was not independently audited in this synthesis; even an accepted positional bound would not by itself establish tangent hit equivalence or physical winding-pack fidelity. No final paired throughput or spectral acceptance is available at this observation.

### Related Codex owners and dependencies

I also read compact prompt/result records from **Continue stellarator neutronics UQ** and **Complete ASC 2026 WISTELL-D recovery** to identify dependencies. These are adjacent projects, not additional completed StellarCSG kernel attempts; this report does not audit all of their separate research chats or schedules.

The UQ session's scope is vanilla ParaStell/OpenMC plasma-state uncertainty with fixed hardware and clearance. Its latest available owner result at **20:14 UTC** reports two CAD services still active, no OOM evidence, and stagnant CPU time/possible stalling of one worker at its task cap. This is historical owner evidence, not a fresh remote observation. It does not supply an accepted new CAD reference or show that extra cores improved the build. Recover/review its eventual terminal artifact through that owner before relying on it for physical input.

The ASC recovery session's broader publication/secondary-radiation objective remains incomplete. Its recent records describe diagnostic navigation repair and recovery work, and an unresolved version decision for native production/reaction filters. Those products are not current general StellarCSG geometry qualification or authorization to change the runtime here.

## 5. What the previous tests establish

### Results worth keeping

- **Bounds:** the recorded rational audit passed 552,960 inequalities over 640 analytic spans and matched 3,840 compiled box endpoints. It establishes stored-power centerline bounds under recorded arithmetic assumptions, not all frame, BVH, root or general CAD correctness.
- **Facet controls:** accepted P00 facets have eight exact transverse component intersections. Common magnet material 7 permits a useful union control. Recorded 360 sampled material entries pass; union/priority occupancy agrees on 262,144 resolved sign assignments. This does not establish distinct per-coil tally ownership or continuous CAD.
- **Source interface:** a fresh earlier local rerun passed 9/9 synthetic checks. Real source/wall clearance remains unadmitted; a swapped sampling-key negative fixture still falsely passes.
- **Exact offset bank:** PR #5 supplies independently checked scalar roots/misses, including tiny positive even contacts, complete eligible prefixes and native entry/exit smoke.
- **Harnesses:** negative controls prevent accepting nonfinite comparator results and preserve child failures. They make later evidence more credible.

### Claims that cannot carry current acceptance

The August [performance report](PERFORMANCE_REDESIGN_FINAL_REPORT.md) records useful raw observations, including a complete 48-coil shared-BVH result **5.889 times faster than fine DAGMC** and a spline torus at **0.4537 times native torus throughput**. Those experiments used older geometry/contracts and weaker completeness checks. Later strict wrong-root evidence prevents treating the old swept timings as a qualified correct-kernel result. Historical plasma observations also need their own current accuracy/closure checks.

Likewise, zero observed lost particles, randomized agreement, a small residual, a sampled geometric error, and a green kernel-disabled CI job do not establish complete nearest-root or physical fidelity.

The last inspected PR #3 CI result had 11 upstream build/test lanes green with the experimental C++ kernel **OFF**, and 57 formatting failures. No completed experimental qualification/check suite was available for PR #4 or PR #5. Upstream inclusion needs an enabled-kernel CI lane plus the ordinary regression gates.

### PR #5's timing, stated accurately

| Recorded mean over three clean pairs | Accelerator on | Same final binary, accelerator off |
| --- | ---: | ---: |
| Sum of 160 distance-query times | 0.865648 s | 3.507429 s |
| Child process wall time | 1.547897 s | 4.032762 s |

This gives **4.05-times lower distance time** and **2.61-times lower process wall time**. Nine blocked normal queries/missing normal timings persist; distance and evaluate timings are complete. Runs overlapping the independent Fraction verifier were excluded and retained.

Representative hit medians are approximately **8.4–8.7 ms** with acceleration, while most misses are microseconds. Expensive hit costs remain a concrete motivation for changing the query architecture. These values are not comparable with the unlike-bank historical 175 ns ZTorus sentinel.

The target remains matched throughput at least **80% of native CSG**: for identical work, candidate time at most 1.25 times native time. A 1 microsecond query target, speedup over an incorrect old solver, or speedup over mesh is a separate measurement.

### Frozen-bank identity reconciliation

The mathematical review correctly flagged differing hashes. This review established:

- Checkpoint working-file SHA-256: 7348483e39128259a844d22a7618869a3f111604ea48d01e196a87fe0d396af7.
- PR #5 working-file SHA-256: fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723.
- Both normalized from CRLF to LF: **db42cf99fe566cb81b033c98465139194f3c3cfc5ec94b45a985b8da0a93c0ba**.
- Both committed Git blobs: **362e02f6c4fe2e8b03638ad916e4d91c898b55ad**.
- All 160 ordered records and all CSV field strings compare equal.

Thus the difference is line-ending representation, not changed ray records. Keep both raw hashes and the explicitly defined normalization; never claim byte identity across the two raw files.

## 6. Where we are actually stuck

There are four separate barriers.

**Representation and physical input.** Correct WISTELL-D MAKEGRID filaments do not uniquely specify a winding-pack section, frame, CAD revision or trim topology. The diagnostic 10 × 8 cm ellipse differs materially from the nominal 30 × 30 cm rectangular P00 pack. Recovering accepted CAD is necessary even if every diagnostic query is correct.

**General completeness and solid semantics.** The legacy solver cannot certify all earlier roots; its latest saved strict result remains 73 unresolved / 87 no-hit. The new offset formulation resolves the bank, but imported normals/hits, tangencies during tracking, seams, unions and ownership need broader admission. Plasma is a separate surface family.

**Cost of repeated proof.** The new offset path repeatedly handles global nearest-center/ownership obligations. Certified local acceleration helps substantially, but expensive hits remain. This is an architectural target: move global geometric facts into compilation or use the actual boundary faces.

**Transport and evidence.** Matched native speed, spectra and tallies are still being measured. Physical source/wall and material/tally ownership gates remain independent. Some source evidence tooling still admits malformed bindings.

There is no demonstrated impossibility theorem preventing fast stellarator CSG. Existing mathematics covers several central pieces. We need specialized admission, complete event handling and conservative numerical implementation; a broad new theorem is not a prerequisite for the next experiment.

## 7. The mathematical routes worth trying

### A. Direct ruled-face compilation for rectangular packs

For a verified ruled face,

\[
S(u,v)=E_0(u)+v(E_1(u)-E_0(u)).
\]

Coplanarity with ray \(O+td\) gives

\[
(E_0(u)-O)\cdot((E_1(u)-E_0(u))\times d)=0.
\]

For polynomial cubic edges this has degree at most six. For rational cubic edges \(E_i=A_i/w_i\), with positive denominators, a scaled equation is

\[
d\cdot(A_0\times A_1)+(O\times d)\cdot(w_0A_1-w_1A_0)=0.
\]

Geometry coefficient combinations can be precomputed. Recover \(v,t\), enforce domains/trims, and order complete events by **ray distance**, not edge parameter.

This algebra avoids nearest-centerline ownership during face intersection. It needs explicit parallel/coincident/identically-zero branches, repeated roots, shared edges, orientation and closed-solid material transitions. The Pro prototype reportedly constructs one regular patch with **six valid crossings**: one face cannot be assumed to have one root.

**First experiment:** recover one accepted rectangular coil's actual edge correspondence and polynomial/rational pieces without refitting; make a complete exact event ledger for ordinary, inside-origin, tangent, shared-edge, seam and six-root controls. If the accepted CAD is not ruled in this representation, label any fit approximate and impose an independent fidelity gate.

**Go/no-go:** complete owned-event agreement with the exact checker, conservative failure on unsupported cases, and a profile showing affordable ordinary intersections. Do not begin a full-device exporter first.

[Sagraloff–Mehlhorn](https://arxiv.org/abs/1308.4088) provides complete real-root isolation for square-free real polynomials with coefficient oracles. Repeated-root factorization/multiplicity, exact coefficient formation and geometry branch checks remain our responsibility.

### B. Offline reach/normal-ownership admission for the offset model

Reach bounds the neighborhood in which a curve has a unique nearest point; it depends on curvature and remote proximity. [Aamari et al., Theorem 2.2](https://arxiv.org/pdf/1705.04565) gives the tangent-ball characterization used here.

For regular closed embedded \(C\), tangent \(V=C'(u)\), displacement \(\Delta=C(v)-C(u)\), prove for **all distinct point pairs**

\[
|\Delta|^2\ge 2\rho|\Pi_{N_u}\Delta|.
\]

Then a normal offset of radius \(r<\rho\) has its chosen center as unique global nearest center. In the constant metric used by the new representation, transform the curve and certify \(\rho>1\) for its unit offset.

The proposed constructive improvement removes the fourth-order diagonal zero before interval/Bernstein checking:

\[
G_\rho=|\Delta|^4|V|^2-4\rho^2|\Delta\times V|^2
=(v-u)^4\left(|W|^4|V|^2-4\rho^2|Z\times V|^2\right),
\]

with polynomial divided differences \(W=(C(v)-C(u))/(v-u)\) and \(Z=(W-C')/(v-u)\). Actual paired pieces require separate seam deflation and common-parameter derivative matching.

The Pro chat reports positive whole-domain toy arc/seam certificates and a negative curvature-margin control. These are ingredients, not a closed real-coil certificate. Local curvature alone cannot rule out two nearby remote strands.

**First experiment:** complete all-pairs admission for member 2, then one imported circular coil. Cover same-span diagonal, both seam directions, periodic closure, and every remote span pair; use conservative pair-BVH pruning and an independent checker. Bind the certificate to geometry coefficients, transform, radius, arithmetic and seam identities.

**Go/no-go:** only a complete certificate permits removing query-time global ownership checks. Root isolation, tangency, earlier-root ordering and general inside-point classification still require their own contracts. Certificate-generation exhaustion must mean “not admitted,” not “probably safe.”

### C. Conservative analytic sandwiches and explicit approximation

If a simpler center curve \(P\) has a proved two-sided Hausdorff bound \(\delta<r\), then

\[
P\oplus B_{r-\delta}\subseteq C\oplus B_r\subseteq P\oplus B_{r+\delta}.
\]

This elementary distance argument can give cheap certain-inside/outside tests or uncertainty windows before exact refinement. Alternatively, use an explicitly identified approximate solid only after fidelity/topology/clearance acceptance.

Near tangency, arbitrarily small geometric error can change hit count. A boundary-distance estimate proportional to \(\delta/\gamma\) requires a unique common local crossing and a positive transverse margin \(\gamma\). Approximation alone is not a nearest-root certificate.

**Priority:** secondary accelerator/control route. Do not revive the blocked torus-arc candidate by relabeling sampled fit error as certification.

### What can be borrowed from existing work

Complete polynomial isolation and reach characterization are established foundations. Rendering papers provide useful candidate generators and hierarchy ideas, but must satisfy OpenMC's first-boundary and inside-origin contract before reuse. The [Phantom Ray-Hair Intersector](https://research.nvidia.com/publication/2018-08_phantom-ray-hair-intersector) is directly relevant swept-curve work; the Pro review specifically flags its termination limitations. Its full PDF was not independently retrieved in this review, so that section-level assessment remains attributed to the Pro review.

Robust sign predicates alone do not certify coefficient construction, transformed boxes, recovered roots or event ordering. Existing library licenses and numerical APIs must be checked before integration. No novelty or priority claim is justified by the current review.

## 8. Recommended order of work

| Priority | Small concrete deliverable | Stop/acceptance condition |
| --- | --- | --- |
| **1. Finish the active local study** | Matched native/plasma and same-geometry accelerator on/off coil transport; source/material/data/input hashes; transport time separated from startup; paired spectra and damage scores. | Every exit/count/finite/ownership gate passes. Sparse bins stay unqualified. Report actual throughput, whether 80% is met, and any failed histories. |
| **2. Preserve a reviewable follow-up** | Commit repaired specialization/box-entry tests, harness, negative comparison tests and final receipts to the local PR #5 branch after its independent review. | Reverify affected published scalar controls after solver edits; do not reuse old binary certificates silently. |
| **3. Recover the physical target** | Accepted rectangular CAD/edge/trim revision, periodic identities and material/tally ownership; reconcile accepted facets with later ParaStell solids. | Hash-bound actual target, no substitution by diagnostic ellipse. |
| **4. Run the two deciding mathematics pilots** | One genuine ruled coil event ledger; one complete offset ownership certificate. | Complete reference agreement/admission and measured cost; retain failure witnesses and bounded work limits. |
| **5. Repair remaining evidence gaps** | Source sampling-key binding negative test; build/audit PR #4's actual compiled BVH. | Malformed sources fail; real topology/box audit passes; traversal tested separately. |
| **6. Extend plasma and transport semantics** | General shaped plasma root/classification controls; periodic tracking, overlap/union and crease/tally ownership tests. | Complete represented-solid semantics for admitted families, not only torus specialization. |
| **7. Upstream qualification** | Experimental-kernel-enabled CI, formatting/regressions, documented API and admission/fallback behavior, independent acceptance. | Reviewable feature with supported geometry and failure contracts. |
| **8. Physical pilot, then large runs** | Qualified source/wall/material model and bounded tally pilot, followed by an authorized resource plan. | Source clearance, geometry fidelity, statistical adequacy and capacity gates satisfied before scaling. |

The geometry owner may obtain CAD/source inputs while kernel experiments proceed. Large transport runs will not repair an unresolved geometric definition or a missing root proof.

## 9. GitHub continuation map and handoff

- [PR #3](https://github.com/FusionSandwich/openmc/pull/3): main checkpoint and this synthesis. Reviewed starting commit **63359cb83d36b419a7e9ba60c45f867073703c21**.
- [PR #4](https://github.com/FusionSandwich/openmc/pull/4): independent BVH diagnostic proposal, unintegrated.
- [PR #5](https://github.com/FusionSandwich/openmc/pull/5): restricted exact-control offset kernel and published evidence at **0098a5e9577a23c48bb2b00d7f4f2f5ea6437817**; active transport follow-up continues separately.
- [Review receipt](CHAT_SYNTHESIS_20260926.json): cutoff, reviewed scopes, fresh artifact/CSV checks, and limits.
- [Detailed local history](LOCAL_CONTINUATION_20260925.md): retained experiments and failures.
- [Matched benchmark protocol](../experiments/benchmark_portability/MATCHED_PROTOCOL.md): baseline measurement contract.

Original accepted P00 CAD/H5M and all optimization/source files are not necessarily in the public repository. The earlier handoff records their hashes and local provenance. A GitHub-only worker must obtain the exact missing inputs before making physical claims.

### Suggested prompt for the next Pro/Codex continuation

> Read dev/stellarcsg/reports/CHAT_SYNTHESIS_20260926.md in FusionSandwich/openmc, then the immutable PR #5 RESULTS.md, CONTINUATION_HANDOFF.md and acceptance receipts linked there. Confirm the current PR heads and whether the local transport follow-up has completed before duplicating work. Pick exactly one bounded deciding experiment: complete ruled-face events for one accepted rectangular coil, or a complete offline ownership certificate for one restricted offset coil. State the represented geometry, exact input hashes, complete-domain proof obligation, unsupported branches, work budget and independent checker before coding. Preserve all failure cases. Recover the mathematics prototype bundle before claiming its 52 checks reproduced. Report executable artifacts, completeness and cost separately; do not infer physical fidelity or near-native throughput from the frozen scalar bank or torus specialization.

**Current conclusion:** there is a usable restricted correctness milestone and a substantial internal speed improvement. The next high-value work is complete matched evidence plus a compiler/representation experiment that removes repeated global geometry work. General physical stellarator CSG at nearly native speed remains an open goal.
