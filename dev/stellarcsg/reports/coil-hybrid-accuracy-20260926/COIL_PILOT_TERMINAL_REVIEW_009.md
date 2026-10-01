# Coil pilot terminal/input review /009 addendum

Bounded read-only review, 2026-09-27 01:08–01:11 UTC. No native worker, HDF5 numerical audit, build or repeat was launched. Decision: **ACCEPT_DIAGNOSTIC_RECEIPT_AND_ACCOUNTING**, **FAIL_TRANSPORT_TARGET**, **FULL_TARGET_FIDELITY_NOT_ADMITTED**. This does not extend previous finite cache accuracy acceptance to general transport or physical winding packs.

## Evidence verified

Reviewed `coil-profile-20260926/meaningful-coil-009/{TERMINAL.json,SUMMARY.json,identities.json,PLAN.json,cache/receipt.json,flat_ring/receipt.json}` plus both process receipts, XML and native text logs; inspected driver `meaningful_coil_009.py` without execution.

The terminal says COMPLETED_DIAGNOSTIC and 40,000 aggregate histories. Each receipt records 1000 particles, 20 batches, current_batch20, n_realizations20, therefore 20,000 histories per method. Both process exits are zero, without timeout; both stderr files are empty and stdout contains none of the recorded fatal/lost/unresolved diagnostic patterns. This checks logs, not an independent mathematical absence of tracking errors. Driver reads completion fields from final statepoints before producing terminal evidence; those HDF5 fields were not reread here.

Recomputed SUMMARY SHA matches terminal binding 20f15f0fee3005e7582c9d674037709972242d194c2021b5bbf99841fd0dd33d. Recomputed all eight geometry/material/settings/tally XML hashes match their worker receipts. Materials, settings and tally files match between methods. Shared settings specify fixed source, seed1741, 1000 particles x20 batches, final statepoint, identical named source-bank path and strict lost-particle limits. `<output><tallies>false</tallies>` disables text tally output; it does not disable scoring. Three result arrays are recorded in each receipt, without fresh per-bin correctness acceptance here.

Recomputed all eleven identities in identities.json match current source/cache snapshot, complete cache DSO, native library/executable, coil payload/source bank, nuclear-data index and Fe56 file, driver and prior CACHE_ACCEPTANCE_003.md. Important identities: cache source 5f71bb5054f74c0e83815bcaf9a75f8509ff0ad59026ea4c551af245b20e6008; complete DSO b3f2aeea1b80c00b806b6bb96435e4e0acc3e7a6b94beaea565ccde733387e68; native library f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6; executable 47a1d0f4a15aba391a3f3ae5cb1dd0776f5041afe073e2e2d3fb58b04885a398. Driver removes LD_PRELOAD before each worker and sets it only for cache; both use fresh native processes, one-thread environment, one allowed CPU and 1 GiB address-space cap. This source/receipt evidence supports the declared reviewed interposition; a fresh dynamic runtime trace was not collected.

## Timing interpretation

| Method | Transport s | Initialization s | Reuse/export s | Native process wall s |
|---|---:|---:|---:|---:|
| Accepted-cache offset diagnostic | 167.489938658 | 6.492197796 | 0.150600704 | 174.098473556 |
| Built-in flat ring | 0.104743599 | 6.446435942 | 0.173347099 | 6.694941139 |

Recomputed transport ratio **1599.0470086673** agrees with SUMMARY; target <=1.25 fails. Reused-input-through-validation walls 174.303838860/6.925897038 are separate measurements containing preparation, native work and validation. Do not sum them with their nested stages. Cold builds are UNKNOWN because payload/XML were reused. Separate geometry load/compile and full output-finalization are UNKNOWN; statepoint timer snapshots are not complete finalization. No software compilation or DAGMC/Embree worker ran. One fixed seed, cache then flat ring, host background activity and ~0.105 s native denominator do not support an uncertainty-qualified portable ratio, although the gap is clearly large.

The custom geometry uses exact_control_offset for a retained near-circle round tube; flat ring uses cylinders95/105cm and planes +/-3.926990817cm, with identical radius150cm vacuum world and material/cell IDs. Different boundaries and tally values are expected. No equality test between these different solids can qualify their physical fidelity. Full winding-pack section/frame/corners/trims and matched target mesh remain unadmitted; nine prior blocked normals are not cleared by these logs.

## Refreshed publication review

Reviewed updated CONSOLIDATED_DEVELOPMENT_20260926.md SHA cc84b5ab23b49e0870a7c973e0719828ae8d449b7496110c1b60b0e63916766a and BUILD_TRANSPORT_RESULTS_20260926.md SHA 53ccd4f65a0737f387d85aad0dbc1aba3417f337172b9ba987b36af172713c32. New coil/plasma completion, elapsed times, transport ratios, reuse/cold distinctions and missing verified-Embree/full-target qualification are accurately stated. Four completed workers total80,000 histories does not imply a completed three-method target matrix. No concrete accounting/scientific blocker to publishing this labeled diagnostic evidence was found. The text's independent-review-request status may now be updated to this limited completed review; broader first-root/per-bin/target accuracy remains open.

Next action: publish the accepted source changes and these appropriately limited text receipts; independently compile/test the conservative BVH proposal under its already specified gates. Do not repeat healthy completed pilots or promote untested plasma/BVH changes. Resolve target geometry binding and runnable verified Embree capability before filling the final matrix.
