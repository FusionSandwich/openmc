# Performance acceptance and cost model

The explicit exact-control offset geometry has independent 1e-11 cm scalar
qualification for both final build14 query modes. Correctness does not establish
the native-throughput target.

## Accepted local observations

`PERFORMANCE_AB.md` and `performance-ab.json` compare the same binary and inputs
with only Bernstein prefix acceleration toggled. Three clean pairs
(04/05, 10/11, 12/13) have mean summed distance times 0.865648128 s enabled
and 3.507428628 s disabled, a 4.05x observed improvement. Mean process wall
times are 1.547897 s and 4.032762 s, respectively (2.61x). All scalar results
match their independently qualified same-mode replicate. Nine normal timings
are missing in every run and remain visible in the evidence.

Runs 06-09 overlapped an independent verifier and are excluded, with raw
observations retained. Fixed pair order and a small local sample limit the
statistical interpretation. This is a useful acceleration check, not a
production transport or native-comparator benchmark.

The historical baseline commit `3f8703db2` / run03 had summed distance time
24.945547355 s and wall time 27.186 s. Other changes, including exact-zero
interval identities, separate that baseline from the final binary. Do not
attribute the entire historical improvement to Bernstein acceleration.

## Cost model and retained acceleration

The solver stores O(N) spans/control hulls. Global minimum queries use interval
stationary contraction and bounded priority-queue subdivision. Each minimum
has at most 24000 popped tiles; projection certification has at most 48000
visits. The ordered fallback has a configured ray-slab budget.

The accelerator samples an untrusted numerical lead, then certifies a root
bracket and the entire earlier prefix. Outside bounds use degree-six by
degree-two tensor Bernstein coefficients of squared metric distance; inside
bounds use fixed exact curve-point witnesses. Strict endpoint signs, unique
projection, derivative sign and distance/residual gates still apply. Failure
falls back within explicit finite budgets. Sixty-six of the frozen rays take
the certified accelerated path in each enabled run. Both modes remain
available with `RootSearchOptions.enable_bernstein_prefix` and the replay
flag `--no-bernstein-prefix`.

Allocations, all-span proposal/minimum work and difficult near-tangent cases
remain costs. Any further optimization needs unchanged scalar qualification,
failure-path checks and a fresh source/binary binding before timing.

## Unmet native-throughput acceptance

For native elapsed time T_native and offset elapsed time T_offset on matched
completed work, relative throughput is T_native/T_offset. The 80% target
requires T_offset <= 1.25*T_native. Unsupported queries, exceptions, missing
timings and wrong answers cannot be dropped or counted as fast successes.
Report preprocessing/compilation separately from steady-state queries.

The matched native benchmark remains NOT_RUN. First fix the represented
geometry, legitimate native comparator, ray/particle workload, compiler flags,
thread count, warmup/cache policy and operation counts. Use fresh-process
repetitions and randomized unique query order, reporting hit/miss/contact and
held-out groups. Record distance/evaluate/normal costs, completed work,
allocations, peak memory and preprocessing.

An analytic torus, facet approximation, bare carrier box or all-no-hit bank is
a different workload and cannot silently replace the shaped spline solid.
A full transport benchmark additionally requires material/data and periodic
boundary qualification. Neither it nor physical winding-pack qualification has
run. No 80% native-throughput claim is made.
