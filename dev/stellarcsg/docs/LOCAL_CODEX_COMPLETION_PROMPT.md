# Local Codex execution prompt — complete and qualify StellarCSG in the isolated OpenMC fork

You are the implementation, verification, benchmark, and repository owner for the remaining StellarCSG work.

## Non-negotiable repository boundary

Work only in the user's fork and only on the existing isolated branch:

```text
Repository: FusionSandwich/openmc
Branch: codex/stellarcsg-native-csg-foundation-20260828
```

Do not modify `develop`, `master`, any other branch, `openmc-dev/openmc`, or any unrelated repository. Do not open a pull request or draft pull request. Push every accepted code change, test, retained input manifest, benchmark result, and report directly to the isolated branch in logical commits.

The branch intentionally contains an experimental implementation under `dev/stellarcsg/`. The root OpenMC integration must remain opt-in and disabled by default until all bounded gates pass.

## Initial checkout and audit

Execute, do not merely describe:

```bash
git clone https://github.com/FusionSandwich/openmc.git openmc-stellarcsg
cd openmc-stellarcsg
git fetch --all --tags --prune
git switch codex/stellarcsg-native-csg-foundation-20260828
git pull --ff-only origin codex/stellarcsg-native-csg-foundation-20260828
git status --short --branch
git log --oneline --decorate -20
```

Record the starting head in:

```text
dev/stellarcsg/reports/LOCAL_CODEX_STARTING_STATE.json
```

Before editing, read at minimum:

```text
AGENTS.md
dev/stellarcsg/README.md
dev/stellarcsg/implementation_manifest.json
dev/stellarcsg/docs/MATHEMATICAL_CONTRACT.md
dev/stellarcsg/docs/MILESTONE_PERIODIC_AXIS_OPENMC_ADAPTER_REPORT.md
dev/stellarcsg/docs/NORMAL_DISTANCE_LAYER_COMPILER.md
dev/stellarcsg/docs/PAPER_REVIEW_AND_ADOPTION_NOTES.md
dev/stellarcsg/openmc_adapter/INTEGRATION.md
dev/stellarcsg/openmc_adapter/openmc_periodic_spline.patch
```

Run the current standalone baseline before changing it:

```bash
cmake -S dev/stellarcsg -B build/stellarcsg-baseline \
  -DCMAKE_BUILD_TYPE=Release \
  -DSTELLARCSG_BUILD_TESTS=ON
cmake --build build/stellarcsg-baseline --parallel
ctest --test-dir build/stellarcsg-baseline --output-on-failure
PYTHONPATH=dev/stellarcsg/python \
  python -m pytest -q dev/stellarcsg/tests/python
```

Do not continue from a failing baseline without first classifying the failure as code, environment, or stale artifact and committing a repair or a precise blocker report.

## Acquire the correct geometry inputs

Clone these repositories next to the OpenMC checkout, at explicitly recorded commits:

```bash
cd ..
git clone https://github.com/FusionSandwich/wistell-d-openmc.git
git clone https://github.com/FusionSandwich/parastell.git
git clone https://github.com/FusionSandwich/blanket.git
```

Use the authoritative WISTELL-D files from `FusionSandwich/wistell-d-openmc/inputs/wistell_d/` or an exact byte-identical source. The expected roles are:

```text
wout_wistell-d.nc       VMEC equilibrium
coils.wistell-d          WISTELL-D coil filaments
blanket_boundary.npy     452-point blanket-boundary field
magnet_boundary.npy      452-point magnet-boundary field
nwl.npy                  452-point neutron-wall-loading field
```

Verify hashes against the live `wistell_openmc.reference.REFERENCE_FILES` mapping and the WISTELL-D source-contract records before copying. Never substitute ParaStell's generic `examples/wout_vmec.nc` and never label a public example as WISTELL-D.

Copy the verified test inputs into:

```text
dev/stellarcsg/test_data/wistell_d/
```

Add a manifest containing source repository, source commit, original path, copied path, bytes, SHA-256, device field periods, modeled extent, and qualification status. Commit the inputs if repository size permits. For a file that must Git LFS, configure and verify LFS on this branch. If a large qualified DAGMC file is unsuitable for normal Git, upload it as a GitHub Actions artifact or release asset from this same fork and commit a hash-bound retrieval manifest and verification script. Do not leave essential provenance only on the local machine.

