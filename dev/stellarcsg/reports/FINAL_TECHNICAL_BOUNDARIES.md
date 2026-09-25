# Final technical boundaries

Updated: 2026-08-30

This branch contains an opt-in experimental research implementation. It is not
qualified for production neutronics.

## Supported and exercised

- Generic external coefficient payloads; changing devices does not require
  generated device-specific C++ or an OpenMC rebuild.
- `PeriodicSplineSurface` evaluation, normal, conservative bounding box,
  XML/Python/summary-HDF5 round trips, canonical content verification, relative
  paths, centimetre enforcement, and transform rejection.
- Exact circular-torus nearest-root specialization, including non-unit rays,
  coincident starts, tangencies, repeated roots, and four-root rays.
- Scale-aware shaped-axisymmetric detection and a conservative subdivision /
  safeguarded-Newton path with global-reference fallback.
- General periodic surfaces through the independent broad reference solver.
- VMEC compilation when each toroidal slice admits the supported single
  geometric-angle chart.
- Cumulative physical-normal layers with fold, intersection, radius, and
  Jacobian rejection.
- Periodic cubic swept centerlines, equal-arc parameterization,
  rotation-minimizing frames with distributed closure twist, and circular or
  elliptical sections.
- Native OpenMC `SweptSplineSurface` parsing, Python/XML/HDF5 construction,
  content verification, normal, local coordinates, and conservative bounds.
- Exact circular swept coils delegated to the exact torus specialization.

## Rejected or intentionally unsupported

- VMEC surfaces with geometric-theta or toroidal coordinate folds. The retained
  ParaStell public example is rejected as `REJECT_THETA_FOLD`.
- Surfaces whose fitted chart crosses `R=0`, has a nonpositive admissibility
  margin, or violates the declared fit tolerance.
- OpenMC transforms on either experimental surface.
- Frenet-Serret as the accepted coil frame.
- Swept superellipses, rounded rectangles, coolant channels, nested winding
  packs, and overlapping/self-intersecting coils.
- Stellarator half-module symmetry transformations.

## Important qualification limits

- The 10-million-ray periodic campaign covers the exact circular-torus path;
  it is not a certification of arbitrary fitted stellarator surfaces.
- The generic swept distance implementation uses a global dense centerline
  search with scalar refinement. It does not yet implement the requested patch
  BVH plus interval-certified local solve.
- No 10-million-ray swept-coil oracle campaign has been accepted.
- The retained OpenMC timings are collisionless/minimal-physics Tier 2 models.
  They are not 14.1 MeV materialized Tier 3 transport and contain no material
  tallies.
- Peak RSS, CPU time, first-batch timing, geometry-kernel fraction,
  distance-calls/history, and general-path fallback frequency were unavailable
  without additional instrumentation or tooling and are reported as such.
- No stochastic volume calculation, native cell-overlap plot, shaped/helical
  OpenMC timing, full WISTELL-D transport, or tally closure is accepted.
- A same-lineage exact-torus DAGMC coarse/fine convergence and matched speed
  comparison exists. Independent DAGMC watertightness and overlap checks pass,
  but OpenMC `-g` reports the explicit volume against the implicit complement;
  no other DAGMC geometry is accepted.
- Clang is installed in OpenMC-Dev-D, but its ASan runtime archives are absent,
  so the requested Clang ASan/UBSan build is environment-blocked at the compiler
  smoke link.

The build option `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG` remains `OFF` by
default. Promotion requires resolving the limits above and independently
reviewing the solver mathematics and retained evidence.
