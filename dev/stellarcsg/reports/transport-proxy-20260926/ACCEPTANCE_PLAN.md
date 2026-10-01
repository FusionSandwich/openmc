# Matched proxy transport acceptance, fixed before production runs

Plasma: exact constant-coefficient R=100 cm, r=20 cm periodic surface against
builtin ZTorus; identical 1 cm Fe56 shell, void plasma, vacuum sphere r=150 cm.
This tests the exact specialization, not arbitrary stellarator plasma shapes.

Coil: 64-control near-circular spline offset with r=5 cm versus builtin
R=100 cm, r=5 cm ZTorus. Native torus is an approximation control. Identical
spline geometry with prefix enabled/disabled is the implementation control.
An equal-volume annulus (two cylinders and two planes) is an additional
rectangular-section shape/cost control; its physics need not match a round tube.

All pairs use Fe56 at 7.8 g/cm3 and 300 K, the same available FENDL data,
256 stored unit-weight 14.1 MeV isotropic source directions at (100,0,0),
same particles/batches/seed/thread/executable/library, vacuum boundaries and
tracklength estimators. Model sizes/materials are controlled proxies, not
physical device material/source qualification. Data MT444 availability is checked.

First run bounded two-batch startup controls; exclude pilots from timing claims.
Production uses 20 batches and three distinct seed pairs, alternating order.
Use 1000 particles/batch for plasma and initially 10/batch for coils, with
180 s per-process limit. A failed pilot/timeout stops that lane for diagnosis.
No automatic run escalation. Report transport separately from initialization
and process wall time, completed work and all failure diagnostics.

Score six energy bins with flux, total, absorption and damage-energy.
Cell/material ownership and spectral/integral sums must close. Preserve
cumulative statepoints and derived paired batch scores. Check exact execution
identities, exits, complete counts, finite scores, unchanged inputs and outputs.

For same-geometry controls, inspect every paired batch bin with numerical
tolerance 1e-7 + 1e-9*max(abs(left),abs(right)); this is a sampled regression
criterion, not a proof about all histories. For statistical comparisons use
paired differences (common random numbers), simultaneous family-wise 95%
Bonferroni Student-t intervals over all 32 bins. Equivalence margins: 5% for
energy bins and 1% for integral/ownership scores. Require at least ten nonzero
paired batch observations for each bin. Sparse/zero bins remain unqualified.
These planned small runs may not establish full-spectrum equivalence.

NRT test conversion: 0.8 * damage-energy / (2 * 40 eV * atom_count), per
source particle. Ed=40 eV is an explicit test convention. Plasma shell volume
is analytic. Coil comparison initially uses the same native reference volume,
so its output is a reference-normalized damage index until actual coil volume
is independently qualified. No physical source-rate, DPA/s or DPA/year claim.

The 80% target is relative transport throughput >=0.8 against the declared
native proxy under matched conditions; passing a torus specialization does
not qualify general shaped surfaces. Different-shape annulus comparisons
are descriptive, never tally-equivalence acceptance.

Documentation: https://docs.openmc.org/en/stable/io_formats/tallies.html
and https://docs.openmc.org/en/stable/methods/tallies.html describe score units
and batch-statistical uncertainty. Geometry differences and sampled statistics
must remain distinct from implementation correctness.
