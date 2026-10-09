# Accepted cache and tally patch publication

This publication adds independently reviewed source changes and targeted test evidence to the existing draft PR. It does not rebuild the production library or accept full-target performance.

## Exact local source reviewed before publication

| File | SHA256 of reviewed local bytes | Acceptance |
|---|---|---|
| dev/stellarcsg/src/certified_spline_offset.cpp | 5f71bb5054f74c0e83815bcaf9a75f8509ff0ad59026ea4c551af245b20e6008 | CACHE_ACCEPTANCE_003.md: narrow immutable interval cache |
| openmc/filter.py | 3a5371909d919f278369a1ce47719192ea7646cf18e08df48c6717a1f9063651 | TALLY_ACCEPTANCE_005.md: transform/bin identity and stored rotation reader |
| tests/unit_tests/test_mesh_filter_transform_identity.py | 3d508ad8950f1362facf0a9defa60a49b4a9de2ca7cd53a803e5e9cde977dda5 | Exact final source/test receipt: 13 passed in 1.16 s |

The root rehashed all three files and checked the actual diff against the independently accepted deltas. Git newline normalization of source and selected text evidence is recorded separately in PUBLICATION_SOURCE_BINDING_20260926.json; raw local hash references remain raw hashes, while the mapping records staged content hashes. This is not a new numerical build or requalification.

## Supporting evidence

- [Cache acceptance](coil-hybrid-accuracy-20260926/CACHE_ACCEPTANCE_003.md) predates integration and correctly records the then-original production source. The table above identifies the integrated candidate.
- [Tally acceptance](coil-hybrid-accuracy-20260926/TALLY_ACCEPTANCE_005.md) and [receipt](coil-hybrid-accuracy-20260926/TALLY_RECEIPT_005.json) bind the final tests. Captured pytest stdout is retained in mesh-filter-transform-20260926/pytest-final.stdout. The tests use actual Python package/XML behavior and manually constructed native-layout HDF5 groups; they do not transport particles.
- [Coil elapsed-time diagnostic](coil-profile-20260926/TOTAL_TIME_RESULTS_005.md), SUMMARY.json and PHASE_MEDIANS.json record the independently accepted cache in isolated complete DSOs at 1,000 histories. Its old aggregate-wall acceptance field is superseded by the transport contract and >=20k minimum, as the report explicitly states.
- New [20k coil](coil-profile-20260926/MEANINGFUL_COIL_RESULTS_009.md) and [20k plasma](plasma-best-time-20260926/RESULTS.md) reports and selected manifest/terminal/worker receipts are published. Both transport time gates fail. They do not qualify a full physical coil pack or independent general-plasma accuracy. No statepoints or binaries are added to Git.

The source changes introduce no dependency, public geometry schema or new transport-loop allocation. The cache stores three immutable full-span derivative interval vectors and preserves the original expression for other intervals. Filter fixes preserve transformed local tally regions and read native 9/12-entry rotation arrays without recomputing the stored matrix.

Production library remains SHA256 f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6. Coherent production rebuild is NOT_RUN. New >=20k diagnostics use individually identified existing experimental binaries; they must retain their actual source/linkage identities.

Unreviewed BVH and failed plasma fast-path proposals are excluded from these production source changes. Raw local statepoints, binaries, physical CAD/HDF5 and nuclear data remain local; selected text evidence does not make a GitHub-only transport reproduction self-contained. No merge or upstream release is implied by updating this draft PR.
