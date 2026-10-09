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
