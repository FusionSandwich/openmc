# Coil and plasma CSG: authoritative geometry-build and transport benchmark

This incorporates the user's latest clarification and supersedes the earlier aggregate-wall-only acceptance wording. Geometry build time and transport time are separate primary measurements. End-to-end wall remains useful supporting accounting.

## The three methods

| Method | Coil geometry | Plasma geometry | Purpose |
|---|---|---|---|
| Our custom CSG | Full complex target coil centerline and winding-pack section/frame/corners/trims | Target nonaxisymmetric stellarator plasma | Method being developed; independent accuracy acceptance required |
| Built-in OpenMC CSG | Simple flat annular ring using cylinders and planes; collection controls at comparable count and gross scale | Similarly sized torus | Transport cost reference; simpler shape expressly permitted |
| DAGMC | Mesh of the target complex coil geometry at stated tolerance | Mesh of target plasma at stated tolerance | Same-target geometry and performance reference |

Latest user correction: every acceptance transport run must complete **at least 20,000 histories**. Earlier 200/1,000-history coil runs are diagnostics only. The DAGMC comparison must use **verified Double Down / Embree**, with build/linkage and runtime backend evidence; ordinary DAGMC is a separately labeled historical reference. A 20,000-history minimum does not by itself guarantee adequate native duration or tally statistics.

Our custom geometry must not be replaced by an annulus, torus or circular 1 cm tube to meet the final speed target. Those remain labeled diagnostic fixtures. Preserve exact analytic fast paths when the input is genuinely analytic, but do not use their performance as qualification of generic complex geometry.

"Full target shape" requires source identity and admitted fidelity: centerline, winding pack dimensions, frame, corners/trims, seams and placement. The user-confirmed WISTELL filaments are the centerline source; current diagnostics do not by themselves bind the physical rectangular pack. Missing fidelity evidence must remain explicit while implementation work continues.

## Transport acceptance

For the same completed history count and declared workload:

**T_transport(custom CSG) / T_transport(built-in proxy) ≤ 1.25.**

Report elapsed seconds and the transport-time ratio directly; the user specifically requests time comparisons rather than throughput reporting. The working interpretation of "80% as fast" is that if the built-in proxy takes 10 seconds in transport, custom CSG must take at most 12.5 seconds. This target concerns transport, not geometry build, startup, total process wall, or shape accuracy. It does not require custom time to be 80% of native time. Include the built-in OpenMC plasma torus explicitly, alongside the built-in flat-ring coil proxy.

The custom solver must also pass correctness/fidelity gates. A fast failed, unresolved, wrong-first-root or silently simplified model cannot pass. Report complete work and failures rather than omitting difficult queries.

## What to time

1. **Cold geometry build/preparation:** begin from explicitly named source geometry inputs; finish with verified transport geometry and model files. Custom CSG includes coefficient/frame/section generation, geometry admission/certificates, offline hierarchy construction and payload/XML export. Built-in includes primitive/Region/cell construction and export. DAGMC includes applicable CAD construction, faceting/meshing, material/volume tagging and H5M export. If CAD or compiled payload already exists, name that starting point and separately measure its reuse path; do not label omitted work as a zero cold build.
2. **Runtime initialization:** geometry loading and any load-time acceleration/admission, nuclear data reads and other native startup. If a geometry-only substage can be measured, record it separately. Do not rename all startup as geometry build or omit a load-time BVH. Offline and runtime stages must not overlap/double-count.
3. **Transport:** use the actual OpenMC transport timer for the same completed histories, source bank/energy, physics/data/material choices, threads and production tally policy. Record elapsed transport seconds directly. Tally scoring performed inside transport is already included; do not add it twice. Tally-off runs are separate diagnostic attribution, not replacements for tally-enabled acceptance.
4. **Output and external wall:** retain statepoint writing, finalization and actual invocation wall time so user-visible total cost is clear. Output frequency/files must match. Report one-off software compilation separately; it is not geometry generation.

For repeated production runs, show per-geometry cold setup and per-run setup/transport/output separately. State amortization explicitly. No worker benchmark may infer full elapsed time by reciprocating an active calculation rate.

## Comparison controls and accuracy

- Separate coil and plasma tables; never combine distinct geometry families or history counts into one timing ratio.
- Freeze source geometry, section/frame/units/scale, geometry artifact, source bank, material/data, binary/library, seeds/counts, threads/hardware, tally/output settings and arithmetic/tolerance identities.
- Built-in approximations may differ in shape. Match gross dimensions, placement, coil count/period, section scale and outer world where feasible. Declare resulting volume/material-path differences and crossings/work when measured. This is a cost control, not a claim of identical physics.
- DAGMC must represent the same intended complex target with recorded mesh tolerance, triangle count and accuracy measurements. Startup/mesh-build tradeoffs must remain visible.
- Independently verify custom first-entry/exit, thin chords, tangencies, seams, normals, corners, cell/material identities and local tally scoring. Compare implementation variants on the same solid for regression. Do not require tallies of deliberately different-shaped native proxies to be equal as a fidelity test.
- Use enough native duration and repeated interleaved observations for a meaningful time ratio, within admitted resource limits. Small pilots are diagnostics. Record uncertainty/tail/fallback costs and do not claim precise portable ratios from a 3 ms denominator.
- Unknown, absent, unsupported or unrun stages are **UNKNOWN/NOT_RUN**, not zero or PASS.

## Report layout

One table per actual target family, with these columns:

| Method | Shape/fidelity | Histories | Cold geometry build s | Initialization s | Transport s | Output s | Process wall s | Transport time / built-in | Accuracy/tally status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Custom CSG | Full target | fixed | measured/UNKNOWN | measured/UNKNOWN | measured | measured/UNKNOWN | measured | measured | PASS/FAIL/UNRESOLVED |
| Built-in proxy | Declared simpler shape | same | measured/UNKNOWN | measured/UNKNOWN | measured | measured/UNKNOWN | measured | 1.0 | Cost control |
| DAGMC | Target mesh, tolerance stated | same | measured/UNKNOWN | measured/UNKNOWN | measured | measured/UNKNOWN | measured | measured | Independent fidelity/scoring evidence |

No full-target three-method coil/plasma table is currently complete. Existing recorded comparisons are listed in `BUILD_TRANSPORT_RESULTS_20260926.md` with missing geometry-build times explicit.

## Continuation ownership

Existing coil profile Sol owns coil work; existing plasma Sol owns periodic plasma proposals; independent Sol reviews consequential changes. Both owners received this clarification. Current bounded work continues without interruption. Exclusive compute lease, full pre-build operator inventory, local resource caps and no acquisition/SSH/schedules remain in force. Root launched no new build or numerical job for this contract.
