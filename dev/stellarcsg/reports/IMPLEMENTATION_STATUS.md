# StellarCSG implementation status

Updated: 2026-08-30

Repository: `FusionSandwich/openmc`

Branch: `codex/stellarcsg-native-csg-foundation-20260828`

Starting branch head: `9adb7c4bd8a97c88f4a4e614b80637d6043c202b`

Scientific status: experimental research implementation; not qualified for
production transport.

## Accepted native milestones

### Provenance and compiler inputs

- Restored the byte-verifiable v2 implementation after proving the newer
  handoff archive was truncated.
- Retained hash-verified authoritative WISTELL-D VMEC, coil, blanket-boundary,
  magnet-boundary, and neutron-wall-loading inputs.
- Retained the pinned ParaStell public VMEC and coil examples as a separate
  generic case; they are never labeled as WISTELL-D.

### Native periodic-spline OpenMC surface

- Root option `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG`, default `OFF`.
- Native evaluation, normal, conservative bound, nearest-positive distance,
  parser registration, Python/XML/summary-HDF5 construction, external HDF5
  loading, canonical SHA-256 verification, relative paths, centimetre unit
  contract, and explicit transform rejection.
- Exact circular-torus specialization and shaped-axisymmetric specialization
  selected with scale-aware floating-point tests.
- Independent global reference oracle and solver-path/fallback diagnostics.
- Exact-torus regression cases include tangencies, repeated roots, coincident
  starts, four roots, interval boundaries, seams, close root pairs, and non-unit
  directions.

### Geometry compiler and fidelity

- Exact torus, shaped Miller-like, and synthetic helical analytic cases pass
  independent 197,633-point fidelity checks.
- Authoritative WISTELL-D LCFS is `PASS_SINGLE_CHART`: maximum Cartesian error
  0.0343815 cm, RMS 0.00241720 cm, and volume relative error -7.11035e-8.
- Six WISTELL-D cumulative physical-normal boundaries were accepted through the
  vessel; fold, layer-intersection, radius, and Jacobian checks are active.
- The public ParaStell VMEC case is honestly rejected as `REJECT_THETA_FOLD`.

### Native swept-spline OpenMC surface

- MAKEGRID filament parsing, equal-arc periodic cubic centerlines,
  rotation-minimizing frames, distributed closure twist, circular/elliptical
  sections, local coordinates, content IDs, and HDF5 payloads.
- Native parser/Python/XML/HDF5 integration, normals, conservative bounds, and
  explicit transform rejection behind the same experimental option.
- Exact circular coil delegates to the exact torus kernel.
- Forty-eight WISTELL-D and forty public ParaStell coils compile with positive
  curvature and clearance margins under the declared qualification sections.

### Retained OpenMC benchmark

- Collisionless/minimal-physics Tier 2, one thread, 1,000,000 histories per
  repetition, one warm-up plus five measured runs, fixed seed 918273645.
- Built-in torus median: 904,275 histories/s.
- Periodic exact torus median: 376,008 histories/s (0.4158x built-in).
- Built-in coil-equivalent torus median: 929,676 histories/s.
- Swept exact circular coil median: 384,171 histories/s (0.4132x built-in).
- All measured and geometry-debug runs returned normally with zero lost
  particles and no reported overlap or geometry error.
- The 1.5x periodic-torus and preferred 2x swept-coil performance targets were
  not met; these exact-geometry candidates were about 2.40x and 2.42x slower
  than their built-in baselines by active histories/s.

### Same-source exact-torus DAGMC comparison

- Built this branch once with DAGMC 3.2.4 and StellarCSG enabled inside the
  pinned `parastell-openmc:0.16.0` image; all comparison cases use that binary.
- Coarse/fine meshes contain 8,682/52,030 triangles and have sampled maximum
  surface errors of 1.473345/0.236576 cm.
- Periodic spline median: 210,111 histories/s; coarse DAGMC: 67,852.0; fine
  DAGMC: 57,496.7. The native periodic surface is 3.0966x/3.6543x faster.
- All measured transports had zero lost particles and leakage 1.0.
- DAGMC watertightness and dedicated overlap tools pass, but OpenMC `-g`
  reports the torus volume against its implicit complement. DAGMC remains
  qualified for retained timing evidence, not for a clean OpenMC debug gate.

## Validation evidence

| Check | Result |
|---|---|
| Standalone GCC Release CTest | 2 passed, 0 failed |
| Standalone Python package tests | 13 passed, 1 expected optional-import skip |
| Native OpenMC Python surface tests | 6 passed, 0 failed |
| Full OpenMC feature-disabled build | passed before final evidence commit; final rebuild recorded separately |
| Full OpenMC feature-enabled build | passed before final evidence commit; final rebuild recorded separately |
| Native OpenMC C++ StellarCSG test | 1 passed, 0 failed |
| Full native OpenMC C++ CTest invocation | 12 passed; 1 optional MCPL test explicitly skipped and counted failed by CTest |
| Ten-million exact-torus ray campaign | zero missed, false, or wrong-nearest roots; 4,099 adversarial rays also passed |
| Joint DAGMC + StellarCSG OpenMC build | passed |
| DAGMC exact-torus measured transport | four cases x five measured repetitions passed, zero lost particles |
| DAGMC `check_watertight` / `overlap_check` | passed both meshes |
| DAGMC OpenMC `-g` | failed: explicit volume versus implicit complement |
| Clang ASan/UBSan | blocked: installed Clang lacks ASan runtime archives |

## Not accepted

- Generic periodic stellarator root certification beyond the broad oracle.
- Patch BVH / interval-certified generic swept-coil distance solving.
- Ten-million-ray generic swept-coil oracle campaign.
- Native OpenMC shaped-axisymmetric, helical, ParaStell, WISTELL-D blanket, or
  full WISTELL-D coil transport models.
- Tier 3 14.1 MeV materialized transport, tallies, stochastic-volume closure,
  native overlap plots, and error-budget decomposition.
- DAGMC comparisons beyond the exact circular-torus coarse/fine case.
- Clean-clone reproduction of the final pushed evidence commit.

See `FINAL_TECHNICAL_BOUNDARIES.md` for the precise supported envelope and
`DAGMC_COMPARISON.md` for the dependency blocker and smallest next action.