Also retain the pinned public ParaStell example as a separate, clearly labeled generic qualification case:

```text
ParaStell commit: de7d2978ff314b060ca2e6b10745a034e8b2a3c4
examples/wout_vmec.nc
examples/coils.example
```

## Goal

Complete and independently qualify a generic native OpenMC CSG method for:

1. smooth plasma, first-wall, breeding-blanket, shield, and vessel boundaries represented by `PeriodicSplineSurface`; and
2. finite-size planar and non-planar coils represented by `SweptSplineSurface`.

The implementation must support a shaped axisymmetric torus and a non-axisymmetric stellarator using generic coefficient data. A new device must require new coefficients, not generated device-specific C++ or OpenMC recompilation.

The decisive outputs are correctness, geometry fidelity, actual OpenMC histories per second, initialization time, memory, fallback frequency, and matched comparisons with built-in CSG and DAGMC where a same-lineage DAGMC model can be built.

## Work package A — clean and finish the periodic-spline OpenMC integration

1. Inspect the live OpenMC source architecture rather than assuming the old patch still applies.
2. Integrate the validated standalone kernel into the actual OpenMC build behind an option such as:

   ```text
   OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=OFF
   ```

   The default must remain `OFF`.
3. Implement and register a real `SurfacePeriodicSpline`/`PeriodicSplineSurface` with:
   - `evaluate`;
   - nearest positive `distance`;
   - `normal`;
   - conservative `bounding_box`;
   - XML parsing;
   - direct Python construction;
   - XML round trip;
   - summary-HDF5 round trip;
   - external coefficient-file loading;
   - canonical payload SHA-256 verification;
   - relative input-path handling;
   - explicit unit enforcement;
   - explicit rejection of unsupported transforms.
4. Do not introduce JAX, CadQuery, MOAB, DAGMC, ParaStell, or Python callbacks into the OpenMC particle-tracking loop.
5. Add native tests to OpenMC's existing C++ and Python test layouts, not only adapter-stub tests.
6. Run a complete OpenMC build with the feature both disabled and enabled.

## Work package B — finish nearest-root correctness and speed

Implement a layered solver policy:

```text
analytic/specialized path where mathematically valid
    -> safeguarded Newton or Halley with a real bracket
    -> conservative patch BVH
    -> interval-Newton/Krawczyk or equivalent certification
    -> independently coded global oracle fallback
```

Required work:

1. Preserve the exact circular-torus specialization.
2. Add a shaped-axisymmetric specialization for toroidally constant axis and radius coefficients. Detect coefficient constancy with a scale-aware floating-point tolerance, not exact equality.
3. Prove or conservatively test that no earlier root exists before accepting a Newton root. The known failure mode is an exit/re-entry path on a nonconvex shaped cross-section.
4. Implement interval-Newton, Krawczyk, or an equivalently strong bounded certification path for unresolved tangent and degenerate candidate intervals.
5. Keep the broad reference solver as an independent oracle.
6. Record all fallback reasons and solver diagnostics.
7. Generate at least 10 million deterministic randomized/adversarial rays across the retained test set if runtime permits. Use fixed seeds and save every failure as a permanent fixture.
8. Require zero missed roots, false roots, and wrong-nearest-root events in the preregistered suite. Numerical distance error should be below `1e-9 * characteristic_length` for well-conditioned analytic cases and below the declared geometry tolerance for fitted cases.

Adversarial cases must include:

- tangent and near-tangent rays;
- coincident starts in both directions;
- roots close to interval boundaries;
- multiple crossings and four-root torus rays;
- axis-angle branch cuts;
- toroidal and poloidal seams;
- short gaps between nested surfaces;
- high-curvature and nonconvex regions;
- exit/re-entry rays;
- rays with non-unit direction input.

## Work package C — plasma and breeding-blanket qualification

Qualify these cases in order:

1. Exact circular torus represented by both built-in OpenMC `ZTorus` and the periodic-spline surface.
2. Shaped axisymmetric D/Miller-like surface with a high-precision numerical reference.
3. Synthetic multi-harmonic helical stellarator.
4. Public ParaStell VMEC example.
5. Authoritative WISTELL-D VMEC equilibrium.

For each fitted surface report:

- independent-grid maximum, RMS, and p95 Cartesian error;
- approximate Hausd