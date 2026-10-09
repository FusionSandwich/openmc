# Workload ladder, profiling and exact P00/plasma speedups — results

## Status (October 9, 2026)

| Step | Evidence | Outcome |
|---|---|---|
| Workload attribution | ladder-02 | GEOMETRY_BOUND: P00 1.66-1.85x ring at matched collisions; workload mismatch F = 1.16 |
| Profile | profile-01/02 | Physics 2-3%; P00 dominated by `ray_interval` `nextafter` calls, facet distance, `normal_at`, parity rays |
| Patch v1 (inline nextafter, std::memcpy) | ab-01 | REJECT_EFFECT 1.05x: `-fno-builtin` made each bit cast a `memcpy@plt` call |
| Patch v2 (same, `__builtin_memcpy`) | ab-02, xval-01 | ACCEPT 1.657x, bitwise identical on all seeds/densities tested |
| Patch v3 (`normal_at` precompute + exact early reject) | ab-03, xval-02 | +1.076x (UNDECIDED vs pre-registered 1.10), bitwise identical |
| Gate, v2+v3 build, 3 seeds x 5 repeats | gate-01 | **PASS (median)**: P00/ring 1.212, 1.211, 1.178; pooled 1.201; worst pairings 1.27-1.28 |
| Geometry images | images/ | OpenMC ray traces/slices of all four models + matplotlib renders of the facet and spline payloads |
| Plasma baseline | plasma/runs/plasma-base-01 | Control build bitwise reproduces the retained Sept 26 plasma statepoints; quiet ratio 200 |
| Plasma source occupancy | plasma/source_occupancy.py | All 256 source sites are one point inside the custom LCFS and outside the torus: 68.4 vs 5.4 collisions/source (12.6x workload) |
| Plasma profile | plasma/runs/plasma-prof-01 | 95% in the periodic-spline distance solver; 55% surface evaluations in the tangent-interval scan |
| Patch v4 (opt-in distance ceiling; plasma) | plasma-v4-gates-01, plasma-ab-01 | **ACCEPT 8.07x** (7.86-8.51), all 12 gate runs bitwise identical; plasma custom/torus 195.9 -> 23.8 |
| Patches v5 (ceiling for facets) + v6 (exact spline indexing) | plasma-v6-gates-01, xval-03 | All bitwise identical (12 gate runs + 5 cross-validation runs) |
| Gate, v2-v6 build, ceiling on | gate-02 | **INVALID** (one first-run outlier, seed 1741 CV 6.8%); seeds 1742/1743 PASS_ROBUST; pooled 1.109 (descriptive) |
| Gate replication (+1 discarded warm-up) | gate-03 | **PASS_ROBUST on all 3 seeds**: medians 1.126/1.117/1.071, worst pairings 1.138/1.122/1.087, pooled 1.105 |
| Patch v7 (value-only exact evaluate) | plasma-v7-gates-01, plasma-ab-02 | Bitwise identical; no measurable effect (1.004x, UNDECIDED) |
| Patch v8 (voxel clearance fast path) | plasma-v8-gates-01, plasma-ab-03 | Bitwise identical; 1.139x (1.092-1.216, UNDECIDED vs 1.10); +0.39 s init |
| Plasma matched-source diagnostic | plasma-matched-01/02 | Source uniform in each plasma: 51.6 vs 60.6 collisions/source; custom/torus 15.8 (control) -> 2.10 (v2-v7) / 2.12 (v2-v8) |
| Plasma counters + matched profile | plasma-diag-01, plasma-prof-03 | 92-95% of plasma distance calls certified; full solver 4.4 calls/history = 45% of time; next steps need oracle validation |

Nominal P00/ring on one build in quiet conditions went from 2.153 (control) to 1.105 (gate-03,
PASS_ROBUST) with no change to any tally bit. Scope: the derived represented P00 facet model versus fixed 30x30 cm
rings; continuous CAD/section/frame fidelity, physical-coil ownership, native event
semantics and independent (Sol) review remain open. Patches live only in `patches/`; no
shared checkout was modified. The plasma benchmark compares unequal workloads (source inside
custom iron, outside the torus); see PLASMA_PLAN.md.

# Density ladder — results

## ladder-02 (decisive): GEOMETRY_BOUND

Identical sealed design plus amendment-2 noise controls (quiet admission, telemetry); no gate
loosened. 32/32 runs exit 0, phase 1,125 s, private lock released, shared lease untouched.
Every pre-registered gate passed (all arm CV <= 3.5%, ring k=1 drift within 5%, fit residuals
2.7%/1.1%); `ladder_analyze.py` (file recheck) and the independent implementation agree on
every field; `verify_results.py` 236/236; residual deviation uncorrelated with host or VM load
(r = 0.11, -0.19). One run was flagged `contended` only because the host-load read failed at
the end of the phase; it sat at its arm median.

| Quantity | median | band (min/max curves) |
|---|---:|---|
| R_thin (P00 at ring workload / ring) | 1.658 | 1.605-1.708 |
| R_dense (P00 / ring at P00 workload) | 1.850 | 1.758-1.913 |
| F (ring at P00 workload / ring nominal) | 1.156 | 1.109-1.213 |

* Nominal P00/ring = 2.138 = F x R_dense: about 1.16x from the 4.06x collision workload and
  1.85x from geometry.
