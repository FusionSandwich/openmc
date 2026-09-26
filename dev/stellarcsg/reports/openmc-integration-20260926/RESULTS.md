# Native CSG tally and source integration, 2026-09-26

The diagnostic integration interface works for both periodic plasma and swept
coil proxies. The new local-tally helper returns ordinary OpenMC tallies with
standard meshes and optional cell restrictions. Standard MeshSource, with
native plasma-cell constraints, is the chosen new plasma-source interface;
the VMEC/UQ adapter can later produce that interface. This does not admit a
physical device source or certify all OpenMC combinations.

## Completed evidence

| Check | Observation | Qualification boundary |
| --- | --- | --- |
| Python helper and source tests | 18 tests, 17 subtests pass | Synthetic source handoff; MOAB construction only |
| Independent equator regression | Old native library fails after 3 checks; repaired library passes 37 | Canonical equator, full-angle tracks and listed edge cases |
| Fresh transport campaign | All six workers exit 0 | Serial neutron proxy workload, one pinned library |
| Plasma mesh-source pair | All 19 tally comparisons agree | Exact torus/periodic-surface proxy; finite histories |
| Plasma constrained-box pair | All 18 tally comparisons agree | Same exact proxy, source rejection exercised |
| Coil file-source pair | All 18 tally comparisons satisfy approximation criterion | Near-circular swept surface versus native torus |
| Corrupted-artifact controls | All 14 reject | Actual file/receipt mutations with raw-data revalidation |
| Independent review | Accepted within stated boundaries | See REVIEW.md; no upstream-readiness claim |

The six repaired runs transport 4,000 plasma and 400 coil histories in total,
sample 3,072 source sites separately, and use 24,576 stochastic volume samples.
Each pair uses identical material, source, settings and tally configuration,
matched seeds and the same loaded library. Plasma has Fe56 at 7.8 g/cm3 and
300 K in a 1 cm shell around an R=100 cm/r=20 cm void torus. The coil fixture
uses the prior near-circular r=5 cm control-offset model. Both native and spline
models are partitioned into complementary material subcells, including a small
local cell, using ordinary plane/box CSG intersections.

Plasma numerical agreement requires each compared mean to differ by at most
`1e-8 + 1e-9 * max(abs(a), abs(b))`. Maximum observed absolute differences are
1.5279510989785194e-10 for the mesh-source pair and 4.729372449219227e-11 for
the box-source pair. The approximate coil criterion is
`1e-5 + 1e-4 * max(abs(a), abs(b))`; its largest observed absolute difference
is 0.05261307040927932 across scores with different units. This is not a single
physical error norm or a confidence interval. Sparse/zero bins do not establish
full-spectrum equivalence. The overall audit state refers to plasma agreement;
the separate coil observations must be read with their approximation boundary.

## A real local-scoring defect found and repaired

The first six-run campaign passed integrated score closure but failed the
native/spline comparison for spherical-mesh local bins in the plasma box-source
case. Damage-energy contributions of approximately 29.43101492238 and
1.56824119806 moved between polar hemispheres while totals remained unchanged.
`comparison-before.json` and the original artifacts preserve this failure.

The canonical equator was treated as a squared cone, giving a repeated root
susceptible to cancellation. `src/mesh.cpp` now solves the exact PI/2 boundary
as the plane z=0. Nearby angles retain the general cone solver. A separate
point-index correction preserves signed tiny heights when acos(z/r) rounds
to PI/2, while retaining radial/azimuth membership checks. Exact z=0 ownership
is unchanged. No spline kernel or comparison tolerance changed.

The 37-check native probe covers both hemispheres/directions, known half-track
fractions, parallel and coincident rays, an already traversed root, tiny nonzero
vertical direction, tiny signed height, unsplit theta, adjacent representable
theta values and translated origins. A separate supplemental point-index probe
covers north-only/south-only theta grids and radial/phi exterior rejection;
its receipts are in native-partial-02. The first supplemental attempt lacked
the required XML origin and failed; native-partial preserves that harness error.
Partial-angle ray traversal remains unqualified.

