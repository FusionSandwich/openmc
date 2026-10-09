# StellarCSG independent static review and bounded next-step contract

Review date: October 8, 2026.

## Scope and evidence

This review inspected the uploaded handoff, methods ledger, evidence index, decisive saved reports/JSON receipts, selected C++ and Python source, and tracked-worktree patch. It did not compile C++, execute the acceptance runner, run OpenMC, inspect a live project checkout, or modify project source. Independent computations were limited to archive/hash checks, receipt arithmetic, and a finite-number counterexample calculation. All 106 manifest-listed files matched their recorded SHA256. That establishes packet consistency, not correctness of the historical experiments or availability of their external inputs.

Source paths below are relative to `sources/stellarcsg-astra-kernel-20260926/` in the uploaded archive, except where stated. Line numbers refer to the extracted source snapshot, not historical report line numbers.

## Conclusion

The immediate dependency is a bounded native event-layer regression, not another broad speed campaign. The strategic problem is larger: representation fidelity, first-intersection completeness, outgoing cell ownership, scoring, and workload attribution have repeatedly been treated as interchangeable evidence. They are separate obligations.

Keep exact analytic specialization, conservative local/shared BVHs, the represented-mesh AABB exclusion, and independently checked arithmetic/reference components. Do not treat the P00 triangle-backed adapter as the final non-faceted geometry method. Direct finite ruled faces are a plausible representation for rectangular swept packs, but the archived prototype reports are not a recovered, compiled, native implementation. Retain periodic plasma patches as a diagnostic baseline, not as an independently certified general solver.

## Static findings

### R1 — Masked vacuum surfaces are treated as events

**Classification:** source-derived predicted failure within the broad stated plane-model domain; not native execution evidence.

`src/axis_plane_events.cpp:136–157` gathers future intersections with every model surface. At lines 249–258, any boundary-condition-bearing plane in a contact group triggers vacuum handling, irrespective of whether it is an active boundary of the owning Boolean region. The code rejects an unchanged owner with `vacuum contact with outgoing owner`.

A concrete proposed negative control is the existing tautological surface 30, used as `(-30 | 30)` in every fixture cell (`dev/stellarcsg/tests/P00_NATIVE_AXIS_ACCEPTANCE_20261001.py:73–84`). Make that otherwise masked plane vacuum. At its contact, membership does not change, but the implementation enters the vacuum branch. This is not a demonstrated native row; it is a prediction directly from the control flow.

The Fraction oracle also uses an unconditional `any(vacuum)` over the contact group (Python lines 154–158), so arithmetic independence does not make its boundary-condition semantics independent.

**Required bounded resolution:** either establish active boundary-condition relevance or narrow admission to a proved common outer-vacuum enclosure and reject unsupported boundary placement before scoring. Do not silently turn a masked surface into a physical boundary.

### R2 — A finite interval can collide with the disabled-time-cutoff sentinel

**Classification:** source-derived predicted failure at an extreme admitted input; not a practical coil-scale failure or native execution result.

`include/openmc/constants.h:97` defines `INFTY` as the largest finite double, M. `src/axis_plane_events.cpp:160–167` accepts any positive finite rounded interval, including M. In `src/particle.cpp:298–305`, a disabled time cutoff supplies `distance_cutoff = INFTY`; lines 337–339 kill the particle whenever the selected distance equals that sentinel.

Take an axial source at -M/2 and a transmitting interface at +M/2, with a vacuum enclosure extending to +M. The exact local length is M and all these coordinates are finite representable doubles. The boundary distance equals the disabled-cutoff sentinel. The exact-event path can therefore score the flight and then kill the particle at the transmitting interface even though another owner exists beyond it.

**Required bounded resolution:** for the first narrow implementation, explicitly reject sentinel-colliding lengths before movement/scoring, or distinguish an enabled time cutoff from the sentinel in the integration path. The exclusion must be documented and independently tested. The existing opposite-extreme overflow guard does not cover this finite-equality case.

