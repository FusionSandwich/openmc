# StellarCSG: current state, blocker diagnosis, and continuation — 2026-09-26

**Later September 26 update:** [the new synthesis](CHAT_SYNTHESIS_20260926.md) reviews the subsequent restricted exact-control offset milestone, independent scalar bank, internal accelerator timing, active matched transport follow-up, and mathematical alternatives. The legacy general-swept findings below remain valid for their recorded representation/source; they are not the latest status of the new offset mode.

## Assessment

The main barrier to near-native OpenMC speed is an **unfinished correct general swept-surface intersection algorithm**. The implementation finds plausible crossings, but cannot certify that a closer crossing was not missed. The latest saved strict replay admits **zero general-swept hits**: 73/160 queries are unresolved and 87/160 are no-hits. This is an intentional failure-preservation repair after four wrong roots were found in the old fast kernel. Returning those candidate distances would restore apparent speed while restoring the correctness gap.

Mathematical/numerical work and implementation work are both needed. Physical coil fidelity and plasma-source clearance are independent missing inputs. Performance optimization is a subsequent gate; no correct candidate has a qualified matched comparison with native ZTorus. There is no demonstrated mathematical impossibility of fast stellarator CSG, and no evidence yet that the current general nearest-centerline formulation can achieve 80% of native throughput.

