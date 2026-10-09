# Fourier torus method ledger

This is the index of this prototype's attempts. Earlier source, inputs,
counterexamples and results remain available. The broader project's historical
routes are indexed in the preserved [method map](attempts/0002-patch-hybrid-20261009/inputs/METHOD_MAP.md)
and [development synthesis](attempts/0002-patch-hybrid-20261009/inputs/CONSOLIDATED_DEVELOPMENT_20260926.md).
Those historical results were read, not rerun or promoted in this trial.

## Preservation rule

Keep each attempt and run directory immutable. Use a new numbered run for a
new execution, even after a failure. Append registration, findings, corrections
and review events to [METHOD_EVENTS.jsonl](METHOD_EVENTS.jsonl). Never replace
an earlier result with a later result or convert UNRESOLVED into a successful
geometry query. The experiment runner rejects an already-existing output
directory before writing source or results.

The initial prototype at commit `6333d4337c37aae83803012b76d67ba09ef4092f`
is preserved byte-for-byte under [attempt 0001](attempts/0001-initial-20261009/manifest.json).
Its original code, README, tests, runner and receipt also remain unchanged in
their original locations. Attempt 0002 verifies those five identities.
The [overwrite-rejection audit](attempts/0002-patch-hybrid-20261009/preservation_audit.json)
also verifies that trying to reuse run 001 leaves all 11 saved run files intact.

## Attempt 0001 — original composition and torus assistance

| ID | Method tried or assessed | Recorded result | Remaining obligation |
|---|---|---|---|
| FT-001 | Parametric Fourier displacements added to a reference torus | Exact one-harmonic reconstruction in synthetic controls | A general surface intersection remains a coupled solve |
| FT-002 | Global torus fit, coefficient-sum position bounds, quartic candidates and interval refinement | 10 functional controls pass; tri-state behavior retained | Exclusion and single-root certificates must be supplied externally; no general Fourier ray certificate generator |
| FT-001-B | Boolean combinations of complete coaxial torus solids | Mathematical rotational-symmetry counterexample for this restricted family; no new Boolean compiler executed | Displaced/trimmed primitives are different constructions |
| FT-001-C | Nonlinear coordinate maps to a reference torus | Documented interpretation; not implemented in this attempt | Curved transformed rays, lengths and normals |

The independent review found that an endpoint sign change could select a
later root inside one candidate window: `(t-0.1)(t-0.2)(t-0.8)` on `[0,1]`.
The fixed API retains CANDIDATE as UNRESOLVED and requires an externally
certified single-root window for HIT. This counterexample remains in the
original tests and is included again in attempt 0002's combined controls.

## Attempt 0002 — the pasted torus-patch and hybrid proposals

The first and second pasted files are identical SHA256
`55f3085fd02e89e00c8d1ab0ff1b904b96c115bff8e95b35c7f57a679bfb8b17`.
Both original paths are retained in the [input manifest](attempts/0002-patch-hybrid-20261009/input_manifest.json),
with one frozen content snapshot. They are one proposal, not two independent
experiments. The hybrid text has a separate frozen identity. All execution
uses existing local NumPy/SciPy, one CPU worker, and synthetic coefficients.

The target is `R=5+[0.8+0.12*cos(3*phi)]*cos(theta)` and
`Z=[0.8+0.12*cos(3*phi)]*sin(theta)`, in metres. Its Fourier input includes
both positive and negative stored xn modes. No real WISTELL input is used and
no physical accuracy tolerance is invented. Errors below are observations,
not passes against the project's physical fidelity budget.

| ID | Method tried | Current result and status |
|---|---|---|
| FT-003 | Fourier-guided curvature-matching two-dimensional torus patches | Local position, normal and two principal curvatures matched for admitted ring-torus fits. Refinement reduces sampled deviation, but adjacent projected patches have gaps: **approximate atlas, no closed solid** |
| FT-004 | Compile constant-weight translated/rotated circular-torus polynomials into one quartic; fit the synthetic target | Compilation works. Rank saturates at 14, fitting error remains: **finite-dimensional approximation, no progressively complete Fourier basis** |
| FT-005 | Exact torus plateaus plus localized cubic-Hermite spline strips in one BVH | A closed C1 synthetic radial-profile surface is constructed. Torus interiors remain inaccurate, and narrow strips increase normal error: **mixed geometry demonstrated, general queries unresolved** |
| FT-006 | All-spline periodic radius profile with the same target nodes and one BVH | More accurate in this restricted synthetic family. This is a new comparator, **not the incumbent production spline solver** |

[Run 001 receipt](attempts/0002-patch-hybrid-20261009/run-001/receipt.json)
binds frozen source, inputs, the 52-ray bank and raw outputs. All **20** combined
functional controls passed. Every general query result is deliberately
UNRESOLVED; candidate-distance agreement is not a completeness proof.
The [independent Sol review](attempts/0002-patch-hybrid-20261009/independent_review.json)
accepts this narrow experimental scope. It identified a tangent contact that
the sampled spline search misses; the input and replay are preserved in
[counterexamples](attempts/0002-patch-hybrid-20261009/independent_counterexamples.json).
The query remains UNRESOLVED rather than being upgraded to NO_HIT.

### FT-003: two-dimensional torus patches

Analytic first/second Fourier derivatives define the metric, outward normal,
principal curvatures and directions. Curvatures alone do not uniquely select a
torus latitude; the generic construction chooses an outer/inner equator
representative. A separately recognized exact circular Fourier input uses
exact torus dispatch, rather than claiming local curvature determines that
whole torus. Zero-curvature and inadmissible ring fits remain unsupported.

| One-field-period atlas | Supported patches | Maximum sampled target-to-torus distance | Maximum sampled projected-neighbor gap | Maximum sampled normal error |
|---|---:|---:|---:|---:|
| Exact circular control, 8 x 12 | 96 | 1.67e-15 m | 1.79e-15 m | 1.48e-6 degrees (floating acos floor) |
| Deformed target, 8 x 12 | 96 | 8.927 mm | 14.326 mm | 3.011 degrees |
| Deformed target, 16 x 24 | 384 | 1.185 mm | 1.932 mm | 0.803 degrees |

Distance is measured from sampled target points to their fitted torus surface;
it is not a certified two-way Hausdorff bound. Neighbor gaps compare the two
projections of the same target edge samples; they are not a proof about every
trim edge. Trim windows derive from mapped samples, so whole-domain coverage
is open. The standalone trimmed-root control rejects roots on the other side
of a torus. A BVH/closed-volume compiler for this 2D atlas is not yet present.
The radial-profile hybrid below does not stitch this general atlas.

### FT-004: compiled constant-weight quartic

**Correction to attempt 0001's broad implicit-sum wording:** for polynomial
torus equations `P_i`, `sum(w_i*P_i)` with constant weights remains degree at
most four. Nonpolynomial distance blends are a different interpretation.
The earlier wording and source remain preserved; this correction is added
here rather than erasing the attempt.

For rigidly positioned circular torus polynomials, the fourth-degree term is
always a multiple of `|x|^4`; cubic terms have the form `|x|^2*l(x)`.
Together with six quadratic, three linear and one constant coefficient, this
family spans at most **14** independent coefficients, within the 35-monomial
space of all degree-four polynomials. This restriction is specific to this
circular-torus polynomial family. The fit enforces weight sum one to rule out
the meaningless zero-polynomial fit.

| Torus polynomials | Observed rank | Holdout algebraic RMS (dimensionless) | Maximum sampled radial first-candidate error |
|---|---:|---:|---:|
| 8 | 8 | 0.0105560 | 125.96 mm |
| 24 | 14 | 0.0101280 | 159.68 mm |
| 64 | 14 | 0.0101280 | 159.68 mm |

Compilation is exact algebraically up to floating arithmetic; the tested
global fit retains measured error, and no physical fidelity acceptance is
evaluated. The
holdout algebraic residual is not a geometric distance. Candidate errors use
12 known radial rays and do not certify other roots, topology or normal sense.
Local quartic fitting remains a separate possible follow-up.

### FT-005/006: torus interiors with local spline joins

Here the hybrid is the restricted separable surface with a positive periodic
tube radius: constant radii on plateaus and cubic Hermite transitions between
them. The Hermite endpoint derivatives are zero, so the joins match torus
positions and tangent planes (C1/G1); C2 is not claimed. The field and normal
use that same approximate radius. This tests local spline joins, not spline
deformation of every torus or a general tensor-product patch stitcher.

| Radius nodes | All-spline maximum sampled error | Hybrid error, 10% strip | Hybrid error, 30% strip | Hybrid error, 60% strip |
|---|---:|---:|---:|---:|
| 12 | 2.402 mm | 78.077 mm | 64.359 mm | 45.591 mm |
| 24 | 0.128 mm | 41.603 mm | 33.325 mm | 22.071 mm |
| 48 | 0.007575 mm | 21.109 mm | 16.808 mm | 10.970 mm |

Smooth joins do not correct the constant-radius interiors. Narrowing strips
concentrates the radius derivative: at 48 nodes the maximum sampled normal
error is 46.73 degrees for a 10% strip, versus 7.03 degrees for a 60% strip.
A coefficient/target-derivative argument gives a conservative same-parameter
position bound for this synthetic hybrid, separately from sampled errors.

One shared BVH dispatches torus candidates to the quartic routine and spline
candidates to sampled bracketing/refinement. It visits every plausible patch
and does not terminate after finding a torus seed. In the 48-node, 10%-strip
case, only **3** selected first candidates are spline candidates, yet **44 of
52 queries** consider a spline patch. Selected-hit frequency therefore does
not measure spline work. The current bounds remain loose and all general
ray results stay UNRESOLVED, including misses, grazing and coincident inputs.
Independent radial equations verify candidates for the represented surface;
they do not validate the original target's generic first intersection.

### Cost observations and next obligations

Raw JSON records construction, traced construction memory, candidate-query
time and counters separately. The profile constructions took 0.0024–0.0115 s;
Python traced construction peaks were 17–95 kB, excluding untracked native
allocations and interpreter/runtime memory. The instrumented 52-ray diagnostics
took 0.039–0.260 s depending on the model. These are single short observations
with different geometric errors and unresolved completeness; they are not a
speed gate or native transport claim. Software acquisition is zero; WOUT
loading, native compilation and transport were not performed.

For FT-003 the next requirement is a whole-domain fidelity/trim construction
and closed joins. For FT-004 it is local fitting with explicit patch topology,
since adding more global circular-torus basis functions has saturated. For
FT-005 it is a fit that preserves interior accuracy while enforcing joins,
plus complete root isolation and tighter mixed-patch bounds. All require a
frozen physical tolerance and independently reviewed first-root/ownership
evidence before real VMEC or transport acceptance.

## Historical routes retained, not restarted

The imported project catalogs preserve swept spans/shared BVH, periodic
plasma patches, exact analytic torus dispatch, certified global offset and
interval cache, P00 facets/components, Bernstein and Bezier atlas candidates,
and earlier torus-arc attempts. The pasted claim about a 160-query all-blocked
torus-arc bank is retained as proposal text; this trial has not independently
reconstructed that raw bank. It is not presented as a result of FT-003.

## Publication record

The [final publication manifest](attempts/0002-patch-hybrid-20261009/publication_manifest_final.json)
records the saved working-file hashes. The earlier preflight manifest is
retained; its Git attribute hash predates the final whitespace settings used
to preserve snapshot bytes during publication. No experimental output changed.

## Attempt 0003 — third idea set: direct Fourier and general local quartics

The [third-set proposal](attempts/0003-direct-fourier-algebraic-20261009/inputs/proposal-3rd-set.txt)
is preserved with its input identity. It correctly points toward comparisons
beyond the already-existing quasi-polar radial spline chart. The local
repository source confirms that chart and its bicubic evaluator; a bounded
source search did not establish the absence of a Fourier kernel on every
other branch. Historical performance figures in the proposal are attributed
claims, not independently rerun measurements here. Swept-coil development is
separate and was not modified or restarted.

| ID | New method | Result and scope |
|---|---|---|
| FT-007 | Direct finite radial Fourier field, analytic gradient, and diagnostic stationary-point ray search; matched with the actual frozen repository bicubic radius evaluator | Exact construction for this three-mode synthetic radial target. Candidate retention corrected after an unsupported later chart interval discarded an earlier candidate. Python costs measured; general first-root completeness remains unresolved. |
| FT-008 | Local full 35-coefficient implicit quartics, signed normal-offset fit constraints, degree-four ray substitution and angular trimming | Refinement reduces measured fitting errors, but seams remain. This is a distinct polynomial family from FT-004's rank-14 torus sums; no closed solid or topology certificate. |

### Preserved development and runs

[Development check 001](attempts/0003-direct-fourier-algebraic-20261009/development-check-001/status.json)
retains two NumPy 2.5 scalar-conversion errors in test assertions and their
original source. The assertions were corrected without changing the geometry.
[Run 001](attempts/0003-direct-fourier-algebraic-20261009/run-001/receipt.json)
passes 28 controls but loses the known-radial-12 candidate when a later
derivative refinement reaches a tube-axis singularity: one of 24 known radial
rays has no direct candidate. Its entire output and source remain immutable.

[Run 002](attempts/0003-direct-fourier-algebraic-20261009/run-002/receipt.json)
passes **29 controls**. Scalar unsupported intervals are retained separately
without discarding earlier candidates; all queries remain UNRESOLVED. Input
hashes are checked against expected manifest identities before and after the
run, and source hashes bind frozen source with a live-source equality check.
The [preservation audit](attempts/0003-direct-fourier-algebraic-20261009/preservation_audit.json)
confirms all 34 earlier attempt/original artifacts and all 12 run-001 files are
unchanged. Reusing run 002 is rejected before output writes; its 12 files are
unchanged too. Earlier ledger/events are frozen as inputs before new entries.

### FT-007: represented surface, accuracy and costs

This target is `rho(theta,phi) = 0.8 + 0.12*cos(2*theta-3*phi)
+ 0.025*sin(theta+6*phi)` about the constant major-radius-5 m axis. Stored
physical n modes are `[0,3,-6]`, used once. Coefficient bounds give positive
radius `[0.655,0.945]` m and `R>0` on the represented surface. Geometric theta
is known by construction; raw VMEC parameter theta cannot generally be
substituted into this chart without reparameterization. No real WOUT was used.
The classifier, gradient, normals and ray candidates evaluate the same model.

The comparator loads a byte-preserved copy of the repository's
`samples_to_periodic_coefficients` and `sample_periodic_bicubic` functions.
Both methods use the same constant-axis Cartesian wrapper and candidate search.
This compares the incumbent **radius evaluator**, not its whole moving-axis
compiler, native C++ tracker, accelerators or OpenMC histories.

| Model | Maximum sampled same-parameter error (4,745 points) | Maximum sampled normal error | Maximum first-candidate error on 24 known radial rays | Median 76-ray Python diagnostic cost (3 repeats) |
|---|---:|---:|---:|---:|
| Direct Fourier | 0 by construction | 1.71e-6 deg floating acos floor | 8.88e-16 m | 0.2629 s |
| Incumbent bicubic 8 x 12 | 3.466 mm | 1.019 deg | 3.276 mm | 0.8790 s |
| Incumbent bicubic 16 x 24 | 0.1452 mm | 0.09181 deg | 0.1128 mm | 0.8587 s |
| Incumbent bicubic 32 x 48 | 0.008117 mm | 0.01061 deg | 0.006464 mm | 0.8831 s |

All 24 known radial candidates are present in run 002 for each model. The
other 52 rays reuse the earlier bank against this *different* target and have
no qualified general first-root oracle. There are 304 stored query rows, all
UNRESOLVED. Unsupported chart intervals occur on 18/17/18/17 rays respectively;
empty searches are not accepted misses. Stationary splitting recovers the
old exact circular tangent at `t=1.234` m, but finite sampling can still miss
oscillatory crossings and multiple stationary points in one interval.

The ~3.3x Python candidate-cost observation is specific to three low modes,
this NumPy implementation, this unqualified search and these approximated
comparators. It includes classifier/gradient/refinement work but not BVH or
cell tracking. Rotated model ordering, three raw times, vector and scalar
field/gradient costs and evaluation counters are saved. Single-process timing
noise and different represented geometric errors remain. No native-throughput
or transport speed conclusion follows. The proposal's 80%-native throughput
(or time ratio <=1.25) goal is recorded as **UNMEASURED**, not adopted as a pass.

### FT-008: full local quartics

Each local polynomial has all 35 Cartesian monomials of degree <=4 in a
normalized tangent frame. Samples on the target and at +/-0.04 local-scale
normal offsets have nonzero signed labels, preventing a vacuous zero fit.
These labels are not a certified signed-distance field. Every fitted design
has observed rank 35; the worst condition grows from 4.49e5 to 2.54e6 with
refinement, a numerical stability obligation for future work.

| One-period atlas | Holdout samples | Maximum sampled normal-line displacement | Maximum normal error | Maximum sampled interior midpoint seam gap |
|---|---:|---:|---:|---:|
| 8 x 12 (96 patches) | 864 | 0.3056 mm | 0.5272 deg | 0.2045 mm (172 seams) |
| 16 x 24 (384 patches) | 3,456 | 0.01187 mm | 0.04748 deg | 0.01271 mm (728 seams) |

No sampled projection or offset-sign failures occurred, nor multiple roots
inside the admitted normal-line window in these samples. Twelve trimmed
local normal-ray controls per atlas have candidates near the target contact;
they remain UNRESOLVED. The nearest polynomial zero on a target-normal line
is the measurement, not a whole-domain or two-way Hausdorff bound. Only
interior seam midpoints were assessed; periodic seams, edge continuity,
spurious sheets beyond the sampled window, closed-solid ownership and complete
first roots are open. No BVH or query-speed comparison for this atlas exists.
This target differs from attempt 0002, so its errors cannot be used as a
matched ranking against the earlier torus-patch numbers.

### Next acceptance obligations

Preserve these runs and negative evidence. A next attempt needs validated
VMEC-to-radial reparameterization, a predeclared physical tolerance, complete
root isolation including grazing cases, patch coverage/seams and ownership,
then matched native queries and full histories. Existing torus-arc/Bezier and
coil attempts stay indexed; none was silently repeated or overwritten.

### Independent counterexamples retained

The [independent counterexample record](attempts/0003-direct-fourier-algebraic-20261009/independent_counterexamples.json)
preserves two remaining limits in run 002's algorithm. First, a positive
radial chart with poloidal mode 2048 has a sign-changing crossing near
`t=0.5499457567` m that is absent from 78 returned candidates; the closest
candidate is about 3.09 mm away. This is an algorithm stress case beyond the
three-mode benchmark, not a new fidelity result or complete first-root oracle.
Second, the exact circular ray from `(7,0,0)` along `(-1,0,0)` has first crossing
1.2 m, but a sampled tube-axis singularity at 2 m aborts the vector grid and
returns no candidate. The retention correction covers scalar refinement
failures; it does not resolve singular sample grids. Both results remain
UNRESOLVED and are preserved as negative evidence, not accepted misses.

The [quartic counterexample](attempts/0003-direct-fourier-algebraic-20261009/quartic_counterexample.json)
also preserves an angularly admitted extrapolated sheet. For the first
96-patch fit, an outward ray admits a polynomial root at about 0.730003 m
whose target field is 0.7842 m. Its point is about 0.7800 m from the patch
center, beyond the 0.1012 m holdout normal-line window. Angular trims alone
do not restrict roots to the fitted spatial neighborhood or eliminate extra
sheets. The result is correctly UNRESOLVED.

After run 002, the three new live sources were formatted with already-local
Black. The [formatting record](attempts/0003-direct-fourier-algebraic-20261009/formatting_manifest.json)
binds before/frozen and after/live hashes and verifies identical Python ASTs
for all three files. No experimental source snapshot or result was changed;
run-002 source hashes identify the exact executed bytes.

The [independent Sol review](attempts/0003-direct-fourier-algebraic-20261009/independent_review.json)
accepts attempt 0003 as reproducible synthetic experiments, after challenging
these failure cases and independently checking source, input, output and
preservation identities. It does not accept production geometry, general
first intersections, physical fidelity or native speed. Full helper API
validation and numpydoc expansion remain a minor future integration item.
