# Independent cache source acceptance, dispatch 003

## Context and decision

**ACCEPT_SOURCE** for precisely
`dev/stellarcsg/reports/coil-profile-20260926/candidate-04/optimization.patch`,
SHA256 `52361a86c15d7ee8b7556408d4ce44e08135c854beee7089628ac28223aa0157`.
This is independent source safety acceptance of the narrow immutable interval
cache under the existing admitted arithmetic/geometry contract. It does not
apply the patch, rebuild production, accept an 80% result, repair nine normals,
or qualify physical coils. Root owns integration and subsequent acceptance.

Production HEAD remains `54f8af0dbccb1ce2dcd066f27ea79667f2d6ee8f`.
The production offset source and retained baseline both hash to
`615cfa0b20b747e166e20632b29912bdcabc3c096c35e4db33169095394f53a0`;
retained candidate hashes to
`5f71bb5054f74c0e83815bcaf9a75f8509ff0ad59026ea4c551af245b20e6008`.
This reviewer applied the repository reviewing-openmc-code criteria to the
three-hunk delta and its relevant consumer/source/build evidence, not the
entire PR. No production patch application/build/native execution was performed.

## Detailed source findings

- Arithmetic endpoints: the initialization is literally
  `impl.scaled(sample(span, I(0, 1), derivative))` for derivative 0, 1, 2.
  The baseline `center` expression is
  `scaled(sample(spans[s], u, derivative))`. Scale and span coefficients are
  identical at these two sites. The cache guard requires exactly [0,1] and the
  same three derivative values; every other request uses the original code.
  Existing outward nextafter arithmetic, monotonic endpoint tightening in
  sample, and interval validation remain in the computation. No expression
  reordering, approximate coefficients, normalization, or looser enclosure is
  introduced. Equality of endpoints follows from expression/input identity
  under the supported deterministic floating arithmetic; exhaustive compiled
  endpoint comparisons were not independently executed by this reviewer.
- Initialization/lifetime: scale is assigned before the span loop. All c,
  hull and nominal fields are populated before the three full_center values;
  the span is appended only after those values are assigned. regularity calls
  sample directly after append; support compilation occurs after all spans.
  There is no call to center on an unpublished/incomplete span. Reallocation
  copies initialized value objects. A constructor exception cannot publish
  a partially built object; the pimpl unique_ptr cleans it up.
- Immutability/thread safety: the source contains one scale assignment and one
  span append site, both in construction. No later cache write, lazy mutation,
  global cache, query-key change or per-particle shared state is introduced.
  Queries read value arrays. This removes no current race guard and adds no
  cache race; threaded transport itself remains NOT_RUN. This is geometry-only
  reuse, not a particle-state cache needing position/direction invalidation.
- Arithmetic environment: constructor admission still requires FE_TONEAREST,
  IEEE binary long double with at least 64 digits and exponent range 16384.
  Every public point/ray query still calls finite_point before using the implementation.
  A changed rounding mode throws before a cached value can be used. The
  retained suite exercises FE_UPWARD rejection. Build receipts use
  `-fno-fast-math -ffp-contract=off`. This acceptance assumes the existing
  supported long-double execution environment and does not qualify arbitrary
  runtime precision-control changes, hardware modes or alternate compiler
  arithmetic. FE exception sticky-flag/trap equivalence is not a promised
  native API contract; precomputation can move such effects into construction.
- Exceptions and semantics: constructor precomputation adds arithmetic/storage
  work, so allocation failure can occur earlier and peak/construction cost
  increases. Admitted finite coefficient/radius ranges place the full-span
  polynomial and scaled derivative operations far below long-double overflow;
  no denominator involving a ray, zero gradient or ownership is precomputed.
  Root order, earlier-prefix certificates, tolerances, budgets, normal minimum/
  projection validation, boundary-band evaluate validation and fallbacks are
  unchanged. Unsupported/ambiguous normals still fail closed. Sticky flags
  and construction timing are not claimed identical.
- Storage/ABI: three V values contain 18 long doubles: 288 added bytes/span on
  the recorded 16-byte long-double ABI, 18 KiB at 64 spans and 1,179,648 bytes
  (1.125 MiB) at the admitted 4096 maximum. Extra vector allocation overhead
  remains implementation-dependent; no independent 4096-span stress run was
  made. Span is private to this translation unit. The public class still
  contains only its unique_ptr pimpl and the public header is unchanged.
  Production must rebuild this implementation coherently; do not mix objects
  constructed with baseline layout and methods compiled for candidate layout.

## Passive cross-DSO and provenance review

Observed native library SHA256 remains
`f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6`.
Candidate DSO is
`b3f2aeea1b80c00b806b6bb96435e4e0acc3e7a6b94beaea565ccde733387e68`;
baseline DSO is
`577dbee3d416b1e518fcad9dc403a26e38643918d3fee60d17a7ffb1f6789b54`.
Hashes were independently observed, not copied as assumed identity.

The candidate-04 DSOs are retained copies of source-identical candidate-02
builds; absence of candidate-04/build-candidate.json is therefore expected,
not proof of a new build. I read candidate-02/build-candidate.json and the
reuse code, which records source equality and copied binary hashes. Its link
uses -Bsymbolic-functions, and each worker receives one explicit LD_PRELOAD
variant in a fresh process. There is no two-variant live object exchange.