### R3 — The known overflow fixture contaminates its second query

**Classification:** confirmed source defect already disclosed by the handoff.

`dev/stellarcsg/tests/test_native_axis_events.cpp:77–86` overwrites all x-plane offsets with +DBL_MAX. Lines 123–128 restore only the material mutation; they do not restore those offsets. The runner generates two guard queries (`P00_NATIVE_AXIS_ACCEPTANCE_20261001.py:114–124,241–248`). The second query can consequently fail starting-owner lookup rather than testing its intended arithmetic guard.

**Required repair:** immutable per-query fixtures, fresh model/process isolation, or exception-safe restoration. Assert model hashes/offset values before and after every injected fault.

### R4 — Context lifecycle and default-off coverage remain incomplete

**Classification:** test gap, not a proven lifecycle defect.

`Particle::from_source()` calls `clear()` (`src/particle.cpp:150–154`), and `GeometryState::clear()` resets the experimental context (`include/openmc/particle_data.h:292–299`). This is a sensible source-reset path. Settings also reset the runtime option. However, the deterministic client constructs a fresh `Particle` for each query (test client line 68), so it does not demonstrate repeated-source reuse of one object. Runtime-off acceptance checks one first event, not a full default-off regression or a compile-option-off build.

Add reuse of the same Particle, two initialize/finalize cycles, a complete runtime-off itinerary, and matching-header/library identity checks. A PUBLIC CMake macro helps correctly linked build-tree clients; it does not make old and new GeometryState layouts ABI-compatible. Installation/distribution remains outside the admitted scope.

### R5 — The all-surface exact path is a correctness scaffold, not a production accelerator

**Classification:** direct source observation plus architectural inference; cost has not been measured.

`validate_model()` repeatedly scans cells/surfaces/tallies. `future_contacts()` allocates and sorts all future plane contacts. `owner()` exhaustively evaluates root cells. These choices make the small reference slice easier to reason about; they do not establish nearly native performance.

For this specifically admitted unit-axis domain, future contact order is equivalent to ordering finite represented plane offsets in the ray direction. Ordinary ordered comparisons on these offsets do not incur subtraction error. The large dyadic representation is useful as an independent arithmetic reference and for retained exact differences, but is not logically necessary to order these particular contacts. This observation does not extend to arbitrary-direction plane intersections, curved surfaces, or rounded transformed geometry.

Keep the first repair narrow. Any subsequent fast filtered implementation would need its own admission, equivalence, and timing evidence.

## What the implementation gets right in principle

The source separates exact-equal contacts from nearby distinct coordinates; computes strict one-sided membership for all root cells; does not round virtual movement while skipping ordinary masked contacts; computes positive local lengths from endpoint differences rather than rounded absolute parameters; overwrites the moved coordinate with the certified plane coordinate before native track-length scoring; commits the successor after that score; and resets context from the source clear path.

Those are appropriate ingredients. None is native acceptance because the retained configure phase timed out before compilation. Representative-only current scoring is an explicit narrow convention, not general all-contact or per-physical-surface current compatibility.

## Performance arithmetic

Read from `dev/stellarcsg/reports/p00-native-validation-20260930-05/speed/SUMMARY.json`:

| Seed | Candidate seconds | Fixed-ring seconds | Ratio | Additional reduction to reach 1.25 |
|---|---:|---:|---:|---:|
| 1741 | 24.648241750999993 | 10.407934450000004 | 2.3682164669090495 | 47.217662850242914% |
| 1742 | 25.984509642000006 | 9.962340493999996 | 2.6082735937051797 | 52.0755796854764% |

These additional reductions are arithmetic requirements holding each corresponding reference time fixed; they are not predictions of obtainable speedup. Retained baseline-to-candidate reductions are 41.1655% and 37.1304%, but baseline strict-FP was OFF and candidate strict-FP ON. Same-build stochastic transport was not run. Candidate and fixed-ring workers did use the same candidate runtime; the compiler confound concerns attributing the before/after change, not the arithmetic of the candidate/proxy gate.

