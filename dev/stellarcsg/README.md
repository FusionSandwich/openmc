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
- conservative correctness-reference nearest-root search including sampled,
  sign-changing, and stationary/tangent candidates;
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
- cumulative radial first-wall/blanket/shield boundary generation;
- hash-bound multi-surface HDF5 output;
- layer-conformal hexahedral tally meshes generated from the same surface
  coefficients;
- HDF5 mesh metadata and legacy VTK export for ParaView;
- command-line analytic demonstration.

### Experimental OpenMC adapter

An opt-in CMake injector adds a `periodic-spline` surface to a dedicated OpenMC
build without editing the root OpenMC source files. It exercises the real
OpenMC `Surface` parser and the C++ `evaluate`, `distance`, `normal`, bounding
box, and HDF5-summary interfaces.

The adapter currently uses the expensive reference root search. It proves the
integration route; it is not yet suitable for production transport or speed
claims.

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

## Experimental OpenMC adapter build

```bash
cmake -S . -B build/openmc-stellarcsg \
  -DCMAKE_BUILD_TYPE=Release \
  -DOPENMC_BUILD_TESTS=OFF \
  -DOPENMC_USE_OPENMP=ON \
  -DSTELLARCSG_BUILD_OPENMC_ADAPTER_TESTS=ON \
  -DCMAKE_PROJECT_INCLUDE="$PWD/dev/stellarcsg/openmc_adapter/enable.cmake"
cmake --build build/openmc-stellarcsg \
  --target stellarcsg_openmc_adapter_tests --parallel
ctest --test-dir build/openmc-stellarcsg \
  -R stellarcsg_openmc_adapter_tests --output-on-failure
```

Python XML wrapper:

```python
from stellarcsg.openmc_surface import PeriodicSplineSurface

surface = PeriodicSplineSurface(
    data_file="compiled_geometry.h5",
    dataset="/surfaces/plasma",
    content_id="sha256:...",
    solver="reference",
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
- The surface-grid compiler performs a useful first star-shapedness check but
  does not yet provide a formal global proof of admissibility.
- The root search is a correctness reference and cannot certify that an
  arbitrarily narrow unsampled root is absent.
- Normal-distance offsets are not yet compiled from ParaStell/jax-sbgeom target
  surfaces; the present build is geometric-radial.
- Swept finite-build magnet CSG is still deferred. Magnet tally meshes will be
  added after the coil surface contract passes.
- No matched end-to-end OpenMC custom-CSG versus DAGMC/Embree benchmark has
  been completed.
- Stellarator-symmetry boundary conditions are separate from ordinary
  rotational periodicity and remain deferred.

See [`docs/EXECUTION_STATUS.md`](docs/EXECUTION_STATUS.md) for the tests
actually executed in this tranche.

Do not use this branch for production neutronics until the adversarial-ray,
matched-geometry, and transport-validation gates in
[`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) pass.
