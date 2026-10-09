# StellarCSG method, speed and tally review

Review date: 2026-09-26, evidence observed through approximately 23:09 UTC.
This updates [CHAT_SYNTHESIS_20260926.md](CHAT_SYNTHESIS_20260926.md).

## Decision

**We have executable restricted geometry methods and useful new mathematical mechanisms. We have not found a complete physical stellarator/coil method that meets the 80% native CSG speed target.** Ordinary OpenMC tally integration has now been demonstrated on small plasma and coil proxies. Universal tally compatibility and physical device qualification remain open.

Interpret the user's target as throughput at least 0.8 times native CSG, equivalently transport time at most 1.25 times native for the same completed workload. Geometry compilation/build time is a separate quantity and has no accepted comparative result here.

The strongest implementation evidence is draft [PR5](https://github.com/FusionSandwich/openmc/pull/5), now published at **54f8af0dbccb1ce2dcd066f27ea79667f2d6ee8f**. Local HEAD and the remote branch head matched in this review. Its owner session, **Solve StellarCSG certified intersections…**, is completed/idle. No session was interrupted or restarted.

## What was reviewed

- All four newly dispatched ordinary Pro chats: complete visible final responses were read and saved privately.
- **Inspect Repository Code**: its formerly unavailable final is now recovered and read. It delivered a standalone alternative kernel; native integration and the original frozen-bank replay remain NOT_RUN.
- **Mathematical methods review**: the full visible final is now readable and saved. Its research routes are advanced by the two newer geometry chats.
- The earlier eleven conversations, their retained failures and results, were reviewed through the existing synthesis and private saved ledger. They were not all queried afresh. Combined accounting is seventeen dispatched repository conversations, plus two never-submitted briefs and one local implementation session.
- Local transport and integration reports, acceptance records, selected current source paths, and independently recorded review evidence. A separate Sol reviewer was assigned a bounded read-only receipt/source consistency check.

Pro chat prototype executions below are **reported by the destination chats**, not rerun here. Their downloadable bundles were advertised but not downloaded, applied, compiled or executed in this review. Reading a final response is not an independent proof audit. This root review acquired no software/data and launched no build, transport or SSH job.

The independent Sol consistency review matched **20 acceptance artifact hashes, 15 listed source hashes, all six repaired receipt/comparison links, six logs, 60 retained output files, nine unique live input identities and the current native libraries/probe**. No current mismatch was found. This corroborates the finite native integration record; it does not reproduce all mathematical proofs or establish a production release.

## Speed evidence

The published [transport proxy report](https://github.com/FusionSandwich/openmc/blob/54f8af0dbccb1ce2dcd066f27ea79667f2d6ee8f/dev/stellarcsg/reports/transport-proxy-20260926/RESULTS.md) records eighteen sequential runs with three seeds, twenty paired batches per seed, identical materials/data/source/threads within each comparison, and no recorded lost/unresolved diagnostics.

| Comparison | Observed throughput | Interpretation |
| --- | ---: | --- |
| Periodic plasma surface / native ZTorus | **62.08%**, range 58.50–65.04% | Below 80%; exact torus specialization only |
| Accelerated near-circular coil offset / native ZTorus | **0.1299%**, range 0.1141–0.1395% | Far below target; slightly different represented geometry |
| Same coil, accelerator on / off | **about 2.49 times** | Real internal acceleration; no native speed qualification |
| Native flat annular ring / native torus | **125.14%** | Different cross-section; cost control only |
| Pro ruled backend / standalone primitive annulus control | **6.099% median paired ratio** | Same exact annular rectangle, standalone queries; sizing gate failed; OpenMC NOT_RUN |
| Pro ownership omission, complete diagnostic bank | approximately **0.99–1.02 times** its own baseline | Completed-hit medians improve about 3.6 times, but unresolved thin crossing dominates |
| Pro canonical swept alternative | shaped complete-bank mean about **291 microseconds/query** | No native denominator; native speed NOT_RUN |

The plasma workload uses an R=100 cm/r=20 cm void torus and a 1 cm Fe56 shell. The coil is a radius-5 cm tube around a 64-control near-circle of major radius 100 cm. The native flat ring uses radii 95/105 cm and planes z=±5π/4 cm; its volume matches the native round torus, not its shape. It cannot establish spectrum equivalence for the round coil or physical rectangular pack.

Native coil runs were approximately 3 milliseconds, limiting the precise ratio. The spline runs were approximately 2.33–2.73 seconds: the short denominator does not plausibly erase the large gap. Plasma needs about a **1.29 times throughput improvement** to reach 80% on this workload. Coil needs approximately **616 times** against its reported torus ratio; this is a scale estimate, not a stable speed qualification.

The later six-run tally/source integration campaign deliberately makes **no new speed claim**. Its repaired library differs from the older timing library, so old timings must retain their historical build identity.

## Have we found a new geometry method?

### 1. Implemented native restricted offsets

PR5 has an explicit exact-control offset representation with interval/Bernstein first-root admission and fail-closed unresolved behavior. Earlier independent frozen-bank certificates cover 69 hits and 91 misses in each accelerator mode. Native seam crossings, classification and selected normals were exercised. These establish a restricted correctness milestone, not arbitrary varying-frame or rectangular winding-pack fidelity.

Plasma uses a separate periodic surface implementation. The matched transport study tests its exact constant-coefficient torus specialization. It does not establish correctness or speed for non-axisymmetric stellarator plasma.

### 2. Offline ownership: strongest new compiler advance

**Implement Offline Ownership Path** reports complete admission for the retrieved member-2 coefficient payload: 256 spans, all 65,536 ordered pairs, exact periodic C2 joins, and transformed reach lower bound 1.25 for a unit offset. An independently implemented checker reconstructs coefficients/boxes and verifies coverage. Compiler/checker observations are approximately 0.49/0.46 seconds and a 2.3 MB certificate.

Its solid uses a constant metric with 14 cm transverse and 24 cm axial radii. It is not the physical rectangular pack. The containing HDF5 was not reconstructed/rehashed by that chat; certificate identity is the retrieved coefficient payload, with native loader/frame binding still open.

The complete certificate can justify deleting one repeated nonlocal owner check **after a validated boundary root**. It does not eliminate arbitrary-point classification, tangencies, first-root ordering or earlier-domain exclusion. The underlying reach characterization is established mathematics, rather than a claimed new theorem. [Aamari et al., Estimating the Reach of a Manifold](https://arxiv.org/abs/1705.04565).

The query prototype has 39 hits, three misses, one invalid input and one unresolved thin crossing. An independent vertical reference confirms 34 hits/two misses; five accepted nonvertical hits still lack an independent root check. The thin case has two positive roots, first about 49.99990926838297 cm, but costs roughly 216,000 system evaluations and remains unresolved. Ordinary completed hits improve about 3.6 times; whole-bank cost barely improves. Native transport/tallies and imported WISTELL coil admission remain NOT_RUN.

**Recommendation:** preserve this certificate mechanism, independently audit its proof/identity, and fix the thin pair with the planar-normal algebraic specialization before native integration or another speed claim.

### 3. Ruled rectangular faces: representation research

**Implement Geometry Prototypes** reports a complete exact reference for an injective synthetic cubic rectangular sweep. Ruled rational cubic edges reduce to a degree-at-most-six determinant polynomial after positive-denominator clearing. Geometry-dependent vector coefficients can be compiled once. Complete real-root isolation is an established foundation; multiplicities, trim tests, recovered parameters and ordering in ray distance remain geometry-specific work. [Sagraloff–Mehlhorn, Computing Real Roots of Real Polynomials](https://arxiv.org/abs/1308.4088).

The six-root witness is decisive: one regular patch can have six valid crossings, with parameter order opposite to ray-distance order. The closed reference retains both endcaps, all events, incident faces, and one-sided membership. Reported controls include 72 Python tests and independently checked ledgers. The compiled fast path is only an exact annular rectangle; general cubic C++ query and actual OpenMC tracking are absent.

A composite whole-solid Surface also encounters the nonvirtual native sense/tie rule at creases: one canonical face normal need not determine the whole-solid side. Separate implicit surfaces/Regions or an explicit directional-sense interface need an integration decision and tests. Do not blindly apply the proposed API change.

**Recommendation:** retain the complete reference, obtain the accepted rectangular CAD edge/trim correspondence, and port one admitted cubic family. Require complete event-ledger agreement before speed tests. The physical pack definition remains missing; correct coil filaments do not settle section shape/frame/CAD identity.

### 4. Canonical swept alternative: now recovered

**Inspect Repository Code** reports a compiled standalone exact-cardinal-spline representation, all-pairs coordinate admission, interval/Krawczyk root isolation, shaped seam hits and consistent local normals/classification. It reports 64-check GCC/Clang/sanitizer suites, 48 high-precision comparisons and 15,027 interval-enclosure checks. The mathematical argument has not had independent acceptance. Tangent/near-tangent cases remain unresolved; original four failure IDs and frozen 160 queries were not replayed. Native adapter is an uncompiled proposal.

This is a separate canonical representation, not a silent repair of the legacy rounded-frame solid. Avoid merging a second broad experimental kernel before showing a decisive advantage over the existing admitted offset path.

## OpenMC tally and source compatibility

The [published native integration report](https://github.com/FusionSandwich/openmc/blob/54f8af0dbccb1ce2dcd066f27ea79667f2d6ee8f/dev/stellarcsg/reports/openmc-integration-20260926/RESULTS.md) is substantive progress. Six fresh repaired runs completed: 4,000 plasma and 400 coil histories, with separately sampled source sites and stochastic volumes. **37 plasma tally comparisons agree; 18 approximate-coil comparisons meet their declared approximation criterion.**

| Capability | Evidence/status |
| --- | --- |
| Cell/material filters and small local CSG subcells | Native finite proxy tests pass |
| Regular, rectilinear, cylindrical and spherical local meshes | Native tested cases pass after equator repair |
| Flux, total, absorption, damage-energy and energy bins | Exercised; sparse bins do not establish full spectra |
| Tracklength, collision, analog; surface/mesh currents | Selected native combinations exercised |
| Universe, cell-instance, birth-cell/birth-mesh, time/particle and other selected filters | Finite root-universe/instance-zero cases; not general repeated geometry |
| StatePoint, Summary, reshape/slice/DataFrame/CSV | Exercised on these fixtures |
| Structured MeshSource, constrained box and FileSource | Native proxy execution and sampled-site containment tested |
| Physical VMEC/UQ support, fixed-wall clearance and rate | Not admitted |
| Transformed local meshes, repeated universes/lattices/distribcell | Additional qualification required |
| Photons, MPI/OpenMP, complete boundary conditions, depletion/MGXS/variance reduction | Not qualified |
| Generic spline Python membership/translate/rotate | Incomplete adapters |

Ordinary tally scoring depends on valid transport segments, cell/material/instance identities and surface events; it should continue through native tally APIs. A local mesh overlay can select a small region without adding transport boundaries. Cell splitting remains appropriate when real CSG subcell identity is needed. Native scores/filters have their own compatibility restrictions; universal support does not mean every possible combination is legal. [OpenMC tally guide](https://docs.openmc.org/en/stable/usersguide/tallies.html).

Every declared score array has nonzero aggregate response, but the independent review found roughly 80% zero individual values in plasma mesh cases and 85% in coil cases. Those zeros are not evidence of per-bin statistical adequacy. Instance tests use instance zero, and response weighting is constant; general repeated instances and arbitrary response functions need their own tests.

**Important native defect already repaired:** the initial campaign preserved integrated closure while moving spherical-mesh damage-energy between polar hemispheres. The equator was solved as a nearly degenerate squared cone. The repaired exact equator plane and signed-height indexing passed 37 independent native checks, plus 18 partial-grid point-index controls, and six fresh runs forming three native/spline pairs. General partial-angle ray traversal remains unqualified. This proves why totals alone are insufficient.

**New Pro findings still present in current source:**

1. MeshFilter equality inherits type/bin comparison while hashing uses mesh ID. Two filters on the same mesh with different translations/rotations can compare equal and be deduplicated by tallies XML export. Source tracing confirms the path; root did not execute the proposed regression.
2. C++ serializes rotation as nine matrix entries or twelve matrix-plus-angle entries, while Python from_hdf5 directly assigns the flat array to a length-three setter. Rotated statepoint reconstruction needs the narrow fix and actual native tests.
3. StructuredMesh's short-flight branch assigns an entire segment shorter than 2*TINY_BIT to one shifted-start bin. The Pro counterexample crosses a face yet preserves total closure with wrong per-bin fractions. That regression was reproduced in an extracted/scaffold context, **not actual native execution here**. The current source still has the branch. It is separate from the repaired spherical-equator defect.

**Implement Tally Compatibility** reports 105 portable tests and a 71-row capability matrix, but native package/transport NOT_RUN. Its two Python interface patches and retained short-track regression should be reviewed and run in the existing local environment. Its standalone scoring timings are not native overhead evidence.

**Implement Plasma Integration** reports the swapped source/mesh hash-key false pass repaired, a fingerprint/bank contract, 59 portable tests and 24,576 checked analytic births. The local PR5 owner has independently already repaired named hash-role checking and hardened parsing/clearance arithmetic: reconcile patches against current HEAD instead of reapplying the old-base loader diff. The Pro analytic torus sampler batches proposals with identical scalar/batched records, but its large scalar-Python speedup does not establish native transport speed. General stellarator source mapping, actual bank interoperability/physical clearance remain open.

For local flux normalization use the occupied cell/mesh intersection volume. Per-source damage-energy is not automatically DPA/time: physical atom count, displacement model and neutron rate are separate admission requirements. Overlapping observations should retain assume_separate=false; ancestor/descendant cells are not automatically a disjoint sum.

## Earlier failed routes and useful infrastructure

The previous synthesis retains conversation-by-conversation details:

- **Optimize Fast Kernel**, **Bernstein Coil Solver Progress**, **Implemented Candidate B Validation**, **Implemented Bezier Atlas**, and **Reject Candidate D Solver** do not supply an admitted replacement. Wrong earlier roots, sampled fallback, point-based pruning, even contacts and all-blocked runs remain decisive negatives.
- **Implemented Period Import Repair** improved periodic import/provenance, but diagnostic circular geometry and rejected held-out fidelity do not establish physical pack shape.
- **Develop Neutron Source Model** supplied interfaces but failed held-out physical source-rate predictions.
- **Audit repository brief**, **Implement Portable Runner Validator**, and **Repository Access Brief** supplied useful audits/validators/adapters, with explicit remaining limitations and mock-versus-native distinctions.
- **BVH Audit Proposal**, draft PR4, remains an unintegrated diagnostic proposal; actual compiled real-data audit was NOT_RUN in the retained result.
- The two unsent briefs never count as experiments. The newer named-hash repair supersedes the corresponding open issue in the earlier synthesis.

## Next experiments and acceptance gates

1. **Close narrow tally defects first.** Review current-base transformed MeshFilter equality/HDF5 rotation fixes. Run actual Python XML/statepoint roundtrip controls, and a native tiny-track per-bin regression. Retain an energy-redistribution counterexample that preserves grand totals.
2. **Recover and independently inspect Pro artifacts.** Bind archive/patch/source identities; audit the complete ownership proof and both checker implementations. Apply only isolated, nonduplicated proposals. Current review has not downloaded those bundles.
3. **Optimize complete query cost.** Offset lane: repair the thin pair, certify exceptional/even contacts and prefix coverage, then profile classification, root refinement, normal and owner costs together. Ruled lane: port the admitted cubic reference and settle native event/sense design. Fast candidates alone do not satisfy transport.
4. **Use two comparator lanes.** For implementation correctness, use exactly the same represented solid with independent reference and on/off controls. For engineering performance, compare similar-size/source/material torus and flat ring proxies, reporting their shape differences. An exact annular geometry represented both ways provides a stronger native coil cost comparison than unlike tube/rectangle physics.
5. **Rerun stable paired timing after a concrete optimization.** Warmed/interleaved repetitions with sufficient native duration, matching binary/data/source/seeds/tallies/threads. Record completed histories, transport/startup/build times separately and geometry distance/classification/normal profiles, median/tail/fallback costs. Time tally-off and tally-on so shared scoring cost cannot conceal a slow geometry ratio. Require throughput >=0.8 in the declared workload; unresolved queries are failures, not omitted samples.
6. **Generalize beyond controls.** Admit one non-axisymmetric plasma and one accepted physical coil pack, with positive hits, inside exits, seams, material/local-bin ownership, source births and clearance. Extend repeated-instance/boundary/parallel/photons tests by explicit feature gates. Fill sparse spectral bins with predeclared statistical acceptance, not aggregate-only checks.

**Current blocker classification:** substantial correctness mechanisms exist. The offset method's query completeness and tail cost, and the ruled method's compiled/native event implementation, remain computational/algorithmic blockers. Accepted physical CAD/source definitions and general-shaped plasma admission are additional modeling blockers. There is no present evidence that a new general mathematical theorem is required, or that larger model runs would solve these blockers.

Keep the local owner checkout and raw artifacts intact. Published text receipts identify results but do not replace local HDF5/NPY evidence or nuclear data. Before any subsequent build/acquisition, refresh the operator-required inventory. No remote work or automatic successor is authorized by this report.