The plasma replay JSON records 28.970192386 / 27.225501160 = 1.0640829792534112. This is a current-versus-old-source-rebuild diagnostic, not the historical archive binary and not a fresh torus comparison.

The separate diagnostic's inferred collision-scoring event counts have ratio 165678/42809 = 3.8701674881450163. They are not boundary counts, and must not be used to normalize the separate 100k speed triads. Cold construction remains unknown where the receipts say null.

## Physical-model issue that numerical repair cannot fix

`dev/stellarcsg/reports/P00_STEP2_CERTIFICATE_20261001.md` reports exact cross-component intersections for selectors 15/16 and 17/18 in the transported 3,348-facet payload. The intersecting triangles predate seam repair. Priority assigns overlapping volume to the earlier selector, producing a mathematical partition but not independently establishing physical coil ownership.

Keep the mesh-to-mesh seam-displacement certificate separate from continuous CAD fidelity. Confirm physical section, frame, corners, trims, placement, periodic image mapping, and whether selectors denote distinct coils or pieces of one coil. No point-classification test can recover missing engineering definitions.

## Exactly one recommended next experiment

### Name

**Corrected native axis-plane event-slice acceptance.**

### Hypothesis

For an explicitly restricted, one-level, void, built-in-axis-plane model and exactly unit-axis rays, anchored endpoint/contact state preserves ordered owner intervals and native local scores, including positive gaps that legacy tolerance-based successor lookup skips.

### Frozen inputs and identities

Starting archive:

`StellarCSG_AI_Review_2026-10-08.zip`

SHA256:

`04c81ec6d0bf1b98f48d9f27405218740d5a119228e6afc61ef629c44e8d8944`

Recorded repository HEAD:

`04a8061dde802f7fd4290fae45b7d84b33bfc020`

The uncommitted implementation is essential. HEAD alone is not its identity.

Tracked-worktree patch SHA256:

`295cebd61ae4cc1df791c522cda7a72af049f797a6acd9312a7ad16cdccf96f6`

Selected initial source hashes:

| Source | SHA256 |
|---|---|
| `src/axis_plane_events.cpp` | `b43d7e0921443534940aec74103d791b8d9ae42aecc74cf4e97fea37e80cd361` |
| `dev/stellarcsg/src/dyadic_axis_plane.cpp` | `1ae8870e2601a15936db25b2181e93ec8b30cd841e3c1e0012813a521ceb0497` |
| `dev/stellarcsg/tests/test_native_axis_events.cpp` | `419fa04da045c8c7b7cc70a6159140693321fe2624edef8866945aeae41fc1c2` |
| `dev/stellarcsg/tests/P00_NATIVE_AXIS_ACCEPTANCE_20261001.py` | `933afcbdf9829974dbaafbab8560c8c2a3982eeeec2d58eacdbe7884f7b4041a` |

Frozen matched libraries, to preserve rather than overwrite:

- Current: `9bf312f3e556b586fec44b714f179b97fa8dd5a25a249951674b01174b49432d`
- Baseline: `546be4c8af7da69196d6b4408de7bfb9af6ac0ddb424a90205cd513b60c19b9a`

Newly compiled experimental clients require their own matching headers/library. Do not link them to these retained pre-context binaries. Hash the corrected source, generated XML/queries, new executable, and loaded library before acceptance. Their future hashes are not yet known.

Retained decisive failure: `dev/stellarcsg/reports/p00-assembly-planes-focused-20261001-01/results.json`, SHA256 `b3fd54489dff64376d7aca25424cd80ae8e2d5719b8c90711e49fba16686d06a`.

The principal analytic fixture has A ending at 1, B beginning at `1 + 2^-48`, source `x=1.7500000000000036`, and direction -x. Expected initial itinerary is B, background of length `2^-48`, then A. Test the analogous forward direction and each axis. This fixture does not need P00 CAD, HDF5 pack payloads, nuclear cross sections, or a stochastic source bank.

### Allowed change

Only repair this opt-in event slice and its acceptance harness: isolate injected mutations; enforce a precise vacuum-boundary domain; prevent sentinel-colliding lengths from silently killing a particle; and add lifecycle/default-off coverage. Keep the dyadic foundation and the physics kernel otherwise unchanged. Do not alter P00 geometry, coil section, priority rules, plasma patches, tolerances, BVHs, or production tallies. Experimental options remain OFF by default.

### Independent oracle and acceptance

Use an independently written analytic/Fraction owner-interval ledger, including explicit Boolean boundary relevance. Do not copy the C++ event loop or its unconditional vacuum policy. Check ordered contacts, contact groups, predecessor/successor, each positive local length, certified endpoint, native cell-flux contributions, and declared representative-current bins.

Cover the retained gap48 ray; adjacent-double endpoints without an interior double; true ties and duplicate surfaces; all axes/directions and token permutations; masked transmission contacts; exact-origin continuation; large anchors with equal rounded absolute times; terminal vacuum; and same-object source/reset lifecycles. Preserve the known fixture failure as a negative-control record rather than erasing it.

Add the masked-vacuum and finite-INFTY cases above. For a deliberately narrowed domain, require their rejection before movement/scoring. Test oblique/non-unit/coplanar rays, nonplanar surfaces, materials, unsupported filters/time cutoffs, stale contexts, and overflow. Corrupt the oracle rows by deleting a gap, changing ownership, moving flux between bins while preserving its total, changing current, or deleting a contact; each corruption must be rejected.

A same-build runtime-off control must preserve the legacy dispatch/trace, including separately identified legacy negative witnesses. Also establish that the compile-option-off build remains valid. Existing arithmetic tests do not substitute for native rows.

### Proposed resource envelope, subject to fresh admission

This is a proposed cap, not an execution authorization or elapsed-time prediction: one CPU, one build worker, at most 2 GiB virtual memory per process, a 900-second total phase cap, and a 300 MiB output cap. Refresh machine/tool/storage/process inventory and confirm at least 3 GiB available WSL memory and 2 GiB free system/target storage, or decline admission. Use existing dependencies only, a new no-overwrite build/output directory, and the existing shared compute lease. Preserve all old trees and uncommitted work.

Diagnose the recorded WSL Git-pointer/configure behavior before assigning the failure to dependencies. HDF5 was found; the failed probe alone does not establish a missing dependency. Allocate a declared bounded share of the overall phase to configuration rather than automatically repeating the failed 60-second cutoff. Stop on the first build/test/resource failure; no automatic retries or successor campaign.

### Decision rules

**Pass:** every supported deterministic row has the exact expected itinerary and correctly rounded local contributions; every unsupported control fails before scoring; all corruption controls fail; lifecycle/default-off checks pass; and source/loader identities are verified. This establishes only the narrow slice, pending independent review.

**Native mismatch:** retain the smallest valid failing row and stop. Do not widen to facets, materials, or plasma.

**Configure/build/cap failure:** record an infrastructure-blocked outcome, not a geometry-method failure.

**Pass but high cost:** retain it as a correctness reference. Do not label it a near-native production path.

There is no 20,000-history performance acceptance in this experiment. A small deterministic correctness test and a statistically adequate transport benchmark serve different purposes. No coil/plasma speed claim follows from this repair.

## Missing evidence that changes later decisions

Physical pack CAD/section/frame/trims and owner mappings; original and transported payload bytes; independent positive-hit/normal references for actual imported geometries; complete generic plasma/adapter source; preserved raw statepoints and source banks; a runnable fully identified checkout/library environment; and the actual ruled/ownership prototype bundles. An unavailable Embree comparison or cloud prototype is not a failed method.
