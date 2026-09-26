# Exact-control offset kernel contract (before implementation)

This is an explicit opt-in representation, not a claim that the legacy rounded
angle/frame program defines the same bitwise surface. Input coefficient bytes
are unchanged. The represented centerline is the exact real periodic cardinal
cubic B-spline of those binary64 controls; division by six is mathematical.
Local span coordinates are retained. Adjacent spans share a C2 seam by the
B-spline identities, including the last/first seam. No global-angle landing is
required. The legacy representation remains available and fail-closed.

## Admitted solid

Two compiler-checkable cases are useful: a constant circular section about a
regular periodic 3D curve, and a constant ellipse about an xy-planar periodic
curve with supplied normal along z. In the latter, a is the z radius and b is
the in-plane radius. All controls/radii must be finite; radii positive and
constant exactly; planar/normal conditions checked on every control. Whole-span
speed checks must exclude degeneracy or compilation rejects. This is a thin
cable/planar shaped coil class, not the WISTELL-D rectangular winding pack.

Let A=I/r for the circular case or diag(1/b,1/b,1/a) for the planar case. Define
F(p)=min_s |A(p-C(s))|^2-1. The solid is F<=0, the boundary F=0. It is a union of
ellipsoids (balls after scaling). At a regular closest point it agrees with
the swept orthogonal ellipse. Closest-point switches preserve F continuity;
ties with different normals are ambiguous for normal/transport and rejected.
For planar curves, Euclidean and scaled nearest parameters coincide.

## Queries and certificates

Ray parameters use the binary64 direction produced by robust scaled/hypot
normalization as exact stored components, matching the numerical convention
of the existing kernel. They are nominal cm, not an additional proof about
the infinitely precise normalization of an arbitrary supplied real direction.
Axis-aligned unit directions (including the decisive seam case) are exact.
Nonfinite origins/directions and zero directions reject.
All eligible t>=minimum_t are searched in a conservative finite coefficient
hull expanded by section radii. For coincident=true, minimum_t is the existing
explicit crossing-push distance; the suppressed interval is part of the API
contract, not a proof that no roots exist there. Unsuppressed origin contact or
tangency may remain unresolved. No endpoint caps are needed on a periodic loop.

The signed distance g(t)=min_s |A(p(t)-C(s))|-1 is continuous and L-Lipschitz,
L=|A d|. Interval evaluation bounds its global minimum using ALL owned spans;
no unverified BVH pruning. Outside requires excluding every center parameter;
inside requires one certified center witness. Ray slabs with a strict sign
certificate are excluded. A sign bracket proves existence by continuity.
The prefix invariant is that every eligible parameter before the bracket is
covered by excluded slabs, without gaps. Slabs are visited in increasing t.
An ambiguous earlier slab blocks any later candidate. Budget exhaustion is
unresolved, never no_hit. no_hit requires exclusion of the entire finite range.

At a hit, a local joined arc must contain a unique closest branch: derivative
h_s=|AC'|^2+(AC-Ap).AC'' is strictly positive throughout the arc, h(left)<0 and
h(right)>0, and all nonlocal spans have a larger distance lower bound. Adjacent
seam pieces join by exact C2 continuity, avoiding tiny endpoint-distance tests.
Alternatively an interval enclosure of every possible minimizing branch may
prove a common strict ray derivative; unresolved competing normals still block
normal admission. Transverse monotonicity plus an opposite-sign bracket gives a
unique crossing. Even roots/tangencies stay unresolved unless separately proved.

The joined arc uses adaptive half-widths 0.5, 1, and 1.5 in local span units.
Every omitted chart tail is part of its certified complement. At stationarity,
R.D=0 in scaled coordinates; eliminating a tangent component whose interval
excludes zero gives R.w=sum(i!=k) R_i*(w_i-w_k*D_i/D_k). Intersecting this with
the direct dot product bounds the same derivative more tightly. A unique
projection with a strict derivative and two same-sign slab endpoints excludes
the whole slab, which handles the transverse near-tangent case without a
larger budget or relaxed tolerance.

