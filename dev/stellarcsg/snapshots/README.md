# StellarCSG verified savepoints

`periodic_axis_openmc_adapter_source.zip` is the complete source and test snapshot for the periodic-axis, conservative-bounds, normal-distance-layer, coefficient-schema, and experimental OpenMC-adapter milestone.

`periodic_axis_openmc_adapter_milestone.patch` is the corresponding one-commit patch against the earlier feature-branch implementation.

The source archive SHA-256 is:

```text
5043bcd871b07067468ca9ba094e6da4b9fb2cc03f21f714248c71f1a9ecc44a
```

The patch SHA-256 is:

```text
7f89f70568283868eeb91954c2aeae2fa207b4ccddffc7aa03daa284704fc922
```

Use `../tools/restore_verified_milestone.py --force` from the repository root to materialize the verified source into `dev/stellarcsg`. The helper verifies the source-archive hash before extracting it.
