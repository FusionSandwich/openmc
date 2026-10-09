# Conservative query combinations

This experiment continues the previous BVH, front-to-back exclusion,
collision-distance ceiling and query reuse directions. It is a standalone
exact reference planner, not a new OpenMC transport backend or speed result.
No Claude source, runtime, input or process is changed.

Immutable boxes enclose root-producing domains. The planner builds a balanced
hierarchy, intersects boxes with a closed ray segment using exact rational
arithmetic, and sorts candidate intervals. A bounded per-worker cache reuses
candidate plans only for identical geometry and query state. The resolver keeps
equal contacts, cannot return a later hit over an earlier unresolved interval,
and distinguishes a ceiling-limited exclusion from a global miss.

## Contracts and limits

- Bounds are caller-supplied. This experiment does not prove they enclose a
  Fourier, spline or ruled surface; that is a separate geometry obligation.
- Directions need not be normalized. Parameters equal physical distance only
  for unit directions. Conversion of finite floats to rational preserves their
  represented values; it does not recover an unrepresented ideal coordinate.
- The callback must solve its entire candidate interval and return its earliest
  root, a proved no-hit, or unresolved. Runtime checks cannot establish a
  callback's completeness. Exceptions propagate.
- The resolver returns root candidates and all equal domain identities. It
  does not commit an owner, score tallies, compute normals or resolve contact
  semantics. Coincidence is in the cache key and remains the callback's concern.
- Contacts accompanying `UNRESOLVED` are provisional best-known candidates.
  Consumers must require `HIT` before using them as a certified earliest contact
  group. An earlier unresolved interval can still contain a closer root.
- This is a per-worker Python reference. Fraction arithmetic is intentionally
  unsuitable for claiming production throughput. A fast filtered C++ version
  needs conservative rounding and independent native tests.

## Validation

Run `test_candidate_scheduler.py` with an existing Python runtime. Twenty
adversarial tests include 120 independent trimmed-plane queries, a subnormal
positive gap, closed corner and ceiling ties, competing roots, earlier/equal
unresolved intervals, corrupted solver packets and cache-key changes. The
12-arm ablation compares hierarchy, ceiling and reuse with direct plane roots.
Work counters report pruning, not time or a predicted speedup.

The next bounded experiment is to bind real incumbent patch bounds to this
planner and check their coverage with the existing independent root bank.
Torus-assisted candidate intervals can later enter through the same callback
contract. Do not combine approximate torus misses with exact exclusion until
their residual bounds are proved. Do not launch a native campaign before
inventory, lease and independent acceptance checks.
