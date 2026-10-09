# Next plasma and coil experiments

October 9, 2026. **Decision record: proposed experiments, none executed here.**

This ranking is an engineering judgment from the [preserved 81-entry results catalog](../../method_documentation_audit/20261009-review-001/METHOD_RESULTS.md), not a demonstrated ranking on one physical workload. The old methods, attempts, failure records and dated audit are retained unchanged. Stable proposal IDs and status are in the [clarified registry revision 001](EXPERIMENT_REGISTRY_REVISION_001.json); the [initial registry](EXPERIMENT_REGISTRY.json) remains intact, with its [clarification record](REGISTRY_CORRECTIONS.json) and append-only [events](EVENTS.jsonl).

## Priorities

| Domain / order | Combination | Why it deserves the next experiment | Main question still open |
| --- | --- | --- | --- |
| Shared prerequisite, NEXT-G01 | Complete first-event contract and independent ownership/scoring witnesses | Restricted plane repair now works, while general facet ties, positive gaps and ownership still fail | Can a supported first event, successor owner and per-bin score be certified together? |
| Plasma 1, NEXT-P01 | Incumbent spline + validated closed distance ceilings + precomputed conservative bounds/BVH + candidate reuse | Ceiling optimization reports about 8.07x on the original workload; work-matched plasma ratio is still 2.10–2.12 | Can we avoid more full solves while proving that no earlier boundary was omitted? |
| Plasma 2, NEXT-P02 | Direct original Fourier/VMEC evaluation + certified parameter patches + the same scheduler | About 3.3x lower synthetic Python candidate-search cost motivates a separate evaluator ablation; geometry remains unresolved | Does the benefit survive real mode counts, actual VMEC parameterization and complete intersection work? |
| Plasma 3, NEXT-P03 | Local full quartics or torus seeds + admitted Cartesian patch domains + exact polynomial reference + actual-surface refinement | Local quartic fits have useful synthetic accuracy; Q02 can audit all roots of the represented polynomial | Can the candidates accelerate the actual target without admitting extra sheets or missing earlier roots? |
| Coils 1, NEXT-C01 | Optimized P00 facets + coupled event/owner repair + physical CAD binding | Later represented-P00 timing gate reports pooled ratio 1.1046, within the 1.25 timing target | Can we preserve useful speed after fixing the actual correctness and physical-identity gaps? |
| Coils 2, NEXT-C02 | Direct ruled rectangular faces + endcaps + certified BVH + complete root/event ordering | Matches rectangular pack surfaces more directly; prior synthetic reference is encouraging | Are the actual section/frame/CAD curves admitted, and are seams, corners and all crossings handled? |
| Conditional reference, NEXT-C03 | Restricted exact-control offset + certified Bernstein prefix + immutable interval cache | Restricted 160-query scalar bank passed; prefix and cache separately showed internal benefits | Does it help an actually admitted circular/constant-metric shape, including hits and normals? |

**First execution order:** freeze the decisive shared witnesses and target contracts; then run the smallest NEXT-P01 exclusion/oracle experiment and NEXT-C01 event/ownership experiment. Establish NEXT-P02's actual-source Fourier reference alongside the spline work, so the incumbent is never presumed to be the physical ground truth. Follow with NEXT-C02's one-span rectangular-face reference and NEXT-P03's ablation on an admitted common plasma target. NEXT-C03 is optional restricted reference work. This ordering ranks implementation risk and existing evidence, not demonstrated future speed or success probability.

Geometry-service diagnostics and proof development can proceed while broader native acceptance remains open. Native throughput admission waits for the candidate's required geometry/event/ownership gates. A faster candidate-only calculation is recorded as such.

## NEXT-G01 — shared event and ownership prerequisite

Preserve the supported scope of M23's independently accepted void, single-instance, unit-axis plane slice. Extend the contract only with new evidence; its acceptance does not automatically cover non-axis facets, transformed universes, material collisions or physical packs.

Freeze the known witnesses: conflicting equal-time cube faces and reversed facet order; the positive `2^-48 cm` gap; original and derived P00 payload identities; component overlaps 15/16 and 17/18; the missed earlier coil entry around 0.002 rather than 0.502 cm; boundary origins and coincident hints; even/near tangencies; the thin two-root pair near 49.999909268 cm; near-parallel slab/lead exclusions; periodic seams and transforms; reused-particle state resets; and local track-length/current-bin redistribution. Include the retained subnormal positive-gap control in the mathematical reference where its arithmetic assumptions hold.

