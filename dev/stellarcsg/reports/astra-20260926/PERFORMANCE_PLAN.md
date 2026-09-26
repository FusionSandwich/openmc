# Performance acceptance and cost model

The correctness baseline is commit `3f8703db2`, native probe02 and frozen-offset-03.
All 160 frozen scalar queries are independently certified for the new exact-control
solid at 1e-11 cm. This does not establish a performance target. The observed bank
walltime is 27.186 s and summed distance time 24.946 s; 69 hit queries have median
236.340 ms. Detailed categories and missing point/normal timings are retained in
`BANK_COST_OBSERVATION.md`. These are one-process observations, not a matched
throughput benchmark. No 80% claim is made.

For a matched workload with native elapsed time T_native and new elapsed time
T_offset, relative throughput is T_native/T_offset. An 80% target requires
T_offset<=1.25*T_native, with equal counts of completed, correct work. Unsupported
queries, exceptions, missing timings and wrong answers cannot be removed from
the denominator or counted as fast successes. Compilation/preprocessing time and
steady-state query time must be reported separately.

The baseline stores O(N) curve spans and control hulls. Its scalar solver repeatedly
computes all-span minimum bounds, with interval stationary contraction and priority
queue subdivision. A ray has at most the configured slab budget; each minimum has
at most 24000 popped tiles. Projection certification has a 48000-visit bound, and
each candidate ray box needs a unique joined projection plus exclusion of all
competitors. This is bounded, but repeats substantial work. In run03, distance
queries total 4104 minimum calls, 40758 minimum nodes and 16712 projection visits.
Allocations in these query paths are a transport scalability limitation.

The next constructive acceleration tests a different certificate organization:
an untrusted fast numerical lead proposes a small bracket; a tensor Bernstein
bound for Q(u,t)-1 proves the entire earlier outside prefix over every span at
once. The degree is 6 in the center parameter and 2 along the ray. Inside prefixes
can be covered by exact/interval fixed-center balls because their ray restriction
is convex quadratic. The admitted root still needs strict interval endpoint signs,
unique projection, strict derivative, and the original distance/residual gates.
Failure preserves the existing solver as a bounded fallback. This experiment is
retained only after independent replay and measured benefit.

Matched final benchmarking remains NOT_RUN. Before claiming the target, fix the
represented geometry, native comparator, ray/particle workload, compiler flags,
thread count, warmup policy, cache policy and operation counts. Use fresh-process
repetitions and randomized unique query order; separate hit/miss/contact and
held-out groups. Record distance/evaluate/normal time, completed work, allocations,
peak memory and preprocessing cost. An analytic torus, facet approximation, bare
carrier box, or all-no-hit bank is a different workload and cannot silently stand
in for the shaped spline solid. A full transport benchmark also requires its
own material/data and periodic-boundary admission; neither has been run here.