* Fits per 100k histories: ring 6.66 s + 0.196 s/C; P00 10.98 s + 0.501 s/C. P00 costs 110
  versus 67 us per history and 5.0 versus 2.0 us per collision; the per-history term is 72%
  of P00 nominal transport.
* To pass: cut P00 transport 41.5% (current rings) or 32% (workload-matched rings).
* Absolute times in this quiet phase (P00 15.3 s, ring 7.1 s) are far below the retained
  100k block (24.6 s, 10.4 s) and ladder-01: earlier campaigns were contention-inflated.

## Profile (profiles/profile-01): where P00's time goes

gdb stack sampling during transport only, 1,000 P00 and 600 ring samples, every profiled run
bitwise identical to ladder-02. Collision physics is 2-3% of samples in both models.

* P00: facet `distance` 57%, `contains`/`parity_ray` 28% (cell search after crossings),
  `normal_at` linear scan 10%, source spatial constraints 7%, rotational periodic BC 6%,
  hot-path allocation ~4%. `std::nextafter` (out-of-line libm, called 4x per nonzero axis
  in `BoundingBox::ray_interval`) is the innermost frame in 30.9% of P00 samples.
* Ring: 81% `Region::distance_complex` (virtual-crossing traversal of the union-based
  background cell).

## ladder-01 — INCONCLUSIVE (noise)

**Pre-registered verdict: INCONCLUSIVE.** All record-level gates passed. The timing-noise
gates failed: 7 of 8 arms had coefficient of variation > 5%, ring k=1 drifted 15.6% between
blocks, and the ring fit residual was 5.6%. Under PLAN.md no decision follows; the
numbers below are descriptive only.

## Execution

* OpenMC-Dev-D (D:), retained runtime `b83f…`/`22392af0…` copied byte-identically with a
  byte-identical 41-library loader closure (PLAN.md amendment 1). Shared campaign lease not
  taken (user instruction); private `ladder.lock` acquired 17:47:43 and released 18:02:30 UTC.
* 32/32 runs exit 0, 100k histories each, phase 883.5 s. Plan `plan.json` SHA256
  `b4072b5825c7d4a447128cf665713ec324fa539687603447a778a25db2855bac`, runner `2926203f…`.
* Passed: identities; bitwise replication of the retained seed-1741 production arrays at
  k=1 for both models; identical production arrays across each arm's 3 timing + 1 counting
  runs; integral collision counts; bracketing (P00 range 1.24–8.42 contains ring 2.07; ring
  range 2.07–17.96 contains P00 8.42); monotone counts. `ladder_analyze.py` rechecked every
  statepoint from file; the independent implementation agreed on every field.
* Environment: WSL VM load average rose from 2.6 to 5.5 during the phase (other work in the
  shared VM); initialization varied 8.0–31.6 s. P00 (facet BVH, memory-heavy) varied more than
  the analytic rings. The gates flagged this correctly.

## Collision workload (exact, seed 1741, 100k histories)

P00 k=1: 8.4230 collisions/history; ring k=1: 2.0737 (ratio 4.06; earlier 20k diagnostic
8.284 vs 2.140).

## Descriptive numbers (not a decision)

| Arm | C/hist | median s | min s | max s | CV |
|---|---:|---:|---:|---:|---:|
| P00 k=1/8 | 1.2413 | 15.566 | 15.318 | 23.873 | 0.267 |
| P00 k=1/4 | 2.3186 | 15.835 | 15.244 | 18.823 | 0.115 |
| P00 k=1/2 | 4.4032 | 18.833 | 17.159 | 20.514 | 0.089 |
| P00 k=1 | 8.4230 | 23.086 | 20.952 | 24.927 | 0.087 |
| ring k=1 | 2.0737 | 8.552 | 7.529 | 8.701 | 0.077 |
| ring k=2 | 4.7980 | 10.095 | 9.828 | 10.372 | 0.027 |
| ring k=4 | 9.8105 | 10.864 | 10.437 | 11.701 | 0.058 |
| ring k=8 | 17.9565 | 14.689 | 13.627 | 15.011 | 0.050 |

| Quantity | median | band (min/max curves) |
|---|---:|---|
| F (ring at P00 workload / ring nominal) | 1.245 | 1.180–1.505 |
| R_thin (P00 at ring workload / ring) | 1.844 | 1.754–2.653 |
| R_dense (P00 / ring at P00 workload) | 2.167 | 1.849–2.427 |

Linear fits on medians, per 100k histories: ring T = 7.86 + 0.368 C s; P00 T = 13.83 + 1.097 C s
(P00/ring: per-history term 1.76x, per-collision term 2.98x).

## Reading, explicitly provisional

* These numbers do **not** support H1 (gap mainly workload). Even the conservative band edges
  of R_thin and R_dense exceed 1.5, the GEOMETRY_BOUND threshold, but the noise gates failed,
  so this is not a pre-registered result.
* F sits at the gate (median 1.245): the 4x workload mismatch alone appears to consume about
  the whole 25% allowance. If confirmed, both the proxy specification and the P00 geometry
  stand between the current pack and the goal.

## What decided it

ladder-02 (above) repeated the identical sealed plan with quiet admission and passed every
gate. ladder-01's provisional reading (geometry-bound, F near the gate) was confirmed in
direction; its absolute times and F were inflated by contention.