Geometry/input admission is coequal with event correctness. Freeze actual VMEC coefficient/mode identities and actual coil CAD/section/frame identities before a target claim. A correct event on the wrong represented solid cannot qualify physical plasma or packs.

Supported queries must either return a certified earliest event and admitted contact/owner set, prove no event before a closed ceiling, or return UNRESOLVED. An earlier or equal unresolved interval cannot be hidden by a later clean hit. Normals and ownership at a crease require an explicit admitted contract. Candidate input order is not a physical owner definition. Follow OpenMC's actual hierarchy/region precedence, not a blanket rule to choose or reject every equal distance.

For positive gaps and tied contacts, follow event handling through successor cell/material, continuation and every affected tally bin. Reject corrupted or missing events, swapped owners, missing positive-gap tracks and redistributed bins even if totals agree. Do not treat zero lost particles or equal tally totals as proof.

**Interval-event composition gate:** Q02 can return nonpoint isolating intervals, while Q01's scalar interface keeps them UNRESOLVED. Before combining them into a complete event solver, independently review an interval-valued scheduler that refines/orders competing intervals, retains earlier unknown prefixes, admits contact ties/owners and bounds final rounding. Substituting interval midpoints or rounded roots into the scalar interface is not certified composition. Until that gate passes, use these tools as restricted references and preserve UNRESOLVED.

## Plasma

### NEXT-P01 — improve the working spline route first

Combine the incumbent bicubic evaluator with conservative immutable patch bounds, traversal ordered by the lower ray parameter, a closed collision-distance ceiling, and bounded candidate-plan reuse. Q01 provides a composition reference, but its caller-certified boxes and complete solver callback remain obligations for the actual spline surface.

Start with a small exclusion bank: compare ceilings off/on and candidate reuse off/on against the same admitted target and complete-query oracle. Each excluded patch/segment needs a conservative enclosure or equivalent proof that the actual represented surface cannot intersect it. A lookup voxel needs a conservative distance/exclusion certificate over its domain; sampled clearance is insufficient. Keep contact at the ceiling and retain uncertain/touching intervals. Validate origin-inside, outside, near-boundary, grazing and seam states.

Cache immutable geometry expressions or candidate plans using the full geometry/transform/ray/domain/ceiling/coincidence identity. Do not reuse completed solver decisions under a changed query. Record cache misses, construction/storage cost and invalidation. Most transport queries may be different, so actual reuse rate is a measurement rather than an assumed gain.

Measure total completed-query time, full-solver calls, interval work, unresolved fraction, preprocessing and memory. Include unresolved/exception paths in bank cost; do not report a survivor-only speed. Keep evaluate/normal/sense and checked-result policies in the comparator: M22's agreeing distances hid a sense failure. Its retained probe lacks the exact point/direction; recover those inputs with a diagnostic before freezing a regression, rather than claim an input-bound witness already exists. The reported 92–95% `ceiling_certified` counter is an implementation classification, not an independent certificate. The matched-source profile still attributes about 45% of time to full solves: reducing those calls is the concrete hypothesis.

Do not multiply the reported ceiling/cache gains. They were measured in different scopes and may accelerate overlapping work. v7 showed negligible isolated effect; v8's effect was undecided and added initialization. Preserve those results and validate any clearance optimization before timing it again.

### NEXT-P02 — direct Fourier with the correct target parameterization

Use original vector-parametric VMEC/Fourier geometry, for example `S(theta, phi) = (R(theta,phi) cos(phi), R(theta,phi) sin(phi), Z(theta,phi))`, with the source's documented mode signs, field-period convention, units and sine/cosine symmetry. Raw VMEC poloidal angle is not interchangeable with geometric `atan2` angle. A scalar radial field is an optional admitted specialization, not the general representation.

First compare evaluator and derivative cost across mode counts using the same source geometry, fixed query bank and explicit spline approximation budget. Verify Fourier reconstruction independently; measure spline-to-source discrepancy separately from query correctness. The old 3.3x Python candidate result is a motivation, not a projected native gain. No coefficient truncation is silently permitted; any truncation creates a separately documented approximation and bound.

Then bound actual parameter patches conservatively and investigate coupled intersections `S(theta,phi) = origin + t*direction`. Interval Newton/Krawczyk or another complete certificate can be considered on admitted regular domains. No fixed sign/stationary sample count proves all roots. Retain the high-mode missed-crossing witness and the grid singularity that currently discards earlier candidates; splitting away an unsupported interval cannot justify skipping its unknown prefix.

