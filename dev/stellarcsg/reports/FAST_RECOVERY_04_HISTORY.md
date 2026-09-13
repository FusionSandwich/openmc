# Historical audit before production edits

All seven requested archive reports were inspected at c67b68fd, as were the
continuation reports and named source diffs. Entries below are different banks
unless explicitly stated; they are not a paired speedup experiment. Missing
measurements are not zero. Arbitrary precision means GMP/rational algebra,
not exact analytic geometry represented with binary64 coefficients.

| Commit / bank | Distance algorithm | Classification algorithm | Correctness evidence | Distance ns/query | Classification ns/query | OpenMC histories/s | Known failure / limit | Arbitrary precision hot path |
|---|---|---|---|---:|---:|---:|---|---|
| 379850112, historical WISTELL | Global scalar reference scan | Global/reference evaluator | Incomplete | unmeasured | unmeasured | plasma 89.11; coil 0.238 | Global scan cost; plasma leakage discrepancy | no |
| 4e97b2480, WISTELL plasma bank | Local periodic patches, BVH, projected Newton, bounded recovery | Local patches | Random real oracle closure incomplete | 11826.72 | unmeasured | 26643.8 | Below preferred 1.3x mesh gate (1.239x) | no |
| 03cb4f99c, coil031 Fibonacci bank | Cubic spans, flattened BVH, capsules, circular Newton | Centerline BVH, golden/Newton refinement | 1000 sampled oracle rays, zero mismatches | 631.624 | 213.908 | 432436 | Single-coil slower than fine ordinary DAGMC (0.475x); later missed entry | no |
| e48c21639 / 1353d0ae5, full48 bank | Shared coil BVH above local swept kernel | Same local evaluator | 100 independent set rays / 4800 per-coil solves; initial zero mismatch | 1060.176 | unmeasured | 289656 | Initial sampled evidence only; 5.889x fine ordinary DAGMC | no |
| c67b68fd preserved archive | Same qualified fast kernel | Same | Reports above preserved; later adversaries invalidate universal correctness | same retained evidence, not a new run | same retained evidence | same retained evidence | .502 instead of .002; unsafe seed pruning and unresolved ordering | no |
| 81211f7b, Track-B | Adds inside-capsule seed | Existing | Scoped missed-entry repair, not completeness | unmeasured | unmeasured | unmeasured | Unsafe best/seed pruning retained | no |
| 4e1efc947, Track-A continuation bank | Admissible-start seed, removes unsafe proxy-seed pruning | Existing | Polynomial bank changed 273 PASS/88 FAIL/23 BLOCKED to 361/0/23; two tangent metamorphisms remain | 2784.93 | evaluate proxy 708.613 | NOT_RUN | No ordering proof or accepted transport | no |
| da7a5417, exact lineage | Exact rational resultant, gcd/Sturm isolation, explicit unresolved rejection | Exact circular nearest-point stationary-root isolation | Restricted circular geometry certificate; later 256/0/128 retained replay | unmeasured here | unmeasured | unmeasured | Rejects unresolved/unsupported inputs; exact cost | yes on candidates |
| 223ea7a1, shared integration | Exact shared-query reuse/accounting | Exact circular nearest-point isolation | Native negative controls; diagnostic integration | unmeasured here | unmeasured | diagnostic only | Cache benefit is not cold speed | yes on candidates |
| 0b56166b, filtered lane | Outward BVH + floating Bernstein exclusion before exact solve | Exact circular nearest-point isolation | Arithmetic regressions; uncertain candidates retained | later 16-ray mode1 81300614 | unmeasured | unmeasured | Broad-phase-only aggregate gain inconclusive | yes on retained candidates |
| dc76fbd1, fast03 16-ray bank | Exact-rational monotone isolation before gcd/Sturm | Exact circular nearest-point isolation | 64 comparisons identical; retained384: 256 PASS,0 FAIL,128 BLOCKED | mode2 2130900.1; mode0 82453404.5 | unmeasured | diagnostic1000: 7.05622 | 98.213% instrumented time inside exact-query region | yes |
| 5ed327ad | Same production as dc76; native-sentinel checksum correction only | Same | Same production evidence | same, not a new independent run | unmeasured | same diagnostic | Zero timed Sturm fallback does not mean zero rational hot-path work | yes |

Evidence: archive reports PERFORMANCE_REDESIGN_FINAL_REPORT.md,
COIL_PATCH_KERNEL_REPORT.json, PERIODIC_PATCH_KERNEL_REPORT.json,
COIL_ROOT_CORRECTNESS.json, OPENMC_GEOMETRY_SPEED_RESULTS.json,
WISTELL_D_FIDELITY.json, ANALYTIC_GEOMETRY_FIDELITY.json. Source diffs were
checked at the named SHAs, including Track-B before/after exact introduction.
Continuation evidence is in stellarcsg-neutral-03 at 4370d957,
dev/stellarcsg/reports/CONTINUATION_20260913.md and local
D:/codex-verification/stellarcsg-20260913-03. Track-A measurement JSON is
dev/stellarcsg/plots/dual_track/continuation_20260913/measurements.json.

## What did not work

- The original global scan was far too slow and did not close all fidelity
  and leakage gates.
- The old capsule/Newton path was fast but did not resolve every earlier
  interval. Its sampled historical PASS did not cover the later near entries.
- An inside-capsule seed alone does not make seed-based best pruning valid.
- First successful Newton root and small residual do not establish ordering.
- Fixed local sign scans cannot certify even roots or a narrow crossing pair.
- Exact gcd/Sturm everywhere repaired important defects but made ordinary
  queries milliseconds long. Exact monotone isolation improved that lane but
  still spent almost all query time inside exact work.
- Single-coil ordinary-DAGMC parity did not pass historically, even when the
  complete48 native set did. No Double Down result may be inferred.
- The 23 prior blocked stress cases, later128 geometry blocks and transformed
  tangent discrepancies are retained evidence, not discarded rays.
- Full blanket overlap and mesh explicit/implicit-complement debug overlap
  invalidate those configurations as clean performance demonstrations.
- Recovery attempt01 failed because Linux Git cannot interpret the absolute
  Windows worktree gitdir; source identity is supplied from Windows Git.
- Recovery attempt02 used the wrong qualified HDF5 group names; no coil/plasma
  timing from that attempt is valid. The historical 1cm benchmark payload is
  distinct from qualified 10cm geometry. Failed stdout/stderr are retained.

No new representation competition is authorized by the achieved gates yet.