For supported planar axis rays, a separate exact linear-arithmetic certificate
can prove even contacts. Original binary64 controls are accumulated exactly as
signed multiples of 2^-1074 in a bounded 2304-bit integer. If every cubic
Bezier support coefficient is <=M (or >=M for a minimum), and each chart has
at least one strict coefficient, all open chart interiors are strictly below
the support. Equality can occur only at the enumerated canonical seams.
The two ray alignments (support coordinate M plus the in-plane radius, axial
coordinate at the plane) and (support coordinate M, axial coordinate plus the
axial radius) give Q>=1 globally. Their complete boundary set consists of the
seam contacts whose remaining coordinate lies on the ray. Exact ordering picks
the first eligible contact; outward conversion and rounding are checked against
the absolute distance and residual tolerances. Flat support charts, arbitrary
directions, and unmatched exact identities fall back to the general certificate.
An exact unsuppressed t=0 remains unresolved; an exactly positive t smaller than
the tolerance is still eligible. Invalid arithmetic or budgets cannot be
bypassed by this path. This proves scalar contacts, not tangent transport sense.

Distance returns a binary64 value in a certified narrow root enclosure; the
enclosure and rounding error must fit the declared t tolerance. It does not
require a representable exact root. Classification returns a certified sign
or an explicit boundary/ambiguous result within the same enclosure convention.
Outward normal is proportional to A^T A(p-C(s)); branch uncertainty must be
bounded, not silently discarded. Shared members keep their original IDs; any
collection/periodic transport behavior needs its own native adapter validation.

The numerical on-boundary band is |F|<=1e-13, narrower than OpenMC's existing
FP_COINCIDENT=1e-12. evaluate returns zero only when the entire certified F
enclosure lies in that band and a unique normal is certified. Otherwise it
returns a proved sign or throws. Unit-normal component enclosures must each
have width<=1e-8 and positive gradient-norm lower bound. Their midpoint is
returned without an uncertified renormalization.

## Arithmetic, limits, and evidence

Use outward long-double intervals with nextafterl after each primitive basic
operation, including divisions and square roots; finite IEEE binary formats,
round-to-nearest, no fast-math/reassociation/FMA contraction, no flush-to-zero.
Canonical coefficients are enclosed from original input controls. Invalid
intervals or unsupported arithmetic reject. Tests must include interval
containment against exact rational evaluation and negative exhaustion controls.
Build flags and long-double format are recorded in the runtime receipt.

Supported controls/query coordinates have magnitude<=1e100, radii>=1e-100;
long double must have at least64 significand bits and exponent range16384.
There are at most4096 spans,24000 minimum tiles,48000 projection visits,
65536 compiler regularity visits,64 levels, and1024 bisections. Ray slabs use
min(8192,initial_subdivisions*(max_refinement_levels+1)). A minimum enclosure
remains valid when its requested precision is not achieved; downstream sign,
distance and residual acceptance gates still apply without tolerance inflation.
Original-control coordinate hulls exclude distant spans using strict outward
distance separation. Their containment follows from nonnegative partition-of-
unity B-spline weights; no external BVH or topology is trusted.

Finite deterministic box/iteration/depth limits bound work and storage. Initial
implementation may be O(N B), N spans and B query subdivisions; no near-native
speed claim follows. A measured cost breakdown and precomputed Bernstein/BVH
route are separate work. First target is one native member-2 seam crossing.
The frozen 160 bank is retained unchanged; tangencies and unsupported inputs
may prevent its milestone, which must be reported rather than relabeled.

## Independent alternatives retained

1. General polynomial H/G with radical-free frames and degree-26 elimination:
   constructive root isolation, but exceptional branches and nearest-owner
   switches make it a larger implementation. Planar reduction degree <=10.
2. Full local patch Krawczyk with exact-control seam charts: viable, requires
   whole-prefix coverage and closest-coordinate transfer.
3. Selected offset-union sign cover: weaker envelope, direct continuous common
   classifier and constructive prefix invariant; potentially much slower.

No route treats a sampled residual, all-no-hit corpus, or static BVH audit as
root completeness. Exact-control interpretation is explicit in the API and
receipts. This document states acceptance obligations, not results.