Advance only when admitted chart coverage, seams, normals, earliest-root completeness and uncertainty propagation are established. Fallback to another evaluator is permissible only for a certified equivalent target; a spline approximation and its Fourier source are not silently the same solid.

### NEXT-P03 — quartic/torus candidates, actual surface authority

Hold target, query bank, patch domains and error budget fixed. Compare no-fit baseline, osculating-torus seeds and full local 35-coefficient quartic seeds within the same completed-query algorithm. Attempts 0002 and 0003 used different synthetic targets, so their errors cannot rank those families against each other.

Normalize local coordinates and track fit conditioning. Give every patch an admitted Cartesian neighborhood as well as parameter/angular trims. Q02 isolates all distinct roots of supplied exact represented degree-at-most-four coefficients; it does not certify uncertain fitted coefficients, floating ray-substitution error, original 3D surface equivalence or ownership. Validate those layers separately. Its COMPLETE result is not a physical HIT. Nonpoint root intervals require NEXT-G01's independently reviewed interval-event scheduler gate; until then retain restricted reference use and UNRESOLVED.

Reject the saved extra-sheet root near `t = 0.730003116 m`, whose target-field diagnostic is about `+0.784203364 m`. Refine plausible candidates on the actual admitted surface and certify all earlier prefixes. A residual-based fit bound alone is not a longitudinal ray-error bound near tangency. No actual surface prefix may be pruned merely because the approximating polynomial has no roots there.

The old local quartic's 384-patch held-out normal-line error was about 0.01187 mm, with midpoint seam error about 0.01271 mm; these are sampled diagnostics, not continuous CAD, trim or periodic-seam certificates. Constant-weight circular-torus polynomial sums remain quartic but saturated at rank 14 in the saved family. Use this arm to test useful seeding, not to assert a complete global basis.

## Coils

### NEXT-C01 — finish the promising represented-facet path

Keep exact-bit nextafter v2, normal precomputation/early reject v3 and the reported bitwise-equivalent facet ceiling v5 as individually identifiable arms. v5 remains pending exclusion/oracle validation. v3's isolated effect was UNDECIDED at 1.076x, and gate-01 failed the robust worst-pair condition. Test the combination with independently admitted actual bounds, complete first contacts and coupled native event/owner repair; do not assume additive gains or prior physical validation. Use the October 8 axis slice as a restricted reference; do not copy its acceptance to general facets.

The represented fixture's exact bounded-solid certificate is valuable, but its overlapping components and seam-repaired identity remain explicit. Determine whether geometry repair, source-CAD correction or an explicitly modeled priority partition is physically intended. A priority partition may be a valid experimental solid without representing separate physical coil owners. Bind retained facets, sections, frames, transforms and periodic images to the admitted source geometry and its existing fidelity budget; do not invent a tolerance.

Start by replaying R02/R03's owner/continuation counterexamples with expected first event, successor and per-bin path lengths. Preserve crease/tie UNRESOLVED states until their contract is supported. Then remeasure the exact corrected variant on the same-build, same-source/seed/material/tally benchmark with initialization and worst timing pairings retained. The 1.1046 ratio is encouraging only for the represented P00/ring comparison; a CAD repair may change the target and costs.

### NEXT-C02 — a rectangular-face representation with complete events

Recover and bind the retained M17 artifact if available, or implement a new explicitly scoped reference from the documented contract. Start with one closed synthetic rectangular span having exact known cubic/rational edge curves and endcaps. Do not introduce general twist/frame laws until their polynomial/rational representation is admitted.

For the stated ruled rational cubic family, elimination can lead to degree-at-most-six polynomials after admitted positive-denominator clearing. **Q02 supports degree at most four and cannot be used unchanged as this oracle.** A separate degree-six-capable reference needs its own execution and independent review. Use it outside the transport hot path to verify all contacts sorted by ray parameter, including the six-crossing witness where parameter ordering reverses ray ordering, endpoints, even roots, nearly parallel rays, seams and corner contacts. Integration also needs the interval-event composition gate in NEXT-G01.

Add exact conservative face/control-hull bounds, the closed ceiling scheduler and candidate-only reuse after reference correctness. Verify orientability, one-sided inside/outside, incident face/edge/corner ownership and endcap coverage. A canonical face normal at a crease need not determine composite-solid sense under the native nonvirtual rules; qualify that coupling explicitly. Then bind one actual physical pack section/frame to its CAD boundary. Refining an approximation is a fidelity experiment; it is not proof that a changed rounded or circular solid represents a rectangular pack.