Passive nm/readelf inspection found candidate definitions for constructor and
destructor aliases, bounding_box, squared_distance_enclosure, normal, distance
and evaluate. The candidate's relocation table has no unresolved
CertifiedSplineOffset function references. Thus its private helper calls stay
inside the candidate, consistent with -Bsymbolic-functions. The native
libopenmc relocation table contains interposable JUMP_SLOT entries for the
constructor, destructor and public queried methods. A shared_ptr constructed
by native CompiledSweptSplineSurface therefore retains the unchanged public
object size while the candidate constructor/destructor own its changed private
storage in these fresh preload processes. The native library also exports
weak private helpers; arbitrary partial interposition would be unsafe and is
not authorized by this review. No fresh LD_DEBUG execution was performed.

This is adequate source/link-structure support for the retained isolated
experiment. It is not a universal dynamic-loader qualification. A coherent
production rebuild avoids retaining this experimental mixed-library setup.

## Finite retained evidence and limits

- correctness-gate.json reports 161 identical non-timing rows (160 queries plus
  summary) in each prefix mode. Its implementation removes timing fields only
  and compares entire remaining dictionaries, including diagnostics and errors.
  I inspected that comparator and the retained source/output/exit receipts.
- historical-scalar-transfer.json reports 160 identities/results exactly equal
  to accepted records in each mode and nine normal errors per mode. This is an
  inherited finite certificate transfer, not a fresh independent oracle replay.
  The source cache identity argument is the primary safety reason; a matching
  finite bank alone could not establish general correctness.
- The retained adversarial suite checks first thin chord missed by all initial
  proposals (on/off, <=1e-11), even-root budget unresolved, exact-origin policy,
  coincident inside/outside, nonfinite tolerance, tiny nonzero direction,
  zero-gradient and competing projection normal exceptions and FE_UPWARD.
  Both retained isolated suite processes exit 0. Their profile reports preserve
  five expected unresolved controls; these must not be counted as misses.
- Native retained first entry is 14.999999999999257 cm, then coincident inside
  exit 10.000000000000936 cm. normal_x is 1, both sense directions and miss
  sentinel are checked. The independent guard rejects later 195/205 cm events.
  Its 14.99--15.01 window is an earlier-event control, not a 1e-11 error oracle.
  The frozen bank and exact thin-chord test supply separate tighter evidence.
- primitive-01/summary.json and evidence-02/summary.json independently rehash to
  `e19e452230717c4bb3dfaf8204308e1c770d8e9d1fb618afe9ae2496236766a7`
  and `be68e22c8e98ca6d0bbf9fc5eabc6d970139eb2ccfdd195672c9e59b3fc786a0`.
  Primitive measurements are uninstrumented native API operations with
  unequal counts normalized by completed iterations and denominators lasting
  about 0.68 s. They support a finite ~1.993x internal observation; they do not
  establish native transport throughput.
- The raw-bin checker visits every baseline tallies/ dataset in all 20 paired
  statepoints, comparing exact array values and XML input hashes. It examines
  all 1280 stored sum/sum-square entries, not just aggregates. I inspected the
  checker/report, but did not independently reopen HDF5/reexecute it because
  that would be another compute block. It is sampled implementation evidence,
  not universal mesh compatibility, statistical equivalence or physical fidelity.
  Its directional traversal checks every baseline dataset, not extra candidate
  datasets; that limitation does not bear on the source-safe cache acceptance.

Purpose/scope, design, physics identity, private-code style and dependency
criteria pass for this narrow source change. No new external dependency or
transport-loop allocation is introduced. Reports document increased memory and
constructor cost. No public schema/API change requires an input-reference edit.

## Next hybrid selected by measured budget

Prioritize an **immutable conservative span BVH used by minimum and projection**,
not a normal-result cache or general planar-normal performance branch. The
baseline native diagnostic assigns 67.19% of exclusive offset service time to
minimum, 20.18% to projection and 10.09% to proposals. It scans 64 spans per
minimum (831,936/12,999), while only ~4.35 insertions/minimum survive and only
one heap node/minimum is processed. That supports accelerating the full-span
bound scan/global separation, rather than optimizing deeper root subdivision
which is uncommon in this workload. Projection has ~68 allocations/call;
bounded local scratch is a separate subsequent hypothesis.

BVH leaves must enclose each original transformed control hull, with outward
node unions. Seed a finite squared-distance upper bound with a valid exact
curve-point witness; visit nodes whose conservative point-distance lower bound
is <= that bound. Reject only strict lower>upper separation, retaining touching
and uncertain domains. Preserve global lower-bound coverage and stationary
minimum proof, all seam neighbors, and projection's global ownership/exclusion
obligation. Reuse the immutable tree for projection separation without
replacing local chart proof. A hint can change order, never omit an earlier ray
domain. No root budget/tolerance inflation or mismatched-solid services.

Measure visit counts, allocations, minimum/projection exclusive costs and full
query outcomes before claiming improvement. Require unchanged 160-bank results
and nine normal errors plus additional far-origin, overlapping-strand,
touching-box, seam and translated/scaled negative cases. Small 64-span trees
may have overhead; retain on/off comparison and reject the optimization if it
does not improve complete service cost.

The planar-normal specialization is still the most useful **specific thin-pair
correctness experiment**: exactly prove metric w.c'==0, isolate every stationary
root/seam/continuum obligation, retain both quadratic branches, global ownership
and t ordering. No fraction of transport rays qualifying for exact orthogonality
has been measured; isotropic general directions cannot be assumed to benefit.
Use it as a separate restricted correctness lane, not the next broad speed claim.

The most valuable immediate root action is coherent integration/rebuild of the
accepted single-file cache, then a freshly admitted bounded uninstrumented
transport A/B and tally-off/on control. This owner is not authorized to perform
that build/campaign. Speed and physical targets remain open.
