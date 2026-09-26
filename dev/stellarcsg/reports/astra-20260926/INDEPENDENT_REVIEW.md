# Independent contract and comparator review — 2026-09-26

## Context

Reviewed the requested uncommitted contract/comparator changes against pinned
`63359cb83d36b419a7e9ba60c45f867073703c21`, following
`.claude/skills/reviewing-openmc-code/SKILL.md` and repository AGENTS.md.
This is a scoped review, not an upstream develop review or completion judgment.
Reviewed comparator SHA-256:
`181622164549f3506a0cd08dad0404396097c163b35a7f606e8320a0df95d10d`.
Reviewed contract SHA-256:
`6ddfc97b6b2f71ab1e9c2f3b4071b38a163173d3b1b7059fcb6d43326dce1866`.
The offset engine was not yet present for this stage of review.

## Summary

The exact-control offset solid is mathematically coherent, with an explicit
representation change and a viable continuous seam proof. It can establish a
new admitted subset milestone. It does not establish correctness of the legacy
rounded frame program, qualify the physical rectangular winding pack, or meet
the unchanged 160-query no-unresolved milestone. The comparator repair rejects
the previously demonstrated nonfinite distance failure but still has reproduced
false PASS paths. Numerical/transport acceptance remains pending.

## Blocking issues

1. **[Major] Failed nearest evidence can produce PASS.**
   `compare_frozen_oracle.py:72` only type-checks
   `candidate_nearest_failures`; neither `read()` nor `main()` requires it to
   agree with failure evidence or be zero in the exact lane. Starting from the
   retained exact-reference JSONL, changing its summary to
   `candidate_nearest_failures=1` is accepted by `read(exact=True)`. Using that
   same mutation on the candidate lane against the unchanged exact lane yields
   `main()` exit 0 and report PASS. A row with `candidate_ok=False` and both
   state fields PASS also yields exit 0/PASS. Require contradictory nearest
   evidence to reject, and validate the producer's Boolean/state/count
   relationships. Add these exact negative cases to the focused tests.

2. **[Major] The comparator does not bind the represented geometry.**
   Candidate/exact comparison at lines 129–140 binds matching IDs and two
   free-form hash strings, not interpretation mode or the frozen-bank identity.
   Adding `geometry_representation="exact_control_offset"` to every candidate
   row while leaving the legacy exact rows unchanged still returns exit 0/PASS.
   The new solid and legacy oracle need distinct representation identities.
   Either require matching recorded modes and an independent oracle for that
   mode, or label legacy/new comparisons as compatibility measurements rather
   than same-geometry qualification. Preserve the frozen ray CSV unchanged.

3. **[Major] Claimed frozen/retained identity is only cross-file equality.**
   Replacing all 160 IDs with `replacement_0` through `replacement_159` is
   accepted. Replacing all coefficient/source strings with `bogus` is accepted,
   including in `read(exact=True)`. The current parser also accepts invalid
   reference states. Bind the canonical IDs and coefficient/source provenance
   to the frozen CSV or a trusted manifest, validate relevant metadata, and
   validate hash syntax. Equality between two mutually corrupted files is not
   frozen-bank identity. The exact artifact also needs independently checked
   identity; an arbitrary all-PASS JSONL is not an exact oracle.

4. **[Moderate] Duplicate JSON object keys are silently accepted.**
   A textual row with `"candidate_found":true,"candidate_found":false` is
   accepted because ordinary `json.loads()` retains the last value. Reject
   duplicate object keys using an object-pairs hook. Reject nonfinite JSON
   constants globally if strict JSON evidence is the intended schema.

## Contract assessment and acceptance conditions

- **✓ Mathematical definition:** `F=min_s |A(p-C(s))|²−1` defines a continuous
  offset-union solid. Distance to the scaled compact curve is Lipschitz with
  constant `|Ad|` along the ray. A strict inside witness and outside exclusion
  over all spans are sound. A sign bracket proves existence, but does not by
  itself prove the first root or its uniqueness.
- **✓ Seam mechanism:** exact-control cubic B-spline C2 identities make the
  joined closest-branch function C1. Strict positive h_s over the joined arc,
  opposing endpoint signs, and exclusion of all nonlocal competitors can prove
  a unique global minimizer without resolving the tiny endpoint distance
  improvement. Interval derivative hulls must cover both owned polynomial
  pieces, with midpoint evaluation on its actual piece; no extrapolated
  single-span polynomial may replace this.
- **[Major acceptance gate] Common classifier:** the implementation must use
  this new F in classification, distance, and normals. Legacy rounded-angle
  ellipse evaluation cannot serve as an authoritative sign check for the new
  mode. Explicit ambiguous/boundary results must be preserved by the native
  adapter; a double-only legacy evaluate interface cannot silently encode an
  unproved sign as zero or an arbitrary finite value.
- **[Major acceptance gate] Prefix coverage:** an accepted narrow bracket must
  have a certified prefix with no gaps, including arithmetic uncertainty at
  slab endpoints. Strict sign at a slab midpoint is insufficient without a
  Lipschitz/interval certificate for the entire slab. A local transverse proof
  must cover the whole final bracket, not just its endpoints. Return distance
  error must include bracket radius and binary64 rounding.
- **[Major acceptance gate] Alternative branch derivative proof:** if multiple
  possible minimizing branches are retained, every branch must have the same
  strict derivative direction throughout the bracket. Closest-branch ties with
  different normal vectors must block normal/transport admission even when
  scalar crossing uniqueness is proven.
- **✓ Scope disclosure:** the contract correctly calls the interpretation
  opt-in, preserves the legacy mode, identifies the physical winding-pack
  exclusion, and retains unsupported/tangent/exhausted queries as unresolved.
  The first native member-2 seam crossing would be a new subset success, not
  completion of the original general-swept/frozen-bank milestone.

## Other review criteria

- Correctness/testing: malformed-distance guards improve the parser, but the
  reproduced negatives above are missing. No engine or native numerical claim
  was accepted in this stage.
- Physics: the offset solid is a diagnostic geometric model, not physical coil
  qualification. Thick/self-near curves may have ambiguous normals; the
  explicit rejection policy is necessary without a reach certificate.
- Design/docs: the contract is clear about the representation change; require
  the same identity in serialized/native APIs and receipts.
- Memory/performance: not evaluated until engine code exists. O(NB) can be
  correct but does not imply near-native throughput.
- Dependencies: this review acquired no software and introduced no dependency.

## Evidence procedure and remaining work

Used existing Windows Python with standard-library imports and in-memory
`Path` mocks. The three decisive cases—nearest-failure summary, contradictory
candidate_ok, and changed representation—were exercised through the actual
`main()` function and each returned exit 0/report PASS. Other malformed cases
were exercised through actual `read(exact=True)`. No build, install, SSH, bank
regeneration, or numerical engine execution occurred. Source files were not
edited by this reviewer; only this report is authorized output.

Next review: inspect the actual offset engine and native adapter, then challenge
arithmetic containment, joined-seam ownership, strict prefix exclusion,
classification ambiguity, normal ties, and deterministic exhaustion against
the integrator's recorded executions. This report does not judge final task
completion.

## Follow-up source audit — engine present, execution acceptance pending

The comparator has subsequently been repaired. Independent in-memory reruns
now reject all six earlier mutations: nonzero nearest-failure count,
candidate_ok/state contradiction, changed representation, renamed bank IDs,
bogus hashes, and invalid reference state. The updated source rejects duplicate
keys/nonstandard JSON constants and binds canonical metadata/order to the
tracked frozen CSV. Earlier comparator findings describe the reviewed initial
revision; these reproduced paths are now closed. This comparator deliberately
supports only the legacy representation, so it cannot qualify the new mode.
The executable receipt must still bind the actual trusted oracle/CSV hashes;
parser acceptance alone does not establish independent oracle authenticity.

Reviewed the initial `certified_spline_offset.cpp`, its live stationary-minimum
and monotonic-bracket repairs, and the native/Python representation integration.
The following logic is sound under valid outward arithmetic:

- Global stationary pruning is justified for an exact C2 periodic curve.
  Interval Newton contraction retains every possible stationary root.
- The Taylor lower bound `q(mid)+2*h(mid)*delta+h'([u])*delta^2` bounds the
  squared-distance function over the owned interval.
- A joined three-chart arc with strict positive stationary derivative and
  opposing endpoint signs has one minimizing projection. Nonlocal squared
  distance lower bounds larger than a uniform witness upper bound establish
  global ownership for every point in a ray box.
- The interval Newton offset hull retains the seam roots without rounding them
  through global angles. A strict common directional derivative plus a sign
  bracket proves crossing uniqueness. Ambiguous midpoint contraction using a
  positive derivative lower bound is sound.

Actionable source issues sent to the integrator (check their final repair):

1. **[Major] Rounded midpoint coverage:** the ray cover initially used
   `mid=(l+r)/2` and `rad=up((r-l)/2)`. A rounded midpoint can be displaced from
   the exact midpoint, making that radius too small for one endpoint. Use
   outward `max(mid-l,r-mid)` distances from the actual chosen midpoint.
   Returned distance enclosure error also needs outward subtraction bounds.
2. **[Major] Normal direction certification:** an absolute component-width
   threshold before normalizing the gradient midpoint does not bound the
   resulting unit direction when the gradient is zero or tiny. Require a
   strictly positive norm lower bound and bounded uncertainty after
   normalization. A centerline query or tiny-gradient query must not return a
   direction manufactured by rounding noise.
3. **[Major] Invalid interval arithmetic:** the initial primitive operations
   lack finite/NaN/result-order checks although the contract requires invalid
   intervals to reject. The initial arithmetic gate admits binary64 long
   double, whose intermediate products can overflow for finite binary64 input
   controls/radii. Also gate unsupported compiler/FMA/flush-to-zero conditions
   or enforce the recorded supported arithmetic envelope. NaN-poisoned min/max
   must never reach no_hit.
4. **[Moderate] Invalid options/data:** require finite positive tolerances, and
   finite positive characteristic length in the public offset constructor.
   Positive infinity currently passes positivity checks; coincident minimum_t
   can consequently become infinite and return no_hit. Fixed iteration caps
   should bound user-specified bisection work.
5. **[Moderate] Ray metric identity:** binary64 `normalized(direction)` is not
   an exact unit vector. Specify the rounded direction as the ray contract or
   account for normalization error when claiming physical cm and absolute
   distance tolerance, particularly for large travel distances.

Native integration correctly selects the new representation and disallows
legacy local coordinates/reference-oracle access in that mode. Exceptions from
ambiguous evaluate/normal queries propagate instead of inventing a sign or
normal. Native executable behavior, rounding containment, first member-2 hit,
exhaustion, origin/tangent controls, and eventual transport usability remain
unverified by this reviewer until final source and decisive receipts exist.

## Independent exact seam reference and repair reread

Created and executed `qualification/exact_offset_seam_reference.py` using the
existing `/opt/openmc-venv/bin/python` in WSL distribution `OpenMC-Dev-D`.
The exact reference uses h5py only to read the original controls; every
geometric calculation thereafter uses Python Fraction. It does not use the
runtime engine, compiled monomial powers, a stationary root solver, or the
candidate result. Input SHA-256 is
`39f77da5ab1fe427cce58b153e9b52cf8915e9973a9b8f3dfad5ab3b00a9e46d`.
Script SHA-256 is
`8f179c3d198268f440e45ec40906ba85710ebd614ddc840b6b1fd2c994c786fc`.
Receipt `exact-seam-reference.json` SHA-256 is
`0a9d2d14747e69a7ec7be0af53d59b489cddf9a71cab69a38948a1083b83df86`.

Independent result:

- Original member-2 controls have exactly constant radii a=24, b=14, planar
  centerline z=0, and positive axial supplied normal controls.
- Exact cardinal B-spline Bezier hulls give global x support lower 520 and
  upper `520 + 1/13194139533312`. The initial all-span convex hull already
  satisfies the requested 1e-10 accuracy and the script's stronger 1e-12
  stopping tolerance, so adaptive subdivision required zero additional tiles.
- Every ray parameter below `211106232532991/13194139533312`, approximately
  15.999999999999924, is strictly outside: its x coordinate exceeds every
  center x by more than the radius b=14. This excludes the entire earlier ray
  without nearest/stationary numerical assumptions.
- The exact seam center witness is
  `(520,61586673559/59421121885698253195157962752,0)`. At t=16+1e-9 its scaled
  squared distance is strictly below one, with exact positive margin
  approximately 1.428571428520408e-10.
- Continuity proves a first boundary in
  `[15.999999999999924,16.000000001]`, width approximately 1.0000757912251477e-9.
  This is an independently accepted reference existence/enclosure result for
  this one new-mode ray. It does not certify crossing uniqueness, normal,
  native implementation, legacy geometry, the full bank, or transport.

The repaired engine source was reread. Midpoint coverage and return error now
use outward actual-midpoint distances; normal certification uses a positive
gradient norm lower bound and unit-component enclosures; interval constructors
reject invalid/nonfinite results; the supported format requires at least 64
mantissa bits and exponent range 16384; controls/query/radii are restricted to
a safe exponent envelope; finite tolerances/characteristic length and fixed
bisection work cap are enforced. These close the concrete initial source
findings under the recorded strict compiler/arithmetic environment. Source is
still being integrated; acceptance must bind the final built-source hash.

Remaining limitation: the contract calls t physical cm while the runtime uses
a rounded normalized direction. Clarify this metric or bound its error for
arbitrary directions/distances. The independently referenced axis ray has
exact direction (-1,0,0), so this does not affect that narrow milestone.
Native `Surface::sense()` calls `evaluate()` before its coincidence-normal
branch; an explicit ambiguous/boundary exception may therefore prevent later
tracking at contact. Preserving that failure is sound, but a first native
distance hit is not full transport admission. Final executable receipts are
still needed for runtime acceptance.

A subsequent independent Fraction calculation tightens the witness endpoint to
t=16+1e-12: its exact positive inside margin is
`5892774601717990109961481369416280291034687605914442897032170831/41249422212027403963380800718584371946769040092954624000000000000000000000000`,
approximately 1.4285714285713774e-13. With the same global support exclusion,
the first boundary lies in `[15.999999999999924,16.000000000001]`.
The saved `probe-01.jsonl` distance, 16.000000000001382, has exact binary64
value `4503599627370885/281474976710656`. Its greatest possible error relative
to any first boundary in that independently proved enclosure is
`1231/844424930131968`, approximately 1.4577968462011388e-12, below 1e-11.
This accepts that one saved scalar distance numerically against an independent
exact geometric argument, conditional on the execution receipt correctly
binding its source/executable. It does not transfer acceptance to later builds
or establish the other solver/native milestones.

## Partial arcs, near tangency, and exact support contacts

The latest partial-arc repair was audited independently. Every omitted tail of
a partially owned span receives nonlocal distance exclusion; the local arc has
length at most three charts and n>=4, so wrapped span ownership is not
duplicated. Strict slope/end signs and exact C2 joins prove a unique owner over
the arc. The original four-control scaled hull is a valid pruning bound by
nonnegative cardinal basis weights summing to one. No new mathematical blocker
was found in this repair.

The near-tangent derivative repair is principled. In scaled coordinates let
R=Ap-AC, D=AC', and w=Ad. Stationarity gives R.D=0, and any pivot with D_k
bounded away from zero yields

`R.w = sum(i!=k) R_i * (w_i - w_k*D_i/D_k)`.

The implementation selects a sign-certified pivot, intersects this bound with
the direct dot-product bound, and hulls retained stationary charts. Both bound
the same scalar under the exact-control metric. A unique projection and a
common strict derivative over a same-sign-endpoint slab prove no root in the
slab. This avoids applying the much larger unconditional Lipschitz constant
near a shallow crossing; it does not enlarge tolerances. Numerical replay of
the repaired a15 case is still an execution acceptance gate.

The first saved 160-ray changed-mode receipt reports 66 hits, 91 no-hits and
three unresolved (a06,a08,a15), with no resolved differences from the retained
legacy reference. Its explicit descriptive-only label is correct. This is not
an unchanged-geometry oracle proof or a full-bank PASS; nine telemetry rows
also remained blocked in that receipt.

Created and executed `qualification/exact_offset_ring_contact_reference.py`;
its persisted result is `exact-ring-contact-reference.json`. Local generation
of the original torus fixture matches the complete frozen payload FNV
`c5aec2165cdec18c`, and the receipt also records a cryptographic hash of that
generated payload. All subsequent support/contact calculations use Fraction.
FNV remains an identifier, not an attestation of a separate runtime dump.

Exact facts for this payload:

- All 64 cardinal Bezier x hulls lie at or below
  `M=702557959320141/140737488355328`, exactly the frozen a08 ray x.
- Every chart has a strict x control; hence no chart lies entirely in the
  supporting plane. With all Bernstein weights positive in an open chart,
  support equality occurs only at enumerated seam endpoints. There is exactly
  one canonical support seam here, with y=`3/36028797018963968` and z=0.
- **a08 is a genuine exact-control even contact**, not a no-hit:
  z=r forces Q>=1 globally, and Q=1 at exact
  `t=72057594037927939/36028797018963968`. Its returned binary64 t=2 has error
  `3/36028797018963968`; the exact witness residual bound is its squared error
  divided by r². Its outward normal is exactly +z. The local contact is of
  higher even order because the ray is tangent to the centerline in xy.
- **a06 is not an exact origin contact.** Its ray x is exactly M+r, so Q>=1
  globally. The origin y=0 differs from the supporting center y. The first
  positive tangent is exactly `t=3/36028797018963968`, approximately
  8.326672684688674e-17, with outward normal +x. Under the existing default
  coincident crossing-push this sole contact is suppressed and no-hit is
  correct; unsuppressed distance must preserve the positive tangent.

The generic runtime certificate proposed to the implementer is independent of
bank IDs: an axis-aligned ray along one planar axis, a global certified support
half-space on the other axis, and either the normal-cap relation
`ray_support=M, |z-z0|=a` or outer-edge relation
`ray_support=M+b, z=z0`. All exact support Bezier controls must satisfy the
half-space; reject flat supporting spans until continuum handling exists.
Enumerate canonical support seams, compute exact contact times, select the
earliest eligible contact after the API's suppression interval, and return
`stationary_tangent` with t/error/residual bounds. If none remain, the complete
support proof establishes no-hit. Unknown/flat/unsupported cases fall back
fail-closed. Only exact linear combinations are needed for this useful subset;
fixed dyadic superaccumulators avoid acquiring Boost/GMP, whose headers were
not found at the checked local standard include locations.

`exact-seam-reference-02.json` now persists the tighter member-2 bracket and
probe-07/binary artifact hashes plus observed exact binary64 error. Its script
supports `--probe` and `--binary`; a final post-format/build rerun must bind the
final source and corresponding launch receipt. Tangent normals are known in
the support cases, but tangent directional sense still requires explicit
transport policy; scalar tangent admission alone does not qualify tracking.

## Exact support implementation source acceptance

Independently read `src/exact_dyadic.hpp` and the landed
`compile_supports()`/`support_distance()` implementation. No blocking source
issue was found in the support certificate. The implementation precomputes x/y
supports in both orientations, chooses an actually attained maximal seam
coordinate, rejects overshooting Bezier controls or flat supporting charts,
and enumerates canonical seam endpoints only. The exact query identities
establish the global Q>=1 bound. Exact contact-time comparison selects the
first contact eligible under the existing suppression policy; a truly zero
unsuppressed contact remains unresolved, while a positive sub-tolerance contact
is preserved. Returned t and residual error gates are checked explicitly.

The 36-limb signed dyadic implementation was checked for binary64 decoding,
normal/subnormal alignment, cross-limb assembly, small-integer multiplication,
same-sign carry, opposite-sign magnitude subtraction and borrow overflow,
negative-zero normalization, and outward conversion to long-double intervals.
The maximum finite binary64 value occupies 2098 bits in units of 2^-1074;
2304 stored bits safely cover these bounded small-weight linear sums.
Unsupported/nonfinite weights/values and overflow invalidate the predicate.
Current threshold conversion is exact: `characteristic` is double and the
minimum_t expression computes std::max over binary64 terms before casting to
Real. The implementation's final residual conversion uses the least binary64
upper bound, retaining the strict requested f tolerance.

This accepts the source mechanism, not an unobserved executable. Root should
check actual-header cancellation/carry controls, tangent/negative/support-
invalidation controls, and the final frozen/native executions against final
source hashes. Relevant exact inputs include DBL_MAX weighted cancellation,
smallest-subnormal cancellation, signed zero, weights 0/+16/-16 and rejected
17, and cross-limb borrow. No build or engine test execution was performed by
this reviewer.

Also inspected `qualification/verify_offset_bank.py` for the independent-bank
agent. Its exact Bernstein degree elevation/product/grid construction,
de Casteljau positivity cover, fixed-center convex-ball inside cover, and
control-hull AABB ray tail are sound. Candidate proposals only choose boxes and
center witnesses; acceptance follows exact rational checks. Sent the author
strict Boolean/numeric schema and disposition/state consistency requirements;
its sign-bracket route cannot certify the new even contacts, which need the
independent support-contact proof. Its stated 2e-8 corpus error bound is weaker
than the runtime 1e-11 distance gate and must remain explicitly labeled.

## Accepted baseline evidence, 2026-09-26

The earlier 2e-8 pilot limitation is superseded for the final frozen corpus by
`independent-bank-tight-01` and `independent-bank-qualified-01.json`. Independently
read the final verifier and aggregation source and checked all nine aggregate
input/attachment SHA256 values against actual files. The source-level exact
Bernstein/product/elevation/subdivision and convex inside-witness arguments
remain valid. The aggregate covers exactly the unchanged 160 query IDs: 158
exact rational prefix/endpoint/tail certificates plus the two independent
support-contact certificates. It establishes 69 first eligible hits within
exact decimal 1e-11 of the observed binary64 parameter and 91 complete eligible
ray no-hits. The a06 observed positive distance equals exact 3/2^55; the a08
observed value 2 differs from exact 2+3/2^55 by only 3/2^55. These certificates
use the exported binary64 normalized direction components and the exact
cardinal cubic of the original checked binary64 controls. They certify this
new geometry explicitly; legacy agreement does not supply the proof.

Read actual `build-receipt-11.json`, `frozen-offset-03/launch.json` and its
receipt/candidate, `offset-tests-06.txt`, `legacy-cpp-tests-02.txt`, and
`native-probe-02.jsonl`. The frozen observation has 160 valid rows, 69 hits,
91 misses, zero unresolved and zero resolved legacy differences. Its nine
blocked telemetry rows concern normal/projection evaluation, so it is not an
all-query normal acceptance. The test receipts record successful offset and
legacy tests. Expanded exact dyadic controls were subsequently inspected in
the test source and their test-only build and `offset-tests-07.txt` PASS were
read; they include smallest subnormal, exponent +1000, DBL_MAX weighted
cancellation, zero weight, rejected weight 17, and signed zero. The later test
source/binary differ from receipt 11 and are explicitly excluded from its
production binding rather than silently treated as unchanged.

Executed only the independent Fraction seam reference, producing
`exact-seam-reference-native-03.json`. It verifies the unchanged analytic H5
SHA256 and proves the first boundary lies between
`211106232532991/13194139533312` and exact `16+1e-12`, using all-span Bezier x
support plus one strictly inside seam center witness. The native observed
distance is exact `4503599627370885/281474976710656`; its distance from any
first root in that enclosure is at most `1231/844424930131968`, approximately
1.4578e-12, below 1e-11. Native probe and library hashes match receipt 11
outputs. Production inputs and outputs were checked against live files;
the now-edited probe source was instead checked against baseline Git snapshot
`3f8703db2` (with canonical LF/CRLF normalization), matching the recorded
compiled probe hash. The receipt lists every historical-source and test-only
exception. No build, installation or engine test was executed by this reviewer.

The native probe source checks registration, first distance, outward normal,
and opposite directional senses at this transverse boundary; the saved PASS
confirms those checks ran. Its `particle_transport:false` is accurate. Accepted
milestones are the explicit subset's constructive kernel mechanism, this
160-ray independent scalar qualification, unchanged legacy test regression,
and this native adapter seam smoke. Remaining gaps include physical varying
radius/frame coils, universal termination/resolution, non-cardinal general
even contacts, normal/evaluate coverage at ambiguous or remote projections,
tangent transport policy, particle tracking, matched performance, and legacy
geometry equivalence. Baseline acceptance belongs to the recorded artifacts
and baseline commit, not to the subsequently edited performance experiment.

## Bounded performance proposal: conditions before source acceptance

An untrusted floating proposal is permissible only if the accepted root keeps
the current certified endpoint, unique projection and derivative proof, and
the complete eligible prefix is independently covered. Every outside-prefix
tile must have strictly positive outward interval Bernstein coefficients for
every curve span. Convert all binomial factors, products and affine t/u
substitutions outward; using floating proposal coefficients would invalidate
the cover. Inside-prefix tiles may use one genuine curve-center witness with
both ray endpoint squared distances strictly below the radius bound, since
the squared norm is convex in t. A sampled minimum or sample signs alone never
certify a prefix. Overflow, ambiguous signs, zero-width/stagnating subdivisions
and budget exhaustion must retain the unchanged slow fallback.

The current stationary minimum enclosure stays mathematically valid when
precision is incomplete: all removed tiles exclude stationary minima or lie
strictly above a valid witness upper bound; the surviving queue minimum is
a global lower bound. Thus evaluate may return a strict proved sign when
`squared.lo>1` or `squared.hi<1`, independently of `complete`. A straddling
interval still fails closed, and the special zero boundary band must retain
its existing completion/projection guards. This is a source argument for the
proposed change, not acceptance of an unobserved new binary.

## Native Region exit reference and fast-path source audit

Executed `exact_native_region_exit_reference.py` under a 1 GiB memory limit
and internal 30-second/100000-node/depth-100 gates. Its
`independent-native-region-exit.json` uses the original checked analytic H5
and native02 observed entry distance. The new origin is the exact rational
value of the binary64 subtraction `550-distance`, matching the Region probe.
One exact seam-center witness is strictly inside at both t=0 and x=506+1e-12;
convexity proves the complete intervening prefix inside. At x=506-1e-12 all
256 exact degree-six Bernstein squared-distance polynomials have strictly
positive Q-1 controls. The 256-node proof took 0.199 seconds and requires no
stationarity solver. Continuity proves the first exit in
[27.999999999997637,27.999999999999634], relative to that rounded origin,
an exact width 2e-12. This is an independent reference for the proposed Region
entry/exit smoke; no new Region execution or particle history is attested here.

