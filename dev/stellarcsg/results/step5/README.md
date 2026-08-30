# Step 5 remote qualification

CAD-free VMEC and MAKEGRID adapters were tested on GitHub Actions.

- `pytest.log`: full StellarCSG Python suite.
- `adapter-smoke.json`: classic-netCDF VMEC replay, surface residual,
  MAKEGRID coil parsing, units, hashes, and coil lengths.
- `synthetic_wout.nc`, `synthetic_coils.txt`, and
  `synthetic_coils.h5`: small deterministic replay fixtures.

The adapters produce frozen StellarCSG coefficient/centerline records;
no CAD kernel is imported.
