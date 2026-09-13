# StellarCSG neutral dual-track benchmark contract

Contract revision: `stellarcsg.neutral-contract/v2` (2026-09-13).
The v1 records remain immutable. This amendment clarifies identity matching and
retention; it does not retroactively qualify old measurements.

## Scope and immutability

This contract belongs to the neutral branch. It defines evidence accepted for
comparison of Track A and Track B; it does not implement either production
algorithm. The qualified baseline is commit
`3041a938c3fb0bc349654f37b0b3ebcd3cd5a9bb`, preserved by
`archive/stellarcsg-composite-3041a938-20260901`.

The harness commit must be byte-for-byte identical in each compared worktree.
Algorithm commits may not be exchanged between tracks before the neutral
comparison. `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG` remains `OFF` by default.

## Required method identity

Every raw result must validate against
`dev/stellarcsg/benchmarks/schema/dual_track_result.schema.json` and record:

- `surface_method`, `coil_method`, and `classification_method`;
- whether specialization and surface-family reuse are enabled;
- exact build and neutral-harness commits;
- SHA-256 hashes of source geometry, compiled geometry, executable or shared
  library, source bank, and H5M when applicable;
- hardware, CPU affinity, thread count, flags, and linked library hashes.

Track A names are `legacy_periodic_patch_v1`, `legacy_swept_span_v1`,
`exact_torus`, `exact_planar_swept`, and `shared_coil_set_bvh`. Track B retains
those controls and may add `revolved_profile_v1`, `bezier_atlas_v2`,
`structured_sector_v1`, `algebraic_proxy_v1`, `coil_biarc_v1`, and
`coil_bezier_tube_v2`.

## Matched execution protocol

One immutable source bank is used per case. Seeds, particles, batches,
materials, tallies, tolerances, hardware, affinity, and thread count are held
constant. Methods run in randomized or balanced order after at least one
warm-up. A qualification block has at least seven measured repetitions;
decisive gates use 11--21. All repetitions are retained.

Each block reruns built-in `ZTorus` as a host-performance sentinel. Shared source
geometry, source bank, settings (including materials, physics, tallies and
tolerances), hardware, affinity and thread count must match across methods.
Each method records its own compiled geometry, executable and linked-library
hashes; these are expected to differ between methods. Within each declared
method and repetition block these identities must remain unchanged, including
warmups. Any unexplained drift invalidates the block. Ordinary DAGMC and Double
Down/Embree additionally require identical H5M bytes. An equivalent compiled
payload across different CSG methods is allowed but is not required.

The command harness verifies declared artifact hashes immediately before and
after each invocation. Linked-library metadata includes local paths and hashes
for these checks. The binary artifact must resolve to the actual command
executable. Interpreter-driven commands declare the interpreter as binary and
the invoked script as an additional artifact. Hashing and durable journal
writes are outside the command's
active transport interval; record them as harness overhead, and account for
possible cache effects when interpreting timing. A declared affinity or method
name is not proof of runtime binding: the campaign owner must independently
verify actual executable linkage, source snapshot, affinity and method dispatch.

Report the median, mean, IQR, coefficient of variation, and a paired/bootstrap
95% interval for the method/sentinel or method/reference ratio. Initialization,
active transport, and total wall time remain separate.

Pair samples by scheduled repetition index, taking the ratio of medians and
resampling complete pairs with replacement. Matching sources does not imply
identical geometry-dependent particle trajectories. Record the numerator and
denominator explicitly. A comparison requires at least seven valid complete
pairs; any invalid attempt still makes the original block ineligible. Retain it
and start a new block rather than silently replacing failed repetitions.

## Required performance observations

Each applicable result records histories/s, ns per distance call, distance and
classification calls/history, crossings/history, geometry CPU fraction,
candidate nodes/patches/spans, correction iterations, local fallback frequency,
production broad-oracle calls, initialization time, and peak RSS. Missing
instrumentation is represented by JSON `null`, never by zero.

## Common accuracy contract

Plasma and blanket comparisons use point-classification disagreement,
independently converged nearest-root error, approximate symmetric two-sided
Hausdorff distance, RMS/p95 surface distance, maximum normal-angle error,
surface-area and enclosed-volume error, seam error, minimum nested separation,
and leakage/current closure.

Coil comparisons use the complete finite swept surface: symmetric two-sided
Hausdorff distance, RMS/p95 distance, normal error, volume and cross-sectional
area error, seam closure, coil--coil and coil--blanket clearance, and nearest
root error. Centerline error is not a substitute for finite-surface error.

Every root mismatch, miss, false hit, lost-particle seed, and informative
fallback case is retained as an artifact and referenced by the result.

## Gates

Correctness is mandatory. Any wrong-nearest-root event fails the method for the
tested case regardless of speed.

| Case | Minimum gate |
|---|---|
| Exact periodic torus | ratio to built-in ZTorus >= 0.95; zero wrong roots/lost particles |
| Exact planar swept coil | ratio to built-in ZTorus >= 0.95; zero wrong roots/lost particles |
| Forced-general torus | throughput / native ZTorus throughput >= 0.25; zero wrong/missed/false roots; zero production broad-oracle calls |
| Shaped axisymmetric | ratio >= 0.50; zero wrong roots |
| Synthetic helical | ratio >= 0.25 and faster than matched fine Double Down/Embree at common error |
| WISTELL-D plasma | faster than matched fine Double Down/Embree; zero lost particles; accuracy and closure pass |
| Representative non-planar coil | coil throughput / matched fine Double Down/Embree throughput >= 0.50, and separately > 1.0 against that reference |
| Complete 48-coil set | 48-coil throughput / matched fine Double Down/Embree throughput >= 0.50, sublinear set scaling, and separately > 1.0 against that reference |
| Blanket/combined | positive-clearance nonuniform blanket; no intersections/lost particles; repeated medians and closure |

Gate states are exactly `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`. A failed
track remains in the comparison.

The two coil denominators above reflect the user's explicit clarification on
2026-09-13. The separate Embree-advantage requirement remains in force even
though it is stronger than the 0.50 continuation threshold. The ZTorus host
sentinel is not the denominator for those coil gates. The 2026-09-13 follow-up
explicitly defines native ZTorus as the forced-general torus denominator;
this amendment preserves the 0.25 minimum and keeps the 0.8 aspiration separate.
Remaining unspecified denominators (shaped axisymmetric and synthetic helical), the
quantitative meaning of sublinear set scaling, and unstated accuracy thresholds
must be frozen explicitly before qualification. No denominator is inferred
for the remaining cases from historical forced-general results.

## Durable command evidence

`dual_track_harness.py` writes a `stellarcsg.neutral-command-campaign/v2`
envelope and a neighboring exclusive-create `*.attempts.jsonl` journal. The
journal retains the campaign declaration, each attempt's start, and each
completed warmup/measured attempt including stdout, stderr, return status and
invalid reasons. Flush and filesystem synchronization occur after each record.
An unmatched start after interruption is unresolved evidence, never a pass.
Process timeouts default to 300 seconds and may be declared per method. No
existing output or journal is overwritten; use a new output path for a retry.

The envelope is timing evidence, not a
`stellarcsg.dual-track-result/v1` qualification record. It therefore does not
claim to validate against the qualification schema. It emits `NOT_RUN` for gate
status when command checks pass and `BLOCKED` when any attempt is invalid.
Separate geometry eligibility, retained adversarial seeds, accurate method
matching, sentinel validation and independent gate evaluation are still
required before a qualification result can be produced. Programmatic calls
without `journal_path` are diagnostic only and declare a null durable journal.

## Model campaign staging

Catalog/import and provenance work may run immediately. Expensive
multi-configuration timing begins only after both tracks have been classified
against the shared analytic and WISTELL-D minimum gates and harness/source drift
checks pass. Each device then proceeds through Q0 provenance, Q1 admissibility,
Q2 common-error fitting, Q3 root correctness, Q4 kernel timing, Q5 Tier 2
transport, Q6 matched ordinary/Double Down DAGMC, Q7 blanket feasibility, and a
selected diverse Q8 Tier 3 subset.

## DAGMC matching

Ordinary DAGMC and Double Down/Embree must traverse the identical H5M byte
stream. The H5M SHA-256, DAGMC/MOAB/Double Down/Embree versions and library
hashes, geometry tolerance, source bank, and OpenMC settings are recorded.

## Artifact layout

Raw immutable records live under `dev/stellarcsg/benchmarks/raw/dual_track/`.
Local-model manifests and retained, redistributable fixtures live under
`dev/stellarcsg/tests/fixtures/multiconfig/`. Plots live under
`dev/stellarcsg/plots/dual_track/` and must state source hash, branch SHA,
method, hardware, threads, tolerance, and sample size.

The catalog validates against
`dev/stellarcsg/benchmarks/schema/local_geometry_catalog.schema.json`.
License-unclear or proprietary geometry is never committed; only hashes,
provenance, local-only classifications, and deterministic generators may be
recorded.
