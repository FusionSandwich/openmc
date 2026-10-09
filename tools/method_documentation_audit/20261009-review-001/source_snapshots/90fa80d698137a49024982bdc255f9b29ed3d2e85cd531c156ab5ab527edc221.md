# Plasma adapter review, 2026-09-26

Production adapter and compiled periodic kernel were not edited. Baseline HEAD at the isolated experiment was `54f8af0dbccb1ce2dcd066f27ea79667f2d6ee8f`; the current runtime library SHA256 was `f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6`.

The preserved generic implementation uses conservative physical-span patches, a flattened BVH, projected damped Newton solves and subdivision/stationary tangency handling. The current kernel inherits that architecture but differs substantially from historical HEAD `3041a938c3fb0bc349654f37b0b3ebcd3cd5a9bb`. A wholesale old-source transfer is not justified by historical timing.

The old exact adapter caches solver options and exact torus parameters and uses direct analytic evaluate/normal and the shared OpenMC torus distance helper. The current root implementation normalizes directions, rejects invalid directions, repairs near-complex/repeated roots, checks residuals and sheets, and uses a scale-aware coincident cutoff. The native helper uses a different root and cutoff policy. Preserve `checked_stellarcsg_distance`: treating unresolved roots as infinity would hide failures. Existing compiled `data()` and `specialization()` suffice to inspect exact constants; a new getter is unnecessary. A one-ULP coefficient perturbation must not specialize, and forced-general controls must remain general.

## Rejected isolated proposal

`adapter-proposal.patch` and `surface_periodic_spline.proposed.*` are retained failed artifacts. The sole renamed-class build passed in 11.2033006749989 seconds (software compilation, not geometry preparation). The probe failed with `PROBE_FAIL: sense changed` after 0.0771645989989338 seconds. Eleven printed z=0 distance records agreed across baseline, candidate and native controls. The probe stopped in the evaluate/normal/sense checks; translated, near-constant, shaped, forced-general/reference and timing-packet controls did not complete.

The failed log does not record the exact point and direction. Tiny spline-derived normal components versus analytic zero components can change `Surface::sense`'s grazing tie-break; that is a source-supported hypothesis, not an identified numerical counterexample. `complete_query_probe_diagnostic.cpp` records the missing details but has not run. No direct analytic normal replacement is accepted.

## Smaller untested proposal

`surface_periodic_spline.cache_only.*` cache the reference-solver Boolean and unchanged root options in the constructor. Evaluate, normal, root algorithm, and checked-result handling remain unchanged. These files have not been built or tested and are not production changes. The tested `prepare_candidate.py` creates proposal files with exclusive creation; do not rerun it against existing files. A later approved experiment should copy preserved inputs into a fresh output directory and choose the diagnostic or cache-only candidate explicitly.

## Real target and backend

`qualified/wistell_d_periodic_surfaces.h5` SHA256 `52695c3c6a7329faccdd009f1179c50c91e24c8902447356d3b2cd77c7f9ca36` is identical to the preserved old file. LCFS content ID is `sha256:0d299bcfa901c5c5572abee7926ba9814b4220e96721c5e5c5c680aff3584f26`. Retained fidelity reports describe 4 field periods and 512 theta by 192 phi samples, with 197633 independent samples: maximum position error 0.0343814882 cm, RMS 0.0024172 cm, maximum normal error 0.11919 degrees, fit tolerance 0.1 cm and volume relative error -7.11e-8. These are sampled results, not a continuous proof or a fresh independent real-WISTELL first-root audit.

Current `build/astra-native/CMakeCache.txt` explicitly has `OPENMC_USE_DAGMC:BOOL=OFF`. The qualified directory's two H5M fixtures are exact-torus meshes, not the real WISTELL plasma target. A same-target DAGMC comparison with verified Embree is unsupported in this build. Historical backend identity is unknown and must not be labeled Embree.
