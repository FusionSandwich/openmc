# StellarCSG remote execution control

**Repository:** `FusionSandwich/openmc`  
**Branch:** `feature/native-stellarator-csg-openmc-0.16`  
**Execution request:** complete steps 1 through 7 in sequence and retain all code, workflows, manifests, and compact results on GitHub.

## Step definitions

1. Replay the bootstrap on a clean remote OpenMC environment.
2. Run Release, sanitizer, and expanded adversarial-ray qualification.
3. Build and test the compiled OpenMC `periodic-spline` surface.
4. Compare the custom surface against OpenMC's built-in `ZTorus`.
5. Add and test generic VMEC and MAKEGRID adapters.
6. Implement and qualify accelerated swept-magnet intersection and coil-local meshes.
7. Compare matched native CSG and DAGMC/Embree stellarator models.

## Current evidence before continuation

- Step 1 bootstrap workflow: previously completed successfully on the feature branch.
- Step 2 sanitizer job: passed.
- Step 2 Release/adversarial job: held because the fast ray search missed one classification in each 10,992-ray case and selected one wrong helical-surface root; this must be corrected rather than waived.
- Step 3 native OpenMC surface workflow: passed at commit `01e5accf51f93e065bc1fcf79acdffe92c754eed`.

Large generated files remain GitHub Actions artifacts. Compact JSON/Markdown evidence and replay scripts are committed to the branch.
