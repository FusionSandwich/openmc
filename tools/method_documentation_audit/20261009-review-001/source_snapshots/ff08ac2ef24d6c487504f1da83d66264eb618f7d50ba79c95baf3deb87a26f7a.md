# Fast recovery checkpoint, 2026-09-13

**Partial Phase III checkpoint. No fast-and-correct winner is qualified.**
The preserved fast architecture is recovered, its speed reproduced, later
reference evidence imported, and the retained missed-entry defect repaired in
an experimental lane. Nearest-root completeness and tangent failures remain.

Repository: FusionSandwich/openmc. New worktree: `stellarcsg-fast-recovery-04`.
Branch: `JS/stellarcsg-fast-recovery-20260913-04`, based on preserved
`c67b68fdaf7be2049308db7da449f14a25123847`. Source repair commit:
`1cef77053` (subsequent formatting is token-equivalent; rebuilt benchmark hash
matches the timed binary: `908900465f2b032a537a1fcc3703220b85fb6b34cd94d3f5bd9eec496faf694e`).
The archive and all 17 original local heads are unchanged and match live origin;
remote develop/default, master and the other two archive refs also match the
initial audit. No PR, push, reset, dependency installation or SSH was performed.
Experimental OpenMC geometry remains OFF by default.

## Fresh preserved baseline

Existing local WSL OpenMC-Dev-D, GCC 14.2, CMake 3.31.6, HDF5 and Python were
reused. Builds and measurements were serial. Desktop interference is not
controlled; measurements are finite-bank descriptive costs, not a universal
hardware latency claim. Runtime/query construction is outside kernel timing.

| Historical bank, fresh run | Median of seven bank means | Retained historical value |
|---|---:|---:|
| WISTELL coil031 distance | 594.7 ns | 631.624 ns |
| Coil031 evaluate/classification proxy | 223.6 ns | 213.908 ns |
| WISTELL plasma distance | 11475.7 ns | 11826.72 ns |
| Native ZTorus sentinel before / after | 180.10 / 172.24 ns | separate historical sentinel |

Historical coil timing contains 1000 distinct Fibonacci directions, but its
classification stage repeats miss origins and is not cold unique classification.
Only one scalar oracle ray was rerun outside that timed loop; the later 384
capture is the stronger fresh correctness control. Full 48 transport and full 48
kernel benchmarks were not rerun under this one-period milestone.

## Frozen scoreboard

Primary bank: `qualification/recovery04_frozen_bank.csv`, SHA256
`7348483e39128259a844d22a7618869a3f111604ea48d01e196a87fe0d396af7`.
All 160 geometry/coincidence/origin/direction tuples are distinct. Each lane ran
seven fresh processes, alternating execution order; no reference solve occurs
between primary timed queries. Reference, classification and normal operations
cannot overwrite candidate dispositions. All 28 OFF attempts are complete.

| Method | Geometry / representation error relative to supplied spline | Distance ns | Classification ns | Normal ns | P95 / P99 distance ns | Reference disagreements | Disposition |
|---|---|---:|---:|---:|---:|---:|---|
| Recovered old c67 | Original cubic tube / 0 representation change | 1211.88 | 1454.38 | 1658.13 | 3600 / 7200 | 4 | Retain as control; unqualified |
| Conditional seed repair | Same cubic tube / 0 representation change | 1685.63 | 1463.75 | 1627.50 | 5100 / 7943 | 3 | EXPERIMENTAL; not promoted |
| Prior floating A4e1, fresh Release build | Same cubic tube / 0 representation change | 2151.25 | 1479.38 | 1665.63 | 6400 / 11381 | 3 | Retain comparator; unqualified |
| Current exact dc76/5ed reference | Same cubic tube / 0 representation change | 14418488.49 | 4283063.04 | 6709008.52 | 138095532 / 220808421 | reference lane | Offline reference; not hot-path winner |
| Native ZTorus | Analytic torus / different geometry | 172-180 | not measured | not measured | not measured | separate sentinel | Control only |
| Candidates A/B/C/D | Not started | - | - | - | - | - | Gated on usable corrected baseline |

Distance/classification/normal columns are medians of seven 160-query bank
means. P95/P99 pool the 1120 individually timed calls, including clock overhead.
Cold classification is an evaluate/sign proxy at fixed query-derived points;
normal measurements use isolated instances. Their accuracy was not newly
certified. The exact classification/normal path uses rational nearest-point
stationary-root isolation; it is not the old golden/Newton classifier.

The seed experiment costs 1.391x old: within the temporary 2x repair allowance,
outside the preferred 1.25x limit. It is 0.784x the prior A cost. Its per-query
median is 600 ns, but misses dominate that median; this is not a claim of
submicrosecond real-coil hit performance. The 8 real WISTELL rays in this bank
are all misses. The 136 held-out random rays are new rays on the planar spline,
not a held-out device/configuration. The historical real-coil bank supplements
this limitation; a held-out real hit population remains necessary.

