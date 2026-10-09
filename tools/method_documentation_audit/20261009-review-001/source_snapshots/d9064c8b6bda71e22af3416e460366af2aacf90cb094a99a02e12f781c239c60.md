# Exact-control offset: verified results and limits

Draft PR: https://github.com/FusionSandwich/openmc/pull/5.
The isolated branch is based on pinned
`63359cb83d36b419a7e9ba60c45f867073703c21`; the original checkpoint checkout
and branch were preserved. Baseline source commit `3f8703db2` is retained.
The final accelerated source and executable identities are recorded in
`build-receipt-14.json` and independently checked in `final-acceptance.json`.

The new `exact_control_offset` representation is explicit in C++, Python, XML,
HDF5 and query receipts. Legacy geometry remains the default.

## Achieved

- Native OpenMC member-2 shaped seam: distance **16.000000000001382 cm**,
  outward normal and both directional sense checks pass. An independent exact
  rational proof bounds its distance error by **1.4577968462011388e-12 cm**.
  This is an actual `SurfaceSweptSpline` call.
- Native CSG `Region` classification changes correctly across that boundary.
  The outside region returns the entry above; the inside region, starting at
  that coincident entry, returns exit distance **27.999999999997744 cm**.
  Signed surface indices are -1 and +1. The separate exact exit proof bounds
  the error by **1.89e-12 cm**. This is a geometry crossing smoke test.
- Unchanged frozen bank, with Bernstein acceleration both enabled and disabled:
  **69 hits, 91 no-hits, zero unresolved and zero wrong scalar results** for
  this explicit representation. All 160 queries in each mode are independently
  certified at **1e-11 cm**: 158 exact rational Bernstein/ball proofs plus two
  exact support contact proofs. Earlier eligible intervals are excluded,
  including interior-origin cases; no-hits exclude the whole ray.
  CSV SHA-256:
  `fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723`.
- The two even contacts are proved roots: a06 is exactly `3/2^55` cm from
  its origin and a08 is `2+3/2^55` cm. The tiny positive a06 root is retained
  below the query tolerance. The generic exact support predicate has no bank-ID
  dispatch.
- Adversarial C++ controls and legacy compiled-surface tests pass. Controls
  cover minimum enclosure, curved seams, zero/coincident contact policy,
  tangent fallback, direction scaling, exhaustion, invalid options/arithmetic,
  competing normals, degenerate geometry, support axis/sign permutations,
  tiny contacts, exact dyadic carry/cancellation and far-point strict signs.
  Eight comparator controls and three Python representation tests also pass.

Tolerances refer to the ray parameter using the recorded binary64 normalized
direction components. Units are nominal cm; this does not assert exact real
normalization for arbitrary vectors. The decisive native seam uses (-1,0,0).

## Measured acceleration

An untrusted numerical proposal is accepted only after complete prefix exclusion,
strict interval endpoint signs, unique projection, strict derivative and the
distance/residual gates. Bernstein tensor bounds exclude outside prefixes;
fixed exact curve-point witnesses cover inside prefixes. Failure falls back to
the bounded ordered solver. Exact-zero interval identities separately improve
both modes.

Three clean fresh-process pairs (04/05, 10/11, 12/13) use the same binary,
geometry, rays and source identities, changing only the acceleration option:

| Mean per run | Enabled | Disabled |
|---|---:|---:|
| Sum of 160 distance-query times | 0.865648 s | 3.507429 s |
| Child process wall time | 1.547897 s | 4.032762 s |

This is **4.05x lower summed distance time** and **2.61x lower process wall
time** in this local observation. Paired distance-time ratios range from
0.2442 to 0.2484. Each enabled run certifies 66 queries through the accelerator.
All non-timing query fields match across replicates within each mode, allowing
reuse of the corresponding independently certified 04/05 scalar results.

Runs 06-09 are preserved and excluded because they overlapped the independent
Fraction verifier. These observations isolate the option in the final binary;
the earlier 24.946 s baseline sum includes other implementation differences.
This is not a comparison with native geometry throughput. See
`PERFORMANCE_AB.md` and `PERFORMANCE_PLAN.md`.

## Decisive evidence

| Evidence | What it establishes |
|---|---|
| `build-receipt-14.json`, build14/native-build04 logs | Successful bounded Release builds; unchanged 17 compiled input records and five executable/library outputs |
| `native-probe-03.jsonl`, `independent-native-region-exit.json` | Actual native surface/Region entry, exit, normal, sense and containment; independently bounded scalar errors |
| `frozen-offset-04/`, `frozen-offset-05/` | Both 160-query modes, execution provenance, normalized directions and costs |
| `independent-bank-qualified-04.json`, `independent-bank-qualified-05.json` | Complete independent scalar qualification at 1e-11 cm |
| `independent-bank-accelerated-04/`, `independent-bank-slab-05/`, support04/05 receipts | Per-query exact prefix/bracket/contact evidence |
| `final-acceptance.json`, `INDEPENDENT_REVIEW.md` | Separate Sol source challenge and verification of build, oracle, native and regression receipts |
| `offset-tests-08.txt`, `legacy-cpp-tests-03.txt`, Python test logs | Actual positive and failure-path controls |
| `PERFORMANCE_AB.md`, `performance-ab.json` | Three clean paired observations, identities, telemetry gaps and excluded observations |
| `PERFORMANCE_REVIEW.md`, `performance-review.json` | Separate Sol recalculation and identity checks; limited acceptance of the local A/B observation |

Build13 compiled while a residual-reporting correction changed an input. Its
receipt detects the change and is explicitly rejected for acceptance. Build14
replaced it with stable inputs. Historical receipts remain unchanged. Hashes
observe file identity; they are not cryptographic compilation attestation.

The report directory has a scoped Git `-text` attribute to preserve original
evidence bytes and their linked hashes. `publication-source-binding.json`
maps the 13 raw compiled source hashes to committed Git blobs and content
hashes. Two source files undergo only CRLF-to-LF normalization in Git; the
other 11 have identical bytes. Local CMake caches/build files remain identified
by the build receipt. This publication bookkeeping does not constitute a rebuild.

## Remaining limits

This is a constant-metric offset solid: constant circular tubes around regular
curves, or constant ellipses on admitted xy-planar curves. It is not the physical
rectangular WISTELL-D winding pack. The eight real coil031 rays are no-hits for
a diagnostic circular-offset payload and do not qualify physical pack hits.
Collections, variable radii/frames and unrestricted degenerate contacts are
outside this mode; unsupported queries fail closed.

Nine auxiliary normal queries remain blocked (`a00`, `w0` through `w7`).
All 160 have evaluate timing in the final runs, but those nine lack normal
timing and prevent a full point/normal usability claim. Their independently
proved scalar no-hits remain valid. Queries still allocate memory.

Native parameter-seam and Region success do not validate physical periodic
boundaries. No neutron/photon particle histories, periodic transport or material
physics qualification have run. The **80% native-throughput target remains
unmeasured and unqualified**.

The pre-existing swapped source-hash false-PASS path remains reproduced by the
checkpoint recheck and is outside this change. The strict comparator now rejects
NaN, infinity, duplicate keys, contradictory status/count fields, invalid or
changed frozen metadata and cross-representation comparisons.

No dependency was acquired, environment modified, SSH/remote job used or schedule
changed. Reproduction requires the hash-matched local analytic and coil031 HDF5
inputs named in the receipts; large source geometry is not duplicated in the PR.
The next steps and resource gates are in `CONTINUATION_HANDOFF.md`.
