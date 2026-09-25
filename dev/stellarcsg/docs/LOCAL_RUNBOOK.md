# Local build and test runbook

## Supported development route

The most reproducible route on a Windows workstation is WSL2 with Ubuntu 24.04.
Native Windows may work with Visual Studio, CMake, HDF5, and Python, but it has
not yet been qualified by this branch.

## Clone and select the isolated branch

```bash
git clone https://github.com/FusionSandwich/openmc.git
cd openmc
git switch codex/stellarcsg-native-csg-foundation-20260828
git submodule update --init --recursive
```

Verify that no production worktree is being reused:

```bash
git status --short --branch
git worktree list
```

## Ubuntu/WSL dependencies

```bash
sudo apt update
sudo apt install -y \
  build-essential cmake ninja-build git \
  libhdf5-dev zlib1g-dev libpng-dev \
  python3 python3-venv python3-pip
```

Create a local environment:

```bash
python3 -m venv .venv-stellarcsg
source .venv-stellarcsg/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e 'dev/stellarcsg[test]'
```

A Conda environment is also provided:

```bash
conda env create -f dev/stellarcsg/environment.yml
conda activate stellarcsg-dev
python -m pip install -e 'dev/stellarcsg[test]' --no-deps
```

## Fast validation

```bash
./dev/stellarcsg/scripts/run_local_validation.sh
```

Expected gates:

1. standalone C++ configure/build succeeds;
2. two CTest executables pass;
3. Python test suite passes;
4. analytic demo writes a hash-bound geometry file and positive-volume tally
   mesh;
5. the geometry microbenchmark emits JSON;
6. the C++ inspector reads the Python-generated HDF5 and evaluates the same
   surface.

Artifacts are written below `build/stellarcsg-local-validation/` and are not
intended for Git.

## Full experimental OpenMC adapter validation

```bash
./dev/stellarcsg/scripts/run_local_validation.sh --openmc-adapter
```

This compiles most of OpenMC and can take several minutes. The adapter is
injected only into that build directory. A normal OpenMC build is unaffected.

Manual equivalent:

```bash
cmake -S . -B build/openmc-stellarcsg \
  -G Ninja \
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

## Inspect the generated geometry and mesh

```bash
stellarcsg demo \
  --output-dir build/stellarcsg-demo \
  --extent field-period
```

Open `build/stellarcsg-demo/tally_mesh.vtk` in ParaView. The cell fields identify
shell, radial, poloidal, and toroidal bins.

Inspect HDF5:

```bash
h5ls -r build/stellarcsg-demo/compiled_geometry.h5
h5ls -r build/stellarcsg-demo/tally_mesh.h5
build/stellarcsg-local-validation/cpp/stellarcsg_inspect_surface \
  build/stellarcsg-demo/compiled_geometry.h5 /surfaces/plasma 600 0 0
```

Optional OpenMC-compatible MOAB tally mesh:

```python
from stellarcsg import write_moab_h5m
write_moab_h5m("build/stellarcsg-demo/tally_mesh.h5m", mesh)
```

The optional H5M path requires PyMOAB from a MOAB-enabled environment. The
standalone mathematics and HDF5/VTK mesh tests do not require MOAB.


## Using a sampled custom plasma surface

The Python API accepts `xyz_cm` with shape `(n_theta, n_phi, 3)` and a uniform
`toroidal phi` vector covering one field period without duplicating the end
point:

```python
from stellarcsg.surface import PeriodicRadialSurfaceData

surface = PeriodicRadialSurfaceData.from_surface_grid(
    name="plasma",
    xyz_cm=xyz,
    phi=phi,
    n_field_periods=nfp,
    axis_r_cm=axis_r,
    axis_z_cm=axis_z,
)
```

The compiler reparameterizes each slice onto geometric polar angle. It rejects
nonunique angular samples and nonpositive radii. More aggressive topology and
Jacobian qualification remains a planned gate.

## Troubleshooting

### CMake cannot find HDF5

Use the Conda environment or provide:

```bash
cmake ... -DHDF5_ROOT="$CONDA_PREFIX"
```

The standalone geometry kernel can still be compiled without file I/O using:

```bash
-DSTELLARCSG_ENABLE_HDF5=OFF
```

### Python build isolation tries to access the internet

After installing local dependencies, use:

```bash
python -m pip install -e 'dev/stellarcsg[test]' \
  --no-build-isolation --no-deps
```

### OpenMC adapter target is absent

Delete that build directory and configure again with the exact
`CMAKE_PROJECT_INCLUDE` argument. Do not reuse a normal OpenMC CMake cache.

### A surface produces a missed or ambiguous ray

Do not loosen tolerances until the failing origin, direction, and coefficient
file have been preserved. The next development phase will add a permanent
adversarial HDF5 corpus and interval/patch certification.
