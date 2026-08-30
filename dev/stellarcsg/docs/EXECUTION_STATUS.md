# StellarCSG execution status

**Status date:** 2026-08-30  
**Repository:** `FusionSandwich/openmc`  
**Branch:** `codex/stellarcsg-native-csg-foundation-20260828`  
**Classification:** `LIMITED_RESEARCH_PROTOTYPE_ONLY`

## Work completed in the first execution tranche

The first bounded development tranche has been implemented rather than merely
specified. The branch now contains a standalone C++ geometry kernel, a Python
surface compiler and mesh generator, an opt-in OpenMC adapter, automated tests,
local run scripts, CI definitions, schemas, and this evidence record.

### Mathematical and C++ kernel

Implemented:

- periodic cubic splines for the moving toroidal reference axis;
- a periodic bicubic radial surface with
  `F(x,y,z) = rho - rho_surface(theta,phi)`;
- analytic gradient and outward normal;
- finite conservative bounds derived from the spline control hull;
- a deliberately conservative correctness-reference root search;
- versioned HDF5 surface coefficients and cross-language loading;
- standalone inspection and microbenchmark executables.

The root search is intentionally not yet presented as production-fast or
mathematically certified. It samples and refines intervals and includes
stationary/tangent candidates, but a later gate must replace or certify this
algorithm with patch bounds or interval methods.

### Generic Python compiler

Implemented:

- analytic torus and helically perturbed fixtures;
- compilation of an arbitrary sampled periodic XYZ surface grid into a radial
  single-chart representation;
- per-toroidal-slice reparameterization to geometric poloidal angle;
- periodic cardinal cubic coefficient generation;
- content-hashed HDF5 surface collections;
- cumulative radial reactor layers;
- conformal hexahedral meshes generated from exactly the same coefficients;
- HDF5, legacy VTK, and optional MOAB H5M output;
- an OpenMC mesh-tally helper and a CLI demonstration.

### Experimental OpenMC integration

Implemented and compiled against the real OpenMC source:

- opt-in `periodic-spline` surface registration;
- XML parsing from a hash-bound external HDF5 coefficient group;
- OpenMC `evaluate`, `distance`, `normal`, bounding-box, and statepoint-summary
  methods;
- an adapter CTest that exercises the real OpenMC parser and surface object.

The integration is isolated through `CMAKE_PROJECT_INCLUDE`. A normal OpenMC
build does not receive the custom surface.

## Verification executed locally

| Gate | Result |
|---|---:|
| Standalone C++ CTest | 2/2 passed |
| Python pytest | 12 passed, 1 skipped |
| Editable package build | passed |
| `stellarcsg demo` | passed |
| Python-written HDF5 read by C++ inspector | passed |
| Experimental OpenMC adapter CTest | 1/1 passed |
| Demo tally-mesh element volumes | all positive |

The skipped Python test requires importing the full OpenMC Python package, which
was not installed with all runtime dependencies in the isolated execution
environment. The C++ adapter itself was built and tested successfully against
the real OpenMC library.

The latest local microbenchmark measured approximately 214 ns per surface
evaluation and 199 ns per normal evaluation on the execution host. These are
microbenchmarks only and are not evidence of an OpenMC or DAGMC speedup.

## What this branch can be used for now

A local user can now:

1. compile and test the standalone geometry kernel;
2. generate a hash-bound analytic helical stellarator and nested radial build;
3. generate a conformal local-tally mesh without CAD;
4. inspect the result in ParaView;
5. verify that C++ reads the Python-generated geometry identically;
6. build the opt-in OpenMC adapter and run its parser/surface test;
7. use the Python API to compile a periodic sampled XYZ plasma surface.

## What is not yet authorized

Do not use the branch for production neutronics or scientific magnet-damage
claims. In particular, the following gates remain open:

- adversarial nearest-root certification;
- non-star-shaped/multi-chart fallback;
- swept finite-build magnet CSG;
- coil-local arc/u/v tally meshes;
- VMEC/MAKEGRID end-user import commands;
- full fixed-source OpenMC transport with the custom surface;
- matched geometry and neutronics comparison against DAGMC/Embree;
- end-to-end speed and memory comparison;
- authoritative WISTELL-D magnet spectra.

## Next critical path

The next implementation tranche should proceed in this order:

1. persist a large adversarial ray corpus and add patch/interval root bounds;
2. qualify the radial chart on at least three genuinely different open
   stellarator surfaces;
3. implement the swept-coil surface and arc/u/v mesh together;
4. run the first OpenMC vacuum-navigation and analytic-shell transport tests;
5. generate a matched DAGMC reference from the same coefficient source;
6. measure end-to-end speed only after geometry accuracy is matched.