Read the landed `proposal_value`, `squared_bernstein`, `split_tensor`,
`outside_prefix`, `inside_prefix` and `accelerated_distance` methods. The
tensor is degree six in owned curve parameter and two in affine ray-box
parameter. Its power coefficients correctly square
A[o+left*d-C(u)]+v*A[d]*(right-left); both cross terms and velocity square are
present. The power-to-Bernstein factors C(i,k)/C(n,k) are outward divisions.
Child tensor indices correctly implement both de Casteljau directions. The
original-control hull skip and complete span loop preserve outside coverage;
the fixed exact curve witness and endpoint upper bounds preserve inside
coverage. Floating proposal Newton, sample signs and bisection only choose
candidates, never prove acceptance. The preserved endpoint sign, global unique
projection and common strict derivative gates establish one crossing in the
candidate bracket; the derivative divided by a uniform upper bound on sqrt(Q)
justifies the interval contraction for sqrt(Q)-1.

The exact-zero interval arithmetic shortcuts are valid for finite intervals,
including subtraction of equal singleton values and division only after the
existing denominator-zero rejection. The new evaluate strict-sign path is
valid even with incomplete precision; finite saturation preserves that sign.
The boundary band still requires completion and a unique normal. One reporting
fix was requested before acceptance: `double(bound)` in the accelerated result
can round down. Return the least binary64 upper bound using the same cast-plus-
conditional-nextafter rule as support results. No other mathematical source
blocker was found. This is source audit only; the altered production binary
and performance remain unaccepted until fresh hash-bound execution and the
unchanged exact rational corpus qualification.

Follow-up source check: the requested residual conversion repair landed in
both accelerated and slow sign-change returns. Each now uses conditional
nextafter only if its binary64 cast is below the accepted Real bound. This
closes the reporting issue without relaxing the residual acceptance gate.

## Final changed-mode acceptance against build 14

Ran only `verify_final_offset_acceptance.py`, a read-only hash/receipt and
Fraction comparison check. Its final `final-acceptance.json` verifies all 17
recorded build inputs and all five outputs against current files, with no
historical-source or test exceptions. Build receipt 14 records successful
compilation, unchanged input hashes and zero acquisition bytes. The added
`enable_bernstein_prefix` option defaults true and gates only the optional
certificate stage; false retains the ordered slab route with the same support,
geometry, budgets and acceptance tolerances. The flag introduces no unchecked
alternative acceptance path.

Read and bound actual frozen04/05 launch, observation and independent aggregate
receipts, their candidate and per-query proof files, canonical CSV, H5,
verifier, support/aggregation sources and fresh support proofs. Both modes
contain exactly 160 unchanged ordered rays and independently certify 69
first eligible hits and 91 complete eligible-ray no-hits at exact 1e-11 cm.
Every ordinary hit's interval/error and first-prefix/after-endpoint flags were
checked directly; the two positive support contacts were independently
compared as exact fractions. The production bank binary matches build 14 for
both runs. Actual offset-tests08 and legacy-cpp-tests03 PASS receipts were
read and hashed. The nine frozen telemetry blocks still preclude a claim of
complete normal/projection telemetry coverage.

Native03 entry distance is bit-identical to native02, so both exact entry and
entry-derived-origin exit references remain applicable. The analytic H5 and
reference scripts/probe identities were checked. Actual Region entry/exit
signed surface IDs are -1/+1; source and PASS output cover before/after
contains, normal, opposite directional senses and the entry/exit sequence.
Observed exit `27.999999999997744` differs from any first exit in the exact
reference enclosure by at most
`129998773611/68719476736000000000000` cm, below 1e-11. The native executable
and libopenmc.so match build 14 hashes. This accepts one native CSG Region
entry/exit smoke, not particle histories or general tangent tracking.

Accepted final milestones are the reviewed constructive subset mechanism,
the optional Bernstein prefix path and preserved fallback against two
independent frozen qualifications, unchanged legacy regression tests, and
the native member-2 Region crossing smoke. Performance remains outside this
review's acceptance; no paired summary was available during the final check.
Physical varying-radius/frame coils, universal bounded resolution, general
even contacts, complete normal/classifier coverage, tangent transport policy,
particle tracking and legacy geometry equivalence remain explicit gaps.
Acceptance applies only to the hash-recorded build 14 artifacts. A later
source/binary change requires renewed binding and relevant qualification.
