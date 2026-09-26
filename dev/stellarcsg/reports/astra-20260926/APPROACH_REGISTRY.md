# Constructive approach registry

Independent Sol analyses began without a prescribed winning mechanism. The
selected implementation was chosen after their separate equations exposed a
constant-metric subset with a common continuous classification predicate.

| Formulation | Key invariant / actual artifact | Decisive case | Cost / gap / next mechanism |
|---|---|---|---|
| Legacy projected Newton + sign scan | Inspected pinned compiled_swept_surface.cpp; residual is only a candidate, retained-prefix gate remains | a03/a06/a08/a15; same-span earlier root | Saved73 unresolved/87 no_hit; no root completeness. Not reopened by increasing seeds or residual tolerance. |
| General radical-free algebraic elimination | Equations below; constructive degree<=26 exact rational Sturm/Bernstein isolation proposed independently | B=0 exceptional branch; remote nearest switch; seam | Not implemented here. Needs exceptional branch and global owner-switch handling; no claimed speed. Next mechanism is exact polynomial elimination with original equations filtering, not another missing lemma. |
| Joined local patch interval Newton/Krawczyk | C2 exact-control seam makes piecewise H/G C1; derivative hull can cross seam | Real root between representable global angles | Numerically viable, but general frames require common classifier and prefix cover. Exact-control seam contract is reused in selected route. |
| Exact-control constant-metric offset union | Implemented certified_spline_offset.cpp: global minimum enclosures, stationary Newton, second-order Taylor bound, ordered Lipschitz cover, monotonic bracket and global projection proof | Member2 shaped seam; remote competing minima; even roots; contact | First saved hit16.000000000001382 cm; independent rational enclosure supports it. Initial2.6s/query, later pruning measurement recorded separately. Tangencies/origin ambiguity and wide local projection can remain unresolved. |
| Compile conservative bounds once | Original-control hull stored per span; exact nonnegative partition-of-unity implies containment; strict distance separation only | A distant span omitted incorrectly would break global-minimum lower bound | Implemented scan pruning with no external BVH topology. StillO(N) and interval arithmetic/allocation costs; next is audited BVH or precomputed Bernstein bounds with same lower-bound invariant. |
| Exact rational independent first-ray proof | qualification/exact_offset_seam_reference.py and exact-seam-reference.json | Member2 seam; no runtime stationary solver reused | Global x support excludes entire prefix; one exact center witness supplies inside endpoint. One query only, not normal/full-bank/native/physical qualification. |

## General algebraic route retained

With exact cubic C(u), V=C', supplied normal N, D=V.V, K=V cross N,
J=K.K, and ray offset r=O+t d-C, stationarity is H=r.V=0. Where
D,J,a,b>0, ellipse classification on that stationary branch is equivalent to

Q=b^2 D(r.N)^2 + a^2(r.K)^2 - a^2 b^2 J=0.

Write H=A+tB, A=(O-C).V, B=d.V, L=B(O-C)-A d. For B!=0, t=-A/B
and the necessary polynomial is

R=b^2 D(L.N)^2+a^2(L.K)^2-a^2 b^2 J B^2,

degree at most26. Planar constant ellipse reduces this to degree at most10.
Square-free exact rational Sturm isolation is a constructive complete
reference for each polynomial, including even roots. It does not remove the
need to validate original equations, handle A=B=0 separately, reject B=0/A!=0
spurious solutions, select global minima, or account for nearest-owner switches
in variable-frame geometry. Independently rounded span powers additionally
require endpoint branches. The new exact-control offset route deliberately
avoids that larger model; it is explicitly selected and not silently substituted.

## Failed executable attempts are retained

The first compile rejected a long-double infinity narrowed into a binary64
bounding box; the type was repaired. The first independent rounded-square
normal test rejected a unique projection because a fixed three-full-span proof
arc reached a corner with negative distance second derivative. This was a
conservative query failure, not a wrong returned normal. The next constructive
repair narrows the joined local arc and certifies its entire complement.
All failed logs remain alongside later receipts; no frozen ray or tolerance was
changed. Comparator false-PASS paths were repaired before accepting new evidence.
