# Same-build A/B: inline exact nextafter in BoundingBox::ray_interval — pre-registration

Written October 8, 2026, before any A/B run. Follows ladder-02 (GEOMETRY_BOUND) and the
stack-sampling profile `profiles/profile-01`, in which `nextafter` was the innermost frame
in 30.9% of P00 transport samples (19.1% under facet `distance`, 11.8% under `parity_ray`)
and 0% of ring samples.

## Change under test

`patches/0001-inline-exact-nextafter-in-ray-interval.patch`: `stellarcsg::next_down` /
`next_up` replace the four `std::nextafter(x, -/+inf)` calls in `ray_interval`. Claimed
bit-identical for every binary64 input (differential test: 0 mismatches in 20,024,746
checks per function; a deliberately wrong mutant fails). Nothing else changes.

Both libraries are built by `builds/build_variants.sh` from one frozen Step 1 source tree
with identical commands; the trees differ in exactly that header (`tree-diff.txt`), and
normalized compile commands must be identical.

## Hypotheses

* **Correctness (gate):** every P00 and ring run of both variants reproduces the retained
  seed-1741 production raw arrays (tallies 1-3, SUM and SUM_SQ) bitwise.
* **Negative control:** ring transport does not use `ray_interval`; median nextup/control
  ring ratio within [0.97, 1.03].
* **Effect:** median P00 transport speedup control/nextup >= 1.15.

## Design

Arms: {control, nextup} x {P00 k=1, ring k=1}, exact ladder-02 inputs (seed 1741, 100k
histories), 5 repeats in 5 randomized complete blocks (order seed 20261009, sealed in
`plan.json` before running). Same child limits as the ladder (1 GiB, one thread, highest
CPU), same quiet-admission rule and telemetry as ladder-02, private `ladder.lock`, shared
campaign lease untouched, stop at first failure, no retry, no successor.

## Gates and decision

* Validity: all exits 0, 100 complete batches, no tracking diagnostics, bitwise replication
  in every run, every arm CV <= 5%, control ring first/last block within 5%.
* If valid: report S = median T(control,P00)/median T(nextup,P00) with the min/max band
  (min/max over repeats), the ring negative control, and the post-patch nominal ratio
  G = median T(nextup,P00)/median T(nextup,ring) against the 1.25 gate.
* S_lo >= 1.15 -> ACCEPT_SPEEDUP_EVIDENCE (still needs independent review before any
  integration); S_hi < 1.15 -> REJECT_EFFECT; otherwise UNDECIDED.

## ab-01 result (patch v1): REJECT_EFFECT

All 20 runs valid: both libraries reproduced the retained seed-1741 arrays bitwise, arm CV
<= 3.1%, ring negative control 1.006. P00 speedup median 1.050 (band 0.925-1.060).
Control `libopenmc.so` = `9bf312f3...`, byte-identical to the Step 1 current library.

Diagnosis (objdump): `-fno-builtin` from strict FP turned each `std::memcpy` bit cast into an
out-of-line `memcpy@plt` call (distance: 48 `nextafter@plt` -> 8 `memcpy@plt` plus 2 outlined
`ray_interval` calls; parity_ray: 24 `nextafter@plt` -> 16 `memcpy@plt`). Patch v1 replaced
one library call with two.

## Amendment: patch v2 and ab-02 (written before building v2)

Patch v2 differs from v1 only in using `__builtin_memcpy` (GCC/Clang; `std::memcpy`
elsewhere) for the bit casts, which compiles to a register move regardless of
`-fno-builtin`. Preconditions before timing: the exactness test passes with v2 under the
library's flags, and objdump of v2 shows no `nextafter@plt` or `memcpy@plt` in `distance`
or `parity_ray`. ab-02 then repeats the identical A/B design (control = the same
`9bf312f3...` build, variant = v2, order seed 20261010) with the same gates and decision.

Preconditions met: v2 `libopenmc.so` `ef2d3bc1...` built with compile commands identical to
control; exactness test 0 mismatches / 20,024,746 per function under the library flags;
objdump shows 0 `nextafter`/`memcpy` calls in `distance` and `parity_ray`, with
`ray_interval` inlined again.

## ab-02 result (patch v2): ACCEPT_SPEEDUP_EVIDENCE

All 20 runs valid and bitwise identical to the retained seed-1741 arrays; arm CV <= 2.9%;
ring negative control 1.0015 (0.975-1.037).

| Arm | median s | min | max |
|---|---:|---:|---:|
| control P00 | 14.763 | 14.384 | 15.418 |
| v2 P00 | 8.907 | 8.864 | 9.476 |
| control ring | 6.856 | 6.739 | 6.949 |
| v2 ring | 6.866 | 6.775 | 6.991 |

P00 speedup 1.657 (1.518-1.739). Nominal P00/ring: control 2.153 -> v2 **1.297** (gate 1.25;
still FAIL against the current rings by ~4%). Independent review is still required before
any integration; the represented-mesh scope and every fidelity gate are unchanged.

v2 cross-validation `runs/xval-01`: P00 and ring seed 1742 and P00 k=1/8, 1/4, 1/2 are all
bitwise equal to their references (ALL_BITWISE_EQUAL).

## Amendment: patch v3 and ab-03 (written before the ab-03 run)

v2 profile (`profiles/profile-02`, 700 samples, results bitwise unchanged): `normal_at` is
18.7% of P00 samples (linear scan, four long-double square roots per triangle), facet
`distance` self 36.1%, `parity_ray` 16.0%.

Patch v3 = v2 + `patches/0003-normal-at-precompute-and-exact-early-reject.patch`: per-triangle
`normal_at` inputs computed once at construction with the identical expressions, plus a
sqrt-free early rejection whose tolerance provably bounds the original from above. Built as
`nextup3` (`ceb7bd88...`; tree differs from control in exactly the three intended files;
compile commands identical). Differential test on all 18 P00 components: 1,355,436 points,
526,946 with a normal, 0 mismatches against a verbatim copy of the original loop compiled
with the same flags; a mutated-tolerance reference fails (492,722 mismatches).

ab-03: identical A/B design, control = v2 (`nextup2`), treatment = v3 (`nextup3`), order seed
20261011, same gates. Hypothesis: P00 speedup v2/v3 >= 1.10 (same decision thresholds as
above with 1.10 in place of 1.15); ring negative control within [0.97, 1.03]; post-v3 nominal
P00/ring reported against 1.25.

## ab-03 result (v3 vs v2): UNDECIDED

All 20 runs valid and bitwise identical to the retained seed-1741 arrays; arm CV <= 2.4%; ring
negative control 1.006 (0.945-1.035). v3 increment 1.076 (1.058-1.131): positive and exact,
but its band straddles the pre-registered 1.10, so no effect claim at that threshold.
Medians: v2 P00 8.870 s, v3 P00 8.243 s, rings 6.869/6.911 s. Post-v3 nominal P00/ring
1.193. Initialization medians unchanged (~5.2 s P00), so the precompute adds no visible
construction cost. v3 cross-validation `runs/xval-02`: ALL_BITWISE_EQUAL (seed 1742 both
models; P00 k=1/8, 1/4, 1/2). Multi-seed gate: GATE_PLAN.md / runs/gate-01.
