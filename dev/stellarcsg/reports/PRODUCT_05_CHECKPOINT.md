- One-period model generated from supplied inputs: PARTIAL. Native plasma/16 finite-member XML exists; vacuum-clipped diagnostic only, not validated periodic geometry.
- Plasma and finite-coil shape errors, section assumptions and clearance: sampled plasma radial max 0.20422 cm / 0.11974% local radius; standardized 1 cm circular coil envelopes, source winding-pack fit and clearance NOT_MEASURED.
- Known numerical/navigation defects and geometry-domain exclusions: recovered strict 3/160 and retained 2/256 disagreements remain; new real stress has 14/160 disagreements; 128 reference geometry blocks are not recovered-production-enforced.
- Actual recovered-candidate one-period transport throughput: NOT_RUN. Only a retained exact-reference clipped diagnostic completed 16 histories.
- Ratio to defined toroidal reference: NOT_RUN.
- Ratio to matched Double Down/Embree: NOT_RUN.
- Simple API and held-out automated conversion: executable simple coefficient example and WISTELL preparation/export; separate ParaStell plasma remains rejected for geometric-theta fold.

# Product milestone 05: unqualified checkpoint

The requested functioning **periodic recovered-candidate** milestone is not
delivered. This continuation implements input/model plumbing, fidelity gating,
new hit-rich stress evidence and a bounded exclusion experiment. No production
C++ solver changes or promotions occurred. The 04 branch remains at full SHA
57cb1fbf75a54a0fa75e70386922ad9cfecf06b1. Work is on the new
JS/stellarcsg-product-20260913-05 branch, with isolated importer commits on
JS/stellarcsg-import-20260913-05. No push, PR, install, remote job or rewrite.

## Product evidence

`one_period.py` consumes raw VMEC/MAKEGRID sources plus the hash-bound compiled
coil payload and sector manifest. It does not yet compile raw coil filaments in
the same command. Units, source hashes, NFP=4, section assumptions, 16 complete
member curves, individual surface/material/cell IDs and neighbor-span metadata
are explicit. No first-12 selection, blanket or whole-device transport is used.

Periodic preparation defaults to REJECT_PERIODIC_SEAM_MISMATCH. The observed
coil rotation discrepancy is about 0.00020307 cm; merely recording this is not
a periodicity fix. `record-approximation` retains supplied curves and records
the mismatch without imposing rotated copies. Only explicit `diagnostic_clipped`
exports vacuum sector faces. Separate native swept surfaces are used, never
surrogate spheres; a sphere is used solely as the enclosing vacuum world.

The first 64x32 plasma fit failed an independent off-grid radial check: max
11.33767 cm, 8.16553% local-radius error. New bounded automatic fitting retains
all attempts and tests a public 1% sampled-error target. Its gate rejected
64x32 (7.8086%) and 128x64 (1.22134%), selecting 256x128 (0.099667%). A distinct
offset validation grid gave max 0.2042205 cm, RMS 0.018439 cm, P95 0.030255 cm,
and max error/local radius 0.119736%. Different maxima come from different
sample locations. These are radial point-to-surface residuals on 4608 points,
not two-sided Hausdorff bounds, normals, volume, topology or clearance proofs.
No source-to-winding-pack fidelity claim follows from unchanged coil splines.

`product05_simple.py` ran and produced a helical test plasma and finite circular
coil using public Python parameters, without CAD/mesh/OpenMC Python dependencies.
The independent ParaStell fixture was attempted with the radial compiler and
again returned `surface slice 0 has a geometric-theta fold`; it is not admitted.

## Actual diagnostic transport

`model-02` contains native XML, compiled plasma, logs, statepoint and closure.
Retained exact-reference OpenMC library SHA256
451b21536d4178a81c4ec5c9a44f6e04eac194c58c87a639d643441ff2717d48
was explicitly bound; it is not the recovered product source. Local H1 at
1e-6 atom/b-cm provides simple positive-density materials. Distributed source
boxes span retained member anchors; geometry overlap checking was enabled.

One batch of 16 histories completed, exit 0, reported leakage 1, no numerical
error/lost-particle report. Initialization 5.931 s; transport-only 2.604 s;
console active rate about 6.10 histories/s. This is a single tiny debug run,
not accepted timing or statistical uncertainty. Statepoint runtime is captured
before final output and yields a slightly different active rate; both receipts
are retained. Nine of 16 coil bins had positive track-length flux. Sum over all
18 cell bins equals the independent global flux tally within 1.13687e-13
absolute / 1.41248e-16 relative. Sparse overlap checks, sampled source coverage
and closure do not prove all member boundaries or periodic navigation.

## Numerical recovery and failed experiment

The old strict bank and production code are unchanged. New source-derived
coil031 stress bank SHA256
59580d8aa8348ad4d81d7e7bed5c5217639fff5d71a39708400994e7b33282cb
contains 32 off-knot locations with five unique constructions each. It is not
a held-out configuration or a realistic transport performance bank.

| Lane | New stress disagreements | Hits | Single-run mean distance ns |
|---|---:|---:|---:|
| Preserved old | 34 | 143 | 3693.75 |
| Seed repair | 14 | 143 | 4644.38 |
| Exact reference | reference | 149 | 113190077.58 |

All 128 ordinary/near-entry/interior/center-exit cases agree after the seed
repair. Fourteen grazing constructions disagree: real04 returns 33.73476 cm
instead of 0.19999636 cm; real02 returns 0.200463 cm while the exact reference
finds its first root at 18.57957 cm. Binary64 construction can split or eliminate
a nominal grazing contact, so category names are not contact oracles. Independent
Sol review confirms both earlier-root misses and false residual acceptance are
present. These selected cases are not an error-rate estimate.

Candidate A stage-one interval cover compiles source cubic controls into outward
Bernstein intervals and excludes boxes using the stationary circular-tube
equations. Checked environment, radius binding and a node/depth budget preserve
uncertain boxes. Independent review conditionally approves only exclusion of
those equations, NOT a geometry certificate, existence test or distance solver.
Final probe: 90 ROOT_FREE, 70 UNRESOLVED, no false exclusions against the saved
exact bank; approximately 106397 ns/query in one run. This form is rejected for
the production hot path. It does not repair a08 or establish root ordering.
No exact fallback is called by this probe; every retained case remains unresolved.

Negative evidence retained: coarse plasma fit and its completed-but-ineligible
diagnostic; intermediate 128x64 fit failure; interval-cover cost/ambiguity;
real grazing failures; held-out theta-fold; periodic seam rejection. Initial
proxy XML and schema mistakes were rejected in review and corrected in separate
commits, not used in the native diagnostic. The first cover receipt predates API
hardening and is superseded by cover-02; only cover-02 is bound to final source.

## Verification and restart

Root tests: 17 PASS (9 importer/XML/fitting plus 8 exact-oracle arithmetic).
Interval-cover arithmetic fixtures: 9 PASS, deliberately not root-existence tests.
Simple artifacts and both real diagnostic runs executed. Twenty local ref checks
are unchanged, including archive, develop and the 04 checkpoint; master is a
remote-tracking ref, not a local branch. No build or benchmark is left running.

Next: implement local root isolation/ordering and bounded difficult-contact
fallback, not more unconditional 2-D box subdivision; repair admission and
projection; resolve periodic source/member mapping with quantified geometry
change; compile coils directly from raw inputs; validate full fidelity and
clearance; then run the recovered eligible periodic model and matched controls.
The external comparator is not the blocker. See PRODUCT_05_RESTART.md.
