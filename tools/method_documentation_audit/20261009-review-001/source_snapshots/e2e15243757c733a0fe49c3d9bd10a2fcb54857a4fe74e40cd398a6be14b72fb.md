# Continuation: native tally and plasma-source integration

State: finite local campaign completed and independently reviewed; no active
simulation, automatic successor, remote job or schedule. Read RESULTS.md and
REVIEW.md before continuing. The native-speed goal and full upstream/physical
qualification remain unmet.

Workspace: existing JS/stellarcsg-astra-kernel-20260926 managed checkout;
draft PR5 https://github.com/FusionSandwich/openmc/pull/5. PR3 and the original
checkpoint remain untouched. Work started from 71f1e080d54cd7f8559790ce2bf87ddc6050afb6.

Current native and Python library SHA256:
`f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6`.
`native-after/receipt.json` binds the equator repair, source, build and 37-check
probe. `native-partial-02/receipt.json` binds the supplemental 18 point-index
checks. `repaired/campaign-plan.json` pins all six fresh transport cases;
`comparison-after.json` and `negative-controls.json` are the final audit outputs.
`acceptance.json` binds the decisive evidence and final independent review.

The former library `7fa3dbf5bef055aa2227842800e54a2daa84537a1ba6730e97f4fb6cd25d317e`
is retained locally in native-before alongside its executable. Initial integration
and older transport-proxy receipts refer to that historical library. Do not
rewrite them to the new hash. The old-worker/runner snapshots correspond to
the initial integration campaign; all pilots are excluded from paired acceptance.
Do not assume a historical receipt hash should match a subsequently edited file.

Tools in dev/stellarcsg/qualification:
- check_openmc_integration.py: one model/source/local-tally worker.
- run_openmc_integration.py: six sequential bounded workers.
- audit_openmc_integration.py: raw HDF5/NPY/XML/receipt audit and paired means.
- test_integration_artifact_controls.py: fourteen actual corruption controls.
- check_spherical_equator.cpp and check_spherical_partial_indices.cpp: native
  deterministic mesh regressions, independent of the spline geometry.

For any rerun, pass a fresh `--report` directory and explicit accepted
`--library-sha256` to the runner; its default hash intentionally still identifies
the historical library. Worker and runner refuse existing output files rather
than overwrite results. In WSL use /opt/openmc-venv/bin/python, with this checkout
on sys.path before importing OpenMC. Its installed editable default otherwise
points to a different project. The worker checks actual import and library paths.
The current auditor also needs retained binary HDF5/NPY artifacts; Git text
receipts alone do not substitute for those raw files.

Original campaign: 4,400 histories across six cases; fresh repaired campaign:
another 4,400. Each campaign separately uses 3,072 sampled source sites and
24,576 stochastic volume samples. One CPU, 2 GiB address-space cap, 180-second
worker timeout. Builds used one job, 1.5 GiB address-space cap and already-local
GCC/CMake/static libraries. No dependencies/data were acquired or environments
changed. Refresh the complete operator-required inventory before any new build;
prebuild/prepartial inventories are historical. WSL RAM is shared host memory.
No remote execution is authorized by this handoff.

Next useful work: fit a physical source's full support to the actual CSG plasma
and check integrated strength/profile/energy/rate without rejection bias; add
generic Python membership/transform adapters needed by geometry tooling; then
extend the test matrix and sample sparse spectra. Profile the coil performance
gap separately. Partial-angle spherical ray traversal, repeated universes,
photons/MPI/OpenMP and physical packs remain explicit qualification gaps.
