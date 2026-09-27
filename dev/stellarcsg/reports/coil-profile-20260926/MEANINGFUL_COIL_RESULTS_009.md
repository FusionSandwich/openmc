# Coil 20,000-history diagnostic /009

**COMPLETED_DIAGNOSTIC; transport performance gate FAIL.** One fixed local block
completed 20,000 histories for the retained accepted-cache offset implementation
and 20,000 for built-in flat-ring CSG, both tally-enabled. This fills a meaningful
history-count diagnostic against the requested coil proxy. It does not qualify
the full WISTELL-D winding pack, physical fidelity, or a three-method comparison.
Owner evidence awaits independent runtime/receipt acceptance.

| Elapsed seconds, one seed 1741 | Custom cache | Built-in flat ring |
|---|---:|---:|
| Reused geometry/XML preparation and export/copy | 0.150601 | 0.173347 |
| Cold geometry construction | UNKNOWN | UNKNOWN |
| Native total initialization | 6.492198 | 6.446436 |
| Native transport | 167.489939 | 0.104744 |
| Recorded statepoint write timer | 0.029161 | 0.028771 |
| External native process wall | 174.098474 | 6.694941 |
| Final-statepoint receipt validation | 0.039176 | 0.041627 |
| Reused input preparation through validated result | 174.303839 | 6.925897 |

Custom/built-in transport = **1599.047** (rounded), exceeding the required <=1.25.
The denominator remains short even at 20k histories. These are measured seconds,
not rate inverses. One seed supplies no error bar; recorded desktop/Julia
background activity limits timing precision. Neither run emitted fatal,
lost-particle, missing-cell or unresolved diagnostic strings. Both exited zero,
and final statepoints report 1000 particles/batch, 20 batches, current batch 20
and 20 realizations. This verifies 20,000 completed configured histories per
method; it does not prove arbitrary geometric correctness.

Initialization contains geometry loading/compilation and cross-section reading;
their independent geometry substage is UNKNOWN. Reading cross sections was
2.145957/2.114073 seconds and is nested inside initialization. Transport,
simulation/active batches, tally accumulation and output timers also overlap.
Do not sum those nested values. Statepoint writing is a native snapshot and does
not measure complete output/finalization; external process wall contains the
finalization that the snapshot omits. Existing HDF5 coefficients and model XML
were reused, so copy/export times do not establish cold construction costs.
One-off WSL dispatch, historical fixture construction and software build are
outside the reused per-method workflow interval. No software build ran.

The custom fixture is one cardinal-cubic near-circular centerline, major scale
100 cm, with a 5 cm round section. The flat ring uses native cylinders at radii
95/105 cm and planes at +/-5*pi/4 cm. It has the corresponding equal-volume
rectangular section but different support, chords and particle trajectories.
Both use the same 150 cm vacuum sphere, 256-site 14.1 MeV file source at
(100,0,0) cm, seed 1741, Fe56 7.8 g/cm3 at 300 K, nuclear data, settings,
three cell/energy/material tally layouts and final-only output policy. The
materials/settings/tally XML hashes are identical. Raw local sum/sum-square
arrays for all three requested tallies are retained and finite. Cross-shape
tally equality is neither required nor claimed. Boundary crossings/history
were not recorded and remain UNKNOWN.

The source cache SHA256 is
`5f71bb5054f74c0e83815bcaf9a75f8509ff0ad59026ea4c551af245b20e6008`.
Fresh custom processes used the retained complete reviewed DSO
`b3f2aeea1b80c00b806b6bb96435e4e0acc3e7a6b94beaea565ccde733387e68`.
Production libopenmc remains
`f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6`;
it was not rebuilt. Source, executable, DSO, data, fixture and harness hashes
were checked before and after this block. Native loader resolution points at
that pinned library. The prior same-solid original/cache correctness gates
remain retained evidence: zero wrong-root/failure queries, nine normal gaps.
No new repair or arbitrary-origin normal qualification is implied by timing.

`meaningful-coil-009/SUMMARY.json` SHA256:
`20f15f0fee3005e7582c9d674037709972242d194c2021b5bbf99841fd0dd33d`.
Worker receipts, complete statepoints, stdout/stderr, XML, Windows/WSL inventories,
input identities and append-only attempts are preserved in that directory.
The block took 183.13 seconds, held one exclusive lease, constrained each
child to one CPU and <=1 GiB address space, and used <=600 seconds/worker and
<=1800 seconds/block. All children exited and the lease was released. No retry,
successor or additional 200/1000-history timing worker ran.

`FULL_TARGET_MATRIX_009.json` records the remaining required rows. The full
physical winding pack is NOT_ADMITTED: section/frame/corner/trim/coil-placement
and material-boundary fidelity remain unresolved. The current pinned build has
DAGMC disabled. Independent `EMBREE_AND_METHOD_REVIEW_009.md` establishes genuine
historical Double Down/Embree linkage, but currently missing backend dependency
closure, and distinguishes standardized 1 cm circular-tube meshes from the
unestablished physical pack. No current verified Embree worker ran. Nonaxisymmetric
plasma is the separate plasma owner's row and is not filled by this coil result.

The independent review accepts BVH candidate
`91b702e429669438163bc81e8ba57244ef6c239602a187b6b66150c5a324d476`
as SOURCE_DESIGN only. It remains uncompiled and unapplied; executable enclosure,
earliest-root/bank, normal/failure and timing checks are NOT_RUN. This block used
the cache only. Its poor flat-ring-relative time motivates that next bounded
compile/acceptance step, subject to root selection and fresh inventory/lease.
