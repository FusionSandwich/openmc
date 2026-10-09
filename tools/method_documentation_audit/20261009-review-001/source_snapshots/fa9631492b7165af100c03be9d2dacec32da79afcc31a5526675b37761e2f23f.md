# StellarCSG: native stellarator CSG research inside the OpenMC fork

This subtree contains an isolated, runnable implementation of the first stages
of the native stellarator CSG development plan. It is intentionally developed
on `FusionSandwich/openmc` branch
`codex/stellarcsg-native-csg-foundation-20260828`; there is no pull request and
ordinary OpenMC builds are unchanged.

The long-term objective is a CAD-free workflow in which a user supplies a
plasma/equilibrium surface and coil centerlines, then receives native smooth
OpenMC CSG surfaces plus companion meshes for spatially resolved magnet
spectra. The current code is a **research prototype**, not a production
geometry kernel.

## Implemented in this milestone

### Standalone C++ kernel

- periodic one-dimensional cubic B-splines for moving magnetic/reference axes;
- periodic bicubic radial surface field for
  \(F(x,y,z)=\rho-\rho_s(\theta,\phi)\);
- analytic gradient and outward normal;
- finite bounding box based on the B-spline convex hull;
- layered nearest-root search with exact circular-torus and shaped-axisymmetric
  paths plus an independently coded broad reference oracle;
- periodic swept cubic centerlines with rotation-minimizing frames and circular
  or elliptical cross sections;
- versioned HDF5 coefficient reader/writer with content-identity checking;
- analytic torus, shaped-axisymmetric, helical, moving-axis, tangent, and HDF5
  round-trip tests;
- standalone geometry microbenchmark.

### Generic Python geometry compiler

- analytic torus/helical-surface constructor;
- compilation from a periodic sampled XYZ surface grid without CAD;
- reparameterization from an arbitrary input poloidal parameter to geometric
  polar angle;
- periodic interpolation to cardinal cubic B-spline coefficients;
- VMEC and MAKEGRID filament readers;
- cumulative physical-normal first-wall/blanket/shield/vessel boundaries with
  coordinate-fold, intersection, radius, and Jacobian rejection;
- hash-bound multi-surface HDF5 output;
- layer-conformal hexahedral tally meshes generated from the same surface
  coefficients;
- HDF5 mesh metadata and legacy VTK export for ParaView;
- command-line analytic demonstration.

### Experimental OpenMC integration

The root build option `OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG`, disabled by
default, adds native `periodic-spline` and `swept-spline` surfaces. Both
exercise the real OpenMC parser and C++ evaluate, distance, normal, bounding
box, external-HDF5, and summary-HDF5 interfaces.

The implementation remains a research candidate: the generic periodic and
swept paths retain expensive reference searches and are not yet suitable for
production transport claims.

## One-command local validation

Linux or WSL2:

```bash
./dev/stellarcsg/scripts/run_local_validation.sh
```

Add the full experimental OpenMC adapter build:

```bash
./dev/stellarcsg/scripts/run_local_validation.sh --openmc-adapter
```

Windows PowerShell with a working CMake/C++/HDF5 toolchain:

```powershell
./dev/stellarcsg/scripts/run_local_validation.ps1
```

WSL2 is presently the simplest supported Windows route. See
[`docs/LOCAL_RUNBOOK.md`](docs/LOCAL_RUNBOOK.md).

## Manual standalone build

```bash
cmake -S dev/stellarcsg -B build/stellarcsg \
  -DCMAKE_BUILD_TYPE=Release \
  -DSTELLARCSG_ENABLE_HDF5=ON \
  -DSTELLARCSG_BUILD_TESTS=ON \
  -DSTELLARCSG_BUILD_BENCHMARKS=ON \
  -DSTELLARCSG_BUILD_TOOLS=ON
cmake --build build/stellarcsg --parallel
ctest --test-dir build/stellarcsg --output-on-failure
build/stellarcsg/stellarcsg_surface_benchmark
build/stellarcsg/stellarcsg_inspect_surface \
  build/stellarcsg-demo/compiled_geometry.h5 /surfaces/plasma 600 0 0
```

## Python compiler and mesh demonstration

```bash
python -m pip install -e 'dev/stellarcsg[test]'
pytest -q dev/stellarcsg/python/tests
stellarcsg demo --output-dir build/stellarcsg-demo
```

The demonstration produces a cross-language-readable coefficient file and a
companion local-tally mesh:

```text
build/stellarcsg-demo/
├── compiled_geometry.h5
├── tally_mesh.h5
├── tally_mesh.vtk
└── validation_report.json
```

## Experimental OpenMC build

```bash
cmake -S . -B build/openmc-stellarcsg \
  -DCMAKE_BUILD_TYPE=Release \
  -DOPENMC_BUILD_TESTS=ON \
  -DOPENMC_USE_OPENMP=ON \
  -DOPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=ON
cmake --build build/openmc-stellarcsg --parallel
ctest --test-dir build/openmc-stellarcsg -R stellarcsg --output-on-failure
```

Python XML wrapper:

```python
from stellarcsg.openmc_surface import PeriodicSplineSurface

surface = PeriodicSplineSurface(
    data_file="compiled_geometry.h5",
    dataset="/surfaces/plasma",
    content_id="sha256:...",
    solver="layered",
)
cell.region = -surface
```

The OpenMC executable used with this XML must be the adapter-enabled build.

When PyMOAB is installed, `stellarcsg.write_moab_h5m(...)` exports the same
hexahedral mesh for an OpenMC `UnstructuredMesh`/`MeshFilter` tally. The generic
HDF5 and VTK paths remain available without MOAB.

Automatic standalone CI is defined in `.github/workflows/stellarcsg-ci.yml`.
The full adapter build is deliberately manual because it compiles most of
OpenMC.

## Current hard limitations

- The implemented plasma/layer representation is a single radial chart about a
  periodic reference axis. It is not valid for every possible toroidal surface.
- The compiler rejects surfaces outside its single-chart envelope; it does not
  implement a general multi-chart fallback.
- The exact-torus campaign does not certify arbitrary fitted stellarators.
- The generic swept path has no patch BVH or interval-certified local solve and
  has not passed a 10-million-ray oracle campaign.
- Nested swept winding packs, coolant regions, superellipses, and rounded
  rectangles remain deferred.
- No matched end-to-end OpenMC custom-CSG versus DAGMC/Embree benchmark has
  been completed.
- Stellarator-symmetry boundary conditions are separate from ordinary
  rotational periodicity and remain deferred.

See [`reports/IMPLEMENTATION_STATUS.md`](reports/IMPLEMENTATION_STATUS.md) and
[`reports/FINAL_TECHNICAL_BOUNDARIES.md`](reports/FINAL_TECHNICAL_BOUNDARIES.md)
for the current evidence and precise boundaries. The older
[`docs/EXECUTION_STATUS.md`](docs/EXECUTION_STATUS.md) records the first tranche.

Do not use this branch for production neutronics until the adversarial-ray,
matched-geometry, and transport-validation gates in
[`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) pass.