This assessment reviews source/evidence at `52dbc175891838dfbf3e0b97808f354144a51e6e` on `JS/stellarcsg-local-continuation-20260925`. [Draft PR #3](https://github.com/FusionSandwich/openmc/pull/3) remains the main checkpoint. [The September 25 handoff](PRO_HANDOFF_20260925.md) and [detailed continuation log](LOCAL_CONTINUATION_20260925.md) retain the full history; this page supersedes their stale numerical/status summaries where explicitly stated below.

## Tests and results checked

| Evidence | Checked result | What it establishes |
| --- | --- | --- |
| GitHub PR #3 CI | All **11 build/test lanes pass**, including MPI/OpenMP/DAGMC variants; lane durations about 24–52 minutes. Formatting fails with **57 clang-format checks**. [Saved check status](STATE_GITHUB_CHECKS_20260926.json), [run](https://github.com/FusionSandwich/openmc/actions/runs/36191312709). | Upstream regressions and Python surface roundtrips. The inspected job log says `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG OFF`; the dedicated standalone workflow only auto-triggers on the older foundation branch. These green checks do not qualify the experimental C++ kernel. |
| Recovered-old strict bank | Four wrong-root IDs: **a03, a06, a08, a15**. [Exact comparison](local-cont-20260925/strict-old-01/oracle-comparison.json). | The old fast path is not an acceptable correctness baseline. Finite residual checks alone did not repair it. |
| Latest saved strict replay | **73 unresolved, 87 no-hit**, with all four old failure IDs unresolved. The 87 resolved rows agree with the retained exact lane; input provenance matches. [Raw bank](local-cont-20260925/same-span-prefix-bank-01/candidate-0.jsonl), [new independent reread](STATE_RECHECK_20260926_03.json). | Supersedes the earlier **51 unresolved / 21 hit / 88 no-hit** checkpoint. This is a recheck of saved results, not a fresh execution of HEAD. It does not prove the 87 no-hits generally. |
| Native adapter after tie repair | Circular and shaped members and the collection reject uncertified distances; no transport. [Receipt](local-cont-20260925/native-adapter-tiebreak-01/receipt.json). | Native integration preserves failure status. Registration and XML parsing work; native swept tracking is not admitted. |
| Rounded-Horner bound audit | Recorded **552,960 inequalities** on 640 analytic spans, 10,240 tiles and 3,840 final box endpoints pass. Auditor/raw-box/predecessor/source hashes still match. [Receipt](local-cont-20260925/compiled-horner-enclosure-03.json). | A substantial stored-power centerline enclosure result under recorded arithmetic assumptions. It does not prove rounded frame evaluation, traversal, nearest selection or earlier surface-root exclusion. The mathematical calculation was not rerun in this review. |
| Material and union controls | Recorded 360/360 sampled material entries. Union/priority Boolean occupancy agrees on all **262,144** resolved sign assignments; corresponding physical track fields are bitwise identical. [Equivalence receipt](local-cont-20260925/p00-magnet-union-equivalence-02.json). | Bounded derived-facet/common-material controls. This review rehashed **25 artifacts**, including the two banks' XML/HDF5 outputs and referenced facet payload; all match. It did not rerun 360 histories or independently redo the full Boolean proof. |
| Source interface, fresh local rerun | Existing WSL environment: **9/9 synthetic tests pass**, 4.263 s. [Test receipt](STATE_SOURCE_TEST_20260926.json). | Python interface checks only. Initial Windows attempts hit absent OpenMC import/dependency paths; no package was installed. |
| Two fresh negative controls | Comparator accepts a candidate **NaN distance** as PASS; source loader accepts **swapped source/mesh sampling hash labels** after consistent fixture rehashing. Both false passes reproduced. [Review receipt](STATE_RECHECK_20260926_03.json), [reproducer](../qualification/recheck_checkpoint.py). | Two real evidence-tool defects needing small fixes and regression tests. The existing source tests miss the second defect. These synthetic counterexamples do not invalidate the checked finite historical bank or admit a physical source. |

The new review script's exit 0 means its artifact review and eight dependency-free existing parser tests completed. Its two negative controls intentionally report `false_pass_reproduced: true`; exit 0 is **not** a solver or parser qualification result.

## Where the main solver is stuck

### 1. Candidate finding is implemented; nearest-root certification is not

In [the swept distance implementation](../src/compiled_swept_surface.cpp), the BVH limits candidate spans, proxy cylinder/spheres seed Newton, and a projected two-variable Newton iteration proposes an intersection. The fallback samples eight ray segments and bisects sign changes. A found root does not prove that the prefix contains no earlier root; sign scans also do not establish absence of tangencies/even roots.

The code now retains **every intersected candidate span**, including a span where Newton succeeded. At the end, `earliest_unresolved <= best_t` preserves terminal unresolved. No production certificate currently clears those retained prefixes. Thus a BVH audit alone cannot admit a hit: it verifies candidate coverage/topology, while the missing root-exclusion/root-isolation mechanism still has to be implemented.

### 2. The difficult region is a periodic seam and two coupled definitions

The off-production algebraic/interval experiments made real progress. They excluded all 640 analytic spans before a finite lead gap under their stated experimental arithmetic models. Krawczyk tests and strip covers support a unique *modeled* crossing in the last seam chart, with the paired first chart excluded. Exact stored-power identities, stationary convexity bounds, real Newton contraction, and sampled compiled implicit sign brackets also agree in these two examples.

The remaining transfer is load-bearing: continuous local-parameter root boxes, seam ownership, the rounded normal/radius/frame path, globally chosen nearest-centerline branch, and the exact implicit function used by OpenMC must agree. The modeled seam roots lie only about **2e-14** from a chart boundary and inside a gap between adjacent binary64 global angles. A certificate cannot demand that Newton land exactly on the real root in that global-angle representation.

Direct interval tracing also lost correlation between a stationary polynomial and its derivative: even 4,096 query partitions left a Newton guard undecided. A later curvature/contraction argument solved the **real-arithmetic** part, but not every rounded compiled operation or the global nearest/root prefix. Increasing sample counts or repeating the same loose interval calculation does not finish this missing interface.

The distance code solves parametric sweep equations; classification chooses the closest centerline and evaluates an ellipse in that frame. The current code includes a residual cross-check, but compiler-level regularity/unique-coordinate admission for arbitrary coils is not complete. A documented common geometric definition and admissible envelope are necessary before general proofs or optimization.

### 3. Work accumulated in diagnostic scripts without closing the runtime gate

Most recent proofs are narrow, off-production evidence. They do not change the unresolved disposition. The next mathematical deliverable should be a bounded **runtime exclusion/isolation algorithm** with an explicit contract, rather than another isolated sample or arithmetic identity. Keep the existing exact audits as regression evidence and use them to constrain that implementation.

## Physical geometry is a separate blocker

The user-confirmed optimization repository has the correct WISTELL-D filaments; the tracked filament SHA-256 matches. P00 requests a nominal **30 × 30 cm rectangular coil section**. The current **10 × 8 cm ellipse** is a diagnostic representation, with at least a 5 cm nominal support deficit at a shared section center/tangent plane. Its acceleration cannot qualify the intended magnet shape.

Accepted P00 facets contain eight exact transverse intersections among volume pairs 15–16 and 17–18. The one-material union resolves occupancy for the common magnet material in the diagnostic representation; per-coil tally ownership and continuous-CAD fidelity remain open. Original accepted P00 CAD/section-frame revision is not tied to a complete available STEP export in this branch.

The separate UQ task's latest inspected result (19:16 UTC on September 26) reports an ordinary ParaStell combined CAD build still running. Its earlier coil-only result reports **48 valid solids**, all **1,128 pairs** tested with no positive Boolean overlap volume found, and **224 unresolved contact/distance checks**. This is promising for obtaining a physical reference, but is a different generated CAD result from the accepted P00 facet artifact. It does not disprove the exact facet intersections or supply a source-clearance certificate. This task did not SSH or launch a competing job.

The real one-period plasma source remains unadmitted in this StellarCSG handoff. Source export, fixed-wall clearance, moving-plasma admissibility, normalized source/rate separation, and full wall/blanket transport remain distinct gates.

## What the timing says, and what it cannot say

- The saved unlike-bank sentinel measures recovered-old **4,832 ns/query** and native ZTorus **175.065 ns/query**. They use different geometry and ray banks; their arithmetic ratio is not a matched speed claim.
- A separate strict-bank old/residual-candidate session measured **1,161.875 / 1,385 ns/query**: the candidate was about **19% slower**, and all four wrong roots remained. This disproves the claim that the residual tweak supplied a correct fast kernel.
- Candidate/Newton/subdivision counts and fallback time fractions were disabled/null in the decisive strict timing. There is no measured attribution of current cost to candidate counts, root solving, classification, bounds, or fallback.
- Source inspection identifies potentially substantial work: closest-center queries solve a degree-five stationary problem in long double; ray distance may try multiple Newton seeds and repeated implicit/bisection evaluations. Those are optimization targets once correctness is usable. There is no qualified corrected-candidate throughput measurement yet.
- `<=1 us` per single-coil query and `>=80%` native throughput are different targets. Under an actually matched benchmark, 80% throughput means at most **1.25 times** native time for the same operation. Reaching 1 us alone cannot establish that. The observed 175 ns control is only a sizing reference until banks and geometry are matched.

Historical August reports of speedups over fine DAGMC used different fixtures and weaker correctness checks. They do not establish current near-native performance, physical winding-pack fidelity, or compatibility with the later strict failures. The plasma/radial-spline path and a complete nested reactor model also need their own accuracy and closure gates; solving the magnet kernel alone does not qualify the whole stellarator pipeline.

## Concrete continuation plan

| Priority | Deliverable | Acceptance before moving on |
| --- | --- | --- |
| A — small evidence repairs | Reject nonfinite/duplicate malformed comparator inputs; bind each required source sampling hash to its documented key. Add the two reproduced negative tests. | Each malicious fixture fails; existing valid controls pass; historical four wrong roots remain failures/blocked. No tolerance inflation. |
| B — finish the pending BVH evidence | Review [Pro-generated draft PR #4](https://github.com/FusionSandwich/openmc/pull/4), commit `11f8941057ab1500c6e1fd69f59dce39fde8b510`; use a fresh machine inventory before the bounded local helper build. | Actual 640-span dump/audit passes, deliberately corrupt topology/boxes fail. Then separately test ray/point pruning decisions; topology alone is insufficient. |
| C — one usable correct general hit | Freeze one analytic shaped member's geometric contract and paired seam coordinates. Implement continuous local-u root isolation and earlier-prefix exclusion with conservative rounding/error bounds and an explicit work budget. | One native nontrivial hit is admitted; inside/outside/tangent/seam controls behave correctly; an intentionally unprovable case stays unresolved. Then complete the 160-ray exact replay with zero wrong roots and zero unresolved for its admitted input envelope. |
| D — obtain the physical target in parallel | Recover authoritative accepted CAD/section/revision or reconcile the separate ParaStell CAD export; define union/material/tally semantics and obtain source/wall clearance through its owner. | Same physical target and hashes for native and faceted references; bounded fidelity/clearance rather than sample-only agreement. |
| E — profile and optimize a correct candidate | Enable diagnostic counters outside timed production loops; profile roots, candidates and fallback. Precompute admitted span bounds/frame/error data, use tight BVHs and a cheap admitted fast path with bounded certified fallback. | Hash-bound same-session matched distance/classification/normal and transport study; all error/lost-history gates pass, then report median and tail costs plus throughput. |

For C, my proposed change in approach is to carry **local parameter intervals** through the seam and state the geometric/error contract directly. Reuse the real-polynomial contraction and algebraic interval evidence. Avoid making correctness depend on reproducing every branch of a long global-angle Newton loop. This is a design proposal, not an implemented or proved repair.

If the nearest-centerline ellipse cannot express the physical rectangular pack with a tractable consistent classification contract, investigate a second architecture that exports the accepted CAD's spline/ruled faces into bounded parametric patches and intersects those patches directly. That route needs a separate fidelity, inside/outside, root and performance validation; it cannot be presumed near-native. Native analytic primitives should be used where the source geometry is actually that primitive, with approximation modes explicitly identified.

Large conventional ParaStell/OpenMC reference runs can progress through the existing owner once their geometry and source gates pass. Large **StellarCSG** runs cannot substitute for the missing small root certificate. The present best next action is B followed by the narrowly specified C implementation, with A repaired before accepting new evidence.

## Handoff and work ownership

- Main code/evidence and this updated diagnosis: PR #3; root integrator owns mathematical/physical acceptance. No default branch merge occurred.
- Pro BVH proposal: PR #4 is open and **not integrated**. The chat reports Python syntax/synthetic positive and corrupt-box tests passed; C++ build, actual dump and real provenance audit were **NOT_RUN**. No GitHub checks are reported on PR #4.
- The frozen-oracle and source-binding Pro briefs were prepared but never submitted. The reproduced defects now make those tasks precise. Private chat URLs and the local dispatch index remain outside Git.
- Historical builds/tests do not transfer credentials, environments, SSH capacity or resource authorization. No dependency acquisition, rebuild, new native replay, model transport, schedule change or remote job occurred during this review.
- Local user edits to `AGENTS.md`, delegation/scheduler handoffs, and old exploratory scratch are preserved outside this documentation checkpoint. Current user-wide operator rules govern all continuation work.
