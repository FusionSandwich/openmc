# Product milestone 05 contract, version 1

Based on the user's 2026-09-13 milestone reset and local checkpoint
57cb1fbf75a54a0fa75e70386922ad9cfecf06b1. That branch remains preserved.
New root branch: JS/stellarcsg-product-20260913-05. Importer work is isolated on
JS/stellarcsg-import-20260913-05. No production eligibility is implied.

## Product dashboard

Report separately: simple construction; automatic input conversion; source and
representation fidelity; native navigation; matched mesh advantage; defined
toroidal engineering-reference throughput; genuinely held-out configuration.
One field period includes plasma and finite coil members, not a circular tube
substitute described as a source-faithful winding pack. Section assumptions,
units, source hashes, NFP and approximation parameters must be explicit.

The operational targets are <=1% local-size fitting error initially, with a
0.1/0.5/1/2% study, >=2x matched mesh throughput and >=0.8 engineering-reference
throughput aspirations. They are not measurements or neutronics guarantees.
Keep source-to-spline, representation and numerical root errors separate.

## Frozen target contracts, not yet implemented end to end

`stellarcsg.geometric-roots/v2` targets the least nonnegative physical-distance
contact with an enclosure and transverse/stationary kind. Origin association
removes only its uniquely associated root, or returns UNRESOLVED when ambiguous.
`openmc.material-crossings/v1` additionally requires differing one-sided cell
senses. A same-sense stationary contact is not a material/current/tally crossing.
These are independently reviewed target contracts, not a post-hoc alteration of
the recovery04 strict comparison or a claim about current adapter behavior.

Strict recovery04 results remain immutable. No tolerance is increased and no
strict mismatch is relabeled PASS. A forward geometric contact is not necessarily
a material crossing. A contact-only root must not manufacture a material change;
it also must not be silently dropped by an implementation whose stated contract
is nearest positive contact. A crossing must select the correct member/cell on
both sides, including the first entry and exits from an interior origin.

The production adapter currently has only found/distance and converts no-found
to infinity. This is insufficient for an unresolved query. An experimental
exclusion tool will return ROOT_FREE or UNRESOLVED, never treat an inconclusive
range test as no-hit, and never claim existence from a small residual.
UNSUPPORTED_GEOMETRY is distinct from UNRESOLVED_QUERY and from ROOT_FREE.

Coincidence is an origin-boundary association, not permission to erase every
root in a distance window. The existing OpenMC primitives differ in near-zero
handling, so a common revised policy requires independent review and adapter
crossing tests. a06 remains a strict discrepancy pending that evidence; a08
remains a missed contact; a15 remains a numerical-distance discrepancy. Retained
shape0/1 index3 and all 128 reference geometry blocks remain separately reported.

Nearest-root acceptance requires every earlier possible interval resolved or
excluded. Geometry admission, classification, normal and member identity are
additional gates, not consequences of this root invariant.

The OpenMC geometry documentation is context, not a tolerance prescription:
https://docs.openmc.org/en/stable/methods/geometry.html
Local source and adapter behavior take precedence for this build.

Independent Sol/High review traced `cell.cpp:975-976` (surface-ID association),
`surface.cpp:122-135` (normal tie-break), cylinder/sphere origin handling,
`surface.cpp:980-1014` (torus cutoff), and `cell.cpp:1002-1029` (complex-region
membership-change check). The simple-cell path lacks the latter filter. The
collection adapter also drops returned coil identity and applies one coincidence
flag to every member; the diagnostic therefore uses separate member surfaces.
No common crossing policy or collection rewrite has been promoted here.

## Revised execution order

Candidate A and other bounded alternatives may directly address current
blockers; none may be promoted while incorrect. Prepare importer/sector/API in
parallel. Do not silently impose periodic symmetry on inconsistent source data.
Exporting XML or a clipped diagnostic is not periodic transport qualification.
Accepted timing is serial and requires completed histories, explicit numerical
failures, identity and closure checks. The mesh comparison is not the inner loop.

## Current local execution audit

Before new builds: Windows total RAM 33457440 KiB, free 4060728 KiB. C: free
62479335424 bytes (source/target/system); D: free 55312015360 bytes (WSL/data).
Largest residents: Chrome 1.05 GB twice, ChatGPT 0.95 GB, Codex 0.85 GB,
OneDrive 0.70 GB and additional Chrome processes. No owned build/transport ran.
WSL OpenMC-Dev-D reports 25.20 GB total / 24.38 GB available; host headroom is
the actual constraint. Its virtual filesystem has 1.021 TB free, backed by D:.
Existing GCC 14.2, CMake 3.31.6 and Python 3.13.5 in /opt/openmc-venv suffice.
The venv is 606 MB; pip cache 152 MB; apt cache 24 MB. /opt also contains
g4gate7 and g4native. Existing worktrees/builds are inventoried in recovery04.
No environment change, upgrade or acquisition is needed: acquisition 0 bytes.
New standalone probe build is limited to product-05/build, expected <50 MB,
one compiler process. Rollback is isolated generated output only, retained until
explicit cleanup. Existing binaries cannot implement the new exclusion probe,
so a source-bound standalone compile is needed, not a dependency installation.

Later bounded data lookup confirmed local H1 data at
`C:/Users/joshu/Documents/2026_DPA/openc-hts-dpa/.data/openmc/`:
cross_sections.xml SHA256
218236803b2c4a21b038992af93dacfdfe5c0c0401cbbc57f3ff3a947c63abc7,
H1 SHA256
a28ee9ad6fc9e5ce1e6d0c88acb93378c2054ab65f55b9a52bd42abee4d00083.
The absent plain-WSL /data/openmc mount was not a data-acquisition blocker.