The six fresh repaired runs resolve the previously observed bin redistribution
under the original criteria. `comparison-after.json` is authoritative for those
runs; earlier pilots and old-library results are not silently reused.

## Exercised ordinary OpenMC interfaces

The finite matrix includes regular, rectilinear, cylindrical and spherical
meshes; cell/material restrictions; local subcells; energy spectra; flux, total,
absorption and damage-energy; tracklength, collision and analog estimators;
surface and mesh-face current; universe, cell-instance, birth-cell, birth-mesh,
time, particle, outgoing-energy, cosine and response-function filters.
XML model loading, native Summary surface dispatch, StatePoint arrays,
DataFrame conversion, reshaping, slicing and CSV output are exercised.

Reopened raw means reproduce material-partition, local-cell/mesh, response and
secondary-birth closure. Filter bins, scores, nuclides, estimators and mesh
geometry are checked against the model XML. All declared scores have nonzero
aggregate response, but individual bins may still have inadequate statistics.

Local cell volumes are sampling estimates: plasma 429.296875 +/-
15.762949190008996 cm3; coil 180 +/- 0 cm3 in this particular box fixture. The
zero observed uncertainty is not an exact containment certificate. A local
mesh plus cell filter requires each intersection volume for volume normalization,
not the full mesh-element volume. Scores remain per source; damage-energy is
not automatically DPA/time. The preceding transport-proxy report separately
checks its explicitly declared Fe56 NRT conversion, not device material damage.

The mesh source checks two element probabilities (0.25/0.75), conditional
energies (2.45/14.1 MeV), unit directions and native plasma containment. It uses
the isotropic angular distribution; empirical isotropy is not separately tested.
The constrained box deliberately straddles the plasma boundary. Rejection can
change spatial/energy probabilities: physical source admission must independently
establish support and rate against the actual CSG geometry. Secondary neutron
births are not required to remain in the original plasma source mesh.

## Strict source admission and evidence integrity

Sampling receipt hashes are now bound to their canonical source/mesh/mesh-data/
case roles; merely having the right set of hash values is insufficient. Duplicate
JSON keys, nonfinite numbers and boolean identity/count fields are rejected.
Clearance subtraction uses exact binary64 fractions to prevent a sub-ULP unsafe
margin from rounding into acceptance. Mesh bytes are rehashed at source
construction. Optional constraints take actual OpenMC cells.

The fourteen artifact controls reject forged closure, sample hash, means,
uncertainties, runtime, missing output, boolean/nonzero exits, failure logs,
XML hash maps, omitted source constraints, outside source positions, malformed
directions and changed mesh geometry. The independent Sol review checked the
source and decisive receipt/data hashes. Raw HDF5/NPY and rollback binaries are
retained locally; text receipts/configurations are published, with byte-preserving
Git attributes. These are small diagnostic runs, not a replacement for upstream CI.

Pilot-01/02/03 failed in harness setup. Pilot-04 imported an installed OpenMC
checkout rather than this worktree and is excluded; it also exposed an incorrect
assumption about secondary births. Pilot-05 used the correct checkout but is
not part of paired acceptance. Production workers explicitly verify both Python
checkout and loaded library identity. Historical worker/runner snapshots are
retained for the initial campaign.

## Remaining limits and next work

Physical VMEC/UQ support and neutron-rate normalization, native MOAB/UQ sampling,
arbitrary stellarator shapes, real coil packs, sparse spectra and device DPA
remain unqualified. So do repeated universes/lattices, distributed cells,
derivatives, depletion/MGXS, variance reduction, coupled photons, MPI/OpenMP,
unstructured backends and the complete boundary-condition matrix. Python spline
membership and generic translation/rotation still require dedicated adapters.

The speed goal is still unmet. The separate historical transport-proxy campaign
observed plasma at 62.08% of native throughput and the coil at 0.1299%, with
2.49x acceleration over its unaccelerated implementation. Its short native coil
timings limit precision. This integration campaign makes no new speed claim.

All work was local using existing software/data. Preflight/build records include
host memory, disks, processes, compilers, environments, caches and checkouts;
acquisition was zero. No remote work, dependency installation or schedules were
used. See CONTINUATION_HANDOFF.md for exact library identity and continuation.
