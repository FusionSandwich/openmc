# Plasma results: failed sense proposal and completed 20k comparison

The current nonaxisymmetric WISTELL LCFS completed 20000 tally-enabled histories, but transport took **159.723313 times** the builtin torus and failed the <=1.25 gate. The direct analytic evaluate/normal proposal separately FAILED Boolean sense acceptance. Neither result accepts an optimization or establishes independent CAD/DAGMC accuracy.

## Current fixed-seed benchmark-009

Current unchanged library SHA256 `f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6`; executable SHA and complete Python source-tree hashes are pinned in `transport-009-01/manifest.json`. Two sequential methods used one CPU, 2500 particles x 8 batches, seed1741, the same 256-site deterministic 14.1MeV source bank, solid Fe56 at 7.8g/cm3 and 300K, common vacuum world, energy/local mesh/material/cell tallies, and eight retained statepoints each. Materials/settings/tally XML identities are compared in the final validation receipt. This is a controlled transport boundary workload, not a physical plasma composition model.

| Plasma method / shape | Histories | Cold geometry preparation s | Cached construction/export s | Runtime init s | Transport s | Statepoint output s | Native process wall s | Worker process wall s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Current generic periodic / full nonaxisymmetric WISTELL LCFS | 20000 | UNKNOWN | 0.0227205000 | 8.908987740 | 34.819716296 | 0.318504214 | 44.185278351 | 47.891478417 |
| Builtin ZTorus / similarly sized approximate plasma | 20000 | 0.0260434020* | 0.0260434020 | 7.985720082 | 0.218000213 | 0.348096621 | 8.643225121 | 12.251063428 |
| Same-target DAGMC / verified Embree | NOT_RUN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

*Builtin preparation is primitive/model construction and XML export; Python import is separate. Custom cold VMEC fitting, coefficient compilation, admission/certificates and export are not reconstructed by cached HDF reuse. Runtime BVH loading is nested in initialization and has no separate timer. XS reading is nested in initialization: custom2.343825687s, builtin2.412519144s. Do not sum nested timers or call software compilation a geometry build. Output column is statepoint output, not every output operation. Worker wall includes imports, export, native invocation and statepoint validation. The paired block driver measured 63.413652636s after preparation/manifest freezing, not a cold end-to-end build.

Transport ratio is 34.819716296 / 0.218000213 = **159.723313187772**, FAIL. Maximum admitted custom time for this builtin denominator is 0.27250026625s. One seed is timing evidence, not multi-seed uncertainty or statistical accuracy acceptance. Both workers exited0, verified final statepoints/counts/seed/realizations, retained all outputs, and reported no native error/lost/unresolved diagnostics. Filter-ID warnings from Python are retained and checked separately for duplicate XML definitions.

The torus parameters are arithmetic means of the target coefficients (major radius about1007.01cm, minor radius about136.37cm, z offset about0cm); this is an explicitly approximate shape proxy. The custom retains all512x192 coefficients and4field periods. Proxy tally equality is not an accuracy test. Target first-root auditing, per-bin independent statistics and continuous CAD/VMEC fidelity remain UNRESOLVED. Retained sampled fidelity is described in SOURCE_REVIEW.md. Crossings/history were not instrumented.

Current build explicitly has `OPENMC_USE_DAGMC=OFF`; Embree is NOT_VERIFIED. The qualified H5M files are exact-torus fixtures, not the same WISTELL target. This branch is unsupported, not a completed comparator. No software build, acquisition, remote work or automatic retry occurred.

The outer PowerShell wrapper failed after the successful child because an entirely silent driver did not create the expected tee child-log file. Its error and lease release remain in ATTEMPTS. Native/worker receipts and block-result are intact; this postprocessing error does not erase completed work and does not authorize a rerun. An earlier administrative report-path substitution also stopped before any native worker and is retained. The wrapper is preserved as executed.

## Historical elapsed evidence (separate library and workload)

Historical exact torus R100/r20cm, 20000 histories, old library `7fa3dbf5bef055aa2227842800e54a2daa84537a1ba6730e97f4fb6cd25d317e`:

| Method | Cold build s | Init s | Transport s | Process wall s |
|---|---:|---:|---:|---:|
| Builtin torus | UNKNOWN | 5.25357 | 0.0586434 | 5.93812 |
| Custom exact periodic torus | UNKNOWN | 5.26166 | 0.0935142 | 5.98824 |

Transport ratio1.594624459, FAIL1.25; admitted custom threshold0.07330425s. Wall ratio1.00844 does not show transport parity. These analytic timings cannot replace the current real-WISTELL result. Historical real-WISTELL10000-history transport medians were custom0.36314s and fineDAGMC0.45281s; cold build/init/wall/backend are unknown and the count is below current acceptance. Historical leakage0.9955 versus1.0 remained unresolved.

## Companion coil status

| Coil method / required shape | Cold preparation | Init / transport / output / wall | Accuracy |
|---|---|---|---|
| Full rectangular complex WISTELL custom pack | UNKNOWN in this plasma stream | Refer to coil owner's current report | Independent CAD fidelity required |
| Builtin flat-ring proxy | UNKNOWN in this plasma stream | Refer to root consolidated matrix | Different shape; not a tally-equality reference |
| Same-target DAGMC with verified Embree | UNSUPPORTED in current build | NOT_RUN here | Backend and target-mesh identity required |

Round-tube, synthetic annular rectangle and historical volume-equal ring diagnostics do not qualify the full physical pack. Root's `local-coil-wave-20260926/BUILD_TRANSPORT_RESULTS_20260926.md` owns the combined coil/plasma matrix.

## Adapter experiment

The renamed isolated direct analytic evaluate/normal proposal built in11.203300675s but failed `sense changed` after0.077164599s. Eleven printed distance cases passed before the failure. Timing packets and remaining negative controls did not run. Exact failed point/direction are unknown. Keep `isolated-01/`, failed patch and the untested diagnostic; cache-only proposal is also NOT_RUN. Production files were not edited by this stream.