Exact reference 14.42 ms here and prior fast03's 2.13 ms are different banks.
ZTorus cost ratios, one-period histories/s, and matched mesh ratios are not
reported because matching workloads/transport gates were not executed.

| Instrumented work on same 160 inputs | Old | Seed experiment |
|---|---:|---:|
| Candidate spans/query | 0.92500 | 0.91875 |
| Newton iterations/query | 5.11875 | 9.66875 |
| Recovery queries | 2/160 (1.25%) | 2/160 (1.25%) |
| Recovery nodes/query | 0.300 | 0.300 |
| Instrumented bank-mean median ns | 1207.5 | 1718.13 |
| Exact fallback count / time fraction | 0 / 0, absent from code | 0 / 0, absent from code |
| Allocations/query and memory | not instrumented | not instrumented |

ON telemetry is separate from OFF production timing. Exact-reference fallback
fractions on this new bank were not instrumented; retained fast03 timing remains
historical context. None of these samples replaces a root-completeness proof.

## Correctness and promotion gates

Retained 384 replay: old has 4 disagreements on the 256 reference-admitted cases;
seed repair has 2. Both `.502 instead of .002` entries, their rigid transforms
and direction scaling are repaired. The 128 reference geometry blocks retain
their original reason/status exactly. The old and seed kernels still return
values on those inputs: production admission/rejection is **not repaired**.

Final common bank disagreements after seed repair:

- `a06`: boundary-origin disposition; exact reference returns about 8.33e-17 cm,
  floating kernel returns no hit.
- `a08`: tangent missed; exact reference returns 2 cm.
- `a15`: near-tangent distance differs by about 3.108e-7 cm, above unchanged 2e-8.

All 136 held-out random rays agree with the current exact reference on this bank.
There are 0 candidate BLOCKED cases in the common bank, separately from the 128
blocked retained stress cases. The root-ordering invariant is not established.
No kernel is eligible for promotion or method competition.

Validation: old CTests 2/2 PASS; seed CTests 3/3 PASS; imported offline exact-oracle
arithmetic tests 8/8 PASS. Sol/High independently reviewed the numerical patch
and approved only its experimental scope. Capacity guards are explicit but
exhaustion stress coverage is not complete. See FAST_RECOVERY_04_REVIEW.md.

## One field period and remaining work

Direct NetCDF `nfp=4` agrees with coil header `periods 4`: sector is 90 degrees.
`recovery04/sector-1cm.json` conservatively selects 16 finite coils with IDs
1,2,3,8,9,16,17,24,25,32,33,40,41,46,47,48 for x>=0,y>=0. Full finite curves
are retained so neighboring-period portions are not severed. This is not a
first 12 approximation. Membership depends on section size; the qualified 10 cm
payload has a different candidate set. Input symmetry discrepancies are recorded
and not assumed to vanish under exact 90-degree rotation.

This is an input manifest, not a constructed/transport-qualified periodic model.
One-period boundary probes, distributed-source OpenMC, per-coil material/tally
closure and zero-discarded-history transport gates are NOT_RUN because no
eligible fast solver exists. No full blanket or whole-machine transport ran.

Next work is bounded interval/root ordering and the three saved disagreements,
plus classification completeness and explicit geometry admission. Do not add
new representations yet. Later gates: real hit-rich and held-out configuration
banks; periodic member/material mapping; automatic generic VMEC/coil compilation;
local-radius/minor-size fidelity metrics; one-period transport/closure; then
Candidate A first, subsequent methods only when justified, and one final matched
high-fidelity ordinary-DAGMC/Double Down comparison using retained local runtime.
No new fidelity ladder or Double Down comparison has been performed.

## Evidence and failed attempts

- FAST_RECOVERY_04_HISTORY.md: audited timeline and what did not work.
- FAST_RECOVERY_04_PREFLIGHT.md and FAST_RECOVERY_04_REVIEW.md: resources and review.
- recovery04/baseline-historical-03: valid historical-bank reproduction.
- recovery04/frozen-final-off and frozen-final-on: complete primary captures and reduction.
- recovery04/retained-old-01 and retained-seed-01: per-ray comparisons including blocks.
- recovery04/retained-input.txt and retained-exact-reference.jsonl: losslessly copied source evidence.
- recovery04/wistell-coils-1cm.h5: exact local benchmark payload copy, SHA 9bb178...3262b.
- build/recovery-04-controls and recovery-04-profiles: local binaries, build commands and logs.

Failed HDF5 dataset selection, Linux Git worktree-path failure, rejected harness
preparations v0/v1 and pre-edit duplicate-bank timings remain retained. They are
excluded from the primary scoreboard. Restart commands are in FAST_RECOVERY_04_RESTART.md.
