# StellarCSG reference kernel (isolated OpenMC-fork experiment)

This directory is the first implementation slice for the native tokamak / stellarator CSG development plan. It is intentionally self-contained inside `FusionSandwich/openmc` and is **not wired into OpenMC's production build, Python API, XML parser, or transport kernel yet**.

## Isolation contract

- Development branch: `codex/stellarcsg-native-csg-foundation-20260828`
- Frozen starting commit: `9a62e431d3101799e6179a6d0cf3b37440062e23`
- Repository: `FusionSandwich/openmc` only
- No pull request or draft pull request
- No changes to `develop`, `master`, upstream `openmc-dev/openmc`, or any other repository
- No device-specific generated C++ and no CAD/DAGMC dependency in this kernel

The branch shares the frozen OpenMC history because the eventual surface classes must integrate with OpenMC, but all StellarCSG changes are confined to this branch and this subtree until bounded correctness gates pass.

## What this first slice implements

1. A standalone C++17 library and CTest target.
2. A uniform tensor-product periodic cubic B-spline coefficient field for
   \(\rho_s(\theta,\varphi)\), including analytical \(\partial/\partial\theta\)
   and \(\partial/\partial\varphi\).
3. The generic radial implicit-surface coordinate map
   \[
   F(x,y,z)=\rho-\rho_s(\theta,\varphi),
   \]
   with analytical Cartesian gradient and normal.
4. A deliberately conservative finite-interval reference root search that:
   - scans the complete bounding-box interval;
   - refines sign-changing roots by bisection;
   - searches derivative stationary points for tangent roots;
   - returns the nearest detected positive root;
   - records diagnostic counters.
5. Tests for:
   - simple, multiple, tangent, and absent scalar roots;
   - spline periodicity and analytical derivatives;
   - an exact circular torus;
   - a non-elliptical shaped axisymmetric surface;
   - a non-axisymmetric helical surface;
   - coincident and grazing ray behavior;
   - 512 exact torus radial crossings, 12 off-grid tangent crossings, and 200
     exact synthetic-helical radial crossings;
   - analytical surface gradients against finite differences.

## Build and test

From the repository root:

```bash
cmake -S dev/stellarcsg -B build/stellarcsg -DSTELLARCSG_BUILD_TESTS=ON
cmake --build build/stellarcsg --parallel
ctest --test-dir build/stellarcsg --output-on-failure
```

The standalone target has no dependency on OpenMC, HDF5, DAGMC, MOAB, libMesh, or nuclear data.

## Important limitation

The current root search is a **reference prototype, not a certified production ray-intersection algorithm**. Uniform refinement plus stationary-point checks is sufficient for the bounded exact-torus, shaped-axisymmetric, and synthetic-helical tests included here, but it cannot prove that an arbitrarily narrow root was absent. Before OpenMC transport integration, the project still needs conservative patch bounds or interval methods, a permanent adversarial ray corpus, and the preregistered zero-wrong-nearest-root gate.

## Next bounded implementation steps

1. Add interval / patch bounds and a slower independently coded oracle.
2. Add randomized and adversarial ray fixtures with retained failing seeds.
3. Add coefficient-file serialization only after the schema is frozen.
4. Implement the swept-coil lane in a separate subtree/module on the same branch.
5. Integrate a thin `Surface` wrapper only after the standalone correctness gates pass.

The project plan's separation between smooth native CSG transport and a later companion tally mesh remains unchanged. The tally mesh is not part of this first commit.
