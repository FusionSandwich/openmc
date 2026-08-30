# StellarCSG implementation status

Updated: 2026-08-30

Repository: `FusionSandwich/openmc`

Branch: `codex/stellarcsg-native-csg-foundation-20260828`

Starting branch head: `9adb7c4bd8a97c88f4a4e614b80637d6043c202b`

Scientific status: experimental research implementation; not qualified for
production transport.

## Accepted milestones

### Handoff recovery and input provenance

- Recovered the last byte-verifiable v2 source bundle after establishing that
  the newer committed ZIP and patch were truncated.
- Retained hash-verified WISTELL-D VMEC, coil, blanket-boundary,
  magnet-boundary, and neutron-wall-loading inputs.
- Retained the pinned public ParaStell VMEC and coil examples as a distinct
  generic case. They are not labeled as WISTELL-D.

### Native periodic-spline OpenMC integration

- Root build option `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG`, default `OFF`.
- Native `SurfacePeriodicSpline` parser registration, evaluate, nearest-positive
  reference distance, normal, conservative bounding box, and summary-HDF5
  fields.
- Python `PeriodicSplineSurface` construction, XML round trip, summary-HDF5
  reconstruction, relative coefficient-file path preservation, centimetre unit
  contract, and explicit transform rejection.
- External HDF5 schema and surface-type checks.
- Canonical SHA-256 over canonical metadata bytes followed by little-endian
  float64 coefficient payloads, verified on C++ read and write.
- No Python callbacks or new mandatory runtime dependency in particle tracking.

Qualification evidence for this milestone:

| Check | Result |
|---|---|
| Standalone GCC Release CTest | 2 passed, 0 failed |
| Full OpenMC build, feature disabled | build passed |
| Full OpenMC build, feature enabled | build passed |
| Native OpenMC C++ periodic-surface test | 1 passed, 0 failed |
| Native OpenMC Python periodic-surface tests | 4 passed, 0 failed |
| Standalone Python package tests | 12 passed, 1 skipped |
| Python syntax compilation | passed |

The standalone Python skip is the pre-existing optional OpenMC import check;
the native OpenMC Python test was run separately with import-only shims for the
locally unavailable compiled `endf` record helper and Linux `libopenmc` binary.
No dependency was installed or modified for that test.

## Active work

- Layered nearest-root solver, specialized paths, interval certification, and
  deterministic adversarial oracle campaign.
- Plasma/normal-offset layer fitting and geometry fidelity qualification.
- Rotation-minimizing swept-spline coil primitive.
- End-to-end OpenMC transport, DAGMC comparison, geometry-debug, and clean-clone
  reproduction.

## Unqualified or not implemented

- The currently integrated distance path is the broad reference oracle. It is
  correct only within its tested cases and is not a certified production fast
  path.
- No WISTELL-D plasma or blanket fit has yet passed the requested independent
  fidelity gates.
- No native swept-coil OpenMC surface is yet present.
- No matched DAGMC model, OpenMC particles/s result, transport tally comparison,
  or production-scale ray campaign has yet been accepted.

These items must remain reported as incomplete until their retained evidence is
generated and reviewed.
