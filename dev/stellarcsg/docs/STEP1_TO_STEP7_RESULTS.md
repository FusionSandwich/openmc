# Native StellarCSG remote execution: Steps 1-7

**Branch:** `feature/native-stellarator-csg-openmc-0.16`  
**Final Step 7 decision:** `REMOTE_EXECUTION_ERROR`

| Step | Result | Controlling evidence |
|---:|---|---|
| 1 | PASS | Remote clean bootstrap workflow and source archive |
| 2 | PASS | Release and sanitizer CTests; 10,000-ray adversarial campaign with zero classification or distance mismatches |
| 3 | PASS | Compiled OpenMC `periodic-spline` surface, Python API, XML/HDF5 round trip, and C++/Python tests |
| 4 | CORRECTNESS PASS | Matched OpenMC `ZTorus` comparison with zero sense, hit, or distance mismatches; timing is separately recorded |
| 5 | PASS | CAD-free classic-netCDF VMEC and MAKEGRID adapters with frozen hashes and approximately 1e-13 cm surface replay residual |
| 6 | BOUNDED PASS | Circular-cross-section swept-capsule coil prototype, segment BVH, and coil-local hexahedral mesh |
| 7 | REMOTE_EXECUTION_ERROR | `results/step7/matched-csg-dagmc-summary.json`, compact logs, and the GitHub Actions artifact |

## Step 7 interpretation

- Transport equivalent under the preregistered five-sigma gate: `False`.
- Maximum pairwise tally z-score: `None`.
- Native/DAGMC median wall-time ratio: `None`.
- Native median wall time: `None` s.
- DAGMC median wall time: `None` s.
- Smooth-to-faceted maximum sampled deviation: `None` cm.

The Step 7 benchmark is a synthetic five-field-period stellarator-like geometry,
not a production WISTELL-D blanket or magnet calculation. It tests equivalent
geometry generation and transport through both engines. It does not authorize
a general speedup claim or production-science use.
