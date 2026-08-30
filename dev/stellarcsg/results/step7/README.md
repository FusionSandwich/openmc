# Step 7 remote comparison

A five-field-period non-axisymmetric spline surface was used to generate both:

1. a smooth native OpenMC `periodic-spline` CSG surface; and
2. a DAGMC H5M triangulation generated directly from the same surface samples.

Both models use the same one-group nearly-void material, source point, CSG
bounding box, histories, seeds, and tallies. The feature-branch OpenMC
executable is rebuilt inside `openmc/openmc:develop-dagmc` with both
`OPENMC_USE_STELLARATOR_CSG=ON` and `OPENMC_USE_DAGMC=ON`.

- Driver status: ``
- Decision: `REMOTE_EXECUTION_ERROR`
- Transport equivalent under five-sigma gate: `False`
- Maximum pairwise tally z-score: `None`
- Native median wall time [s]: `None`
- DAGMC median wall time [s]: `None`
- Native/DAGMC median wall-time ratio: `None`
- Maximum sampled facet deviation [cm]: `None`

`matched-csg-dagmc-summary.json` is the controlling compact result when the
transport driver reaches completion. The full H5M, MGXS, XML, statepoints, and
run directories are retained as a GitHub Actions artifact.