The reported 6.099% annular-control query ratio and 72 synthetic tests are reference motivation, not native physical-pack throughput. Native integration requires material/ownership/scoring evidence before speed admission.

### NEXT-C03 — restricted offset as an optional reference

Combine exact-control constant-metric offset, certified Bernstein prefix exclusion, immutable full-span intervals and newly certified hierarchy bounds only on its admitted circular or constant planar-ellipse metric domain. Retain all nine normal/projection gaps and add genuine hit-bearing imported cases; miss-only coil rows do not validate entry/exit.

The 4.052x summed-distance gain and about 1.993x complete primitive-workload cache improvement have different denominators; do not multiply them into native speed. The prior cached native proxy still took about 166–167 seconds. This is a correctness/reference lane, with lower priority than the P00 repair or rectangular-face route for physical packs.

## Lower priority based on the retained results

- Global constant-weight torus-sum fits: poor saved target fit and rank saturation; useful only as a bounded candidate/control arm.
- Torus plateaus with narrow spline joins as the final plasma boundary: inaccurate interiors and concentrated normal error; later sampled accuracy did not establish complete tracking.
- More blind Newton seeds, relaxed residuals or sampled no-hit fallbacks: repeated wrong first roots and tangent/origin misses.
- Full arbitrary-precision exact work in every particle query: strong restricted reference value but poor retained native cost. Use exact work to audit/fallback only under an explicit admitted contract and include its full cost.
- Broad global degree-26 elimination, wholesale new cardinal-spline offset or offline owner shortcut: larger unsettled representation/proof/import gaps than the leading routes.
- Another transport campaign before its candidate's correctness/ownership/fidelity gates: does not resolve shared geometry errors.

## Common comparison and promotion rules

1. Freeze target identity, original coefficients/CAD, parameter conventions, units, geometry bounds, ray bank and each comparator before execution. No undeclared fidelity budget or target substitution.
2. Separate analytic controls, synthetic representation diagnostics, actual-source fidelity and native physical qualification. A pass at one level does not promote the next.
3. Record every query disposition and all failures. Exact-polynomial root completeness, actual-surface completeness and native ownership/scoring are separate gates. Preserve unsupported states.
4. Compare optimization arms on the same admitted solid and full completed workload. Separate evaluator time, candidate generation, final solve/certificate, fallback, preprocessing and native initialization/transport.
5. For native torus/mesh proxy comparisons, label different solids and source banks, collisions/history and geometry calls explicitly. A closer work-matched proxy remains a proxy. The retained 80%-throughput goal corresponds to runtime ratio at most 1.25 on the defined accepted comparison; keep robust timing/noise rules, not just a median.
6. Obtain independent Sol review of decisive new logic and evidence. Local-first execution uses existing capabilities; any build/acquisition requires the current user-wide machine inventory. This plan launches no work, acquires nothing and authorizes no remote resources.

## Append-only recording of future execution

All proposal statuses in this plan are **PROPOSED_NOT_RUN**. They are not new successful attempts. Before a run, create a new method/attempt/run directory with an exclusive create operation that rejects any existing destination; freeze its source, inputs, bank, protocol and hashes. Keep raw output, stderr, exit status and result denominator even if execution fails.

Append registration, start, terminal result, failed controls, scope limitations and review as events in that attempt's log. Reference the stable proposal ID, related historical IDs and prior run IDs. A retry or changed protocol gets a new numbered run; a revised proposal gets a new numbered plan. Failed experiments and superseded results stay intact. An execution receipt must distinguish NOT_RUN, FAILED_EXECUTION, COUNTEREXAMPLE_FOUND, UNRESOLVED, INCONCLUSIVE and an explicitly scoped PASS.

This plan's immutable registry stays as the initial proposal snapshot. Subsequent attempts link back to it rather than editing its statuses to hide earlier uncertainty. A new dated catalog can reconcile later results while preserving the October 9 audit and this plan.

## Primary-source context

OpenMC's [geometry methods](https://docs.openmc.org/en/latest/methods/geometry.html) describe boundary distance, hierarchy precedence and crossing decisions. These support treating event/owner correctness as part of the tracking contract. They do not validate this fork's experimental repair.

SymPy's [polynomial reference documentation](https://docs.sympy.org/latest/modules/polys/reference.html) documents root counts and isolating intervals. It supports the distinction between a polynomial root certificate and a separate surface/ownership certificate. No SymPy installation or dependency change is proposed by this record.
