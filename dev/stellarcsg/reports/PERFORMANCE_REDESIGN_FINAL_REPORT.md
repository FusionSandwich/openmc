# StellarCSG performance redesign — final report

## Outcome

The production global searches were replaced with local accelerated kernels. Periodic surfaces now use conservative spline-span patches, proxy triangles, a front-to-back flattened BVH2, projected damped Newton correction, and bounded patch-local recovery. Swept coils now use exact cubic Bézier span hulls, conservative swept boxes, a flattened span BVH2, capsule proxies, circular/general local narrow phases, and bounded span-local recovery. Neither production path calls the broad correctness oracle.

The shared 48-coil WISTELL-D BVH is the strongest result: native smooth CSG reached **289,656 histories/s**, versus **49,189.5 histories/s** for the fine direct DAGMC mesh, making native **5.889× faster**. The representative single-coil gate still fails at 0.4749× fine DAGMC, so the result is specifically a set-level acceleration success, not a claim that every swept query beats mesh.

Branch: `codex/stellarcsg-native-csg-foundation-20260828`  
Evidence commit before this report: `1353d0ae5`  
No pull request was created. `develop`, `master`, and other branches were untouched. The experimental option remains default OFF.

## Commits created

1. `0a88df565` — Record StellarCSG performance redesign baseline
2. `4e97b2480` — Add local periodic patch intersection kernel
3. `03cb4f99c` — Replace swept-coil global search with local span kernel
4. `e48c21639` — Add shared swept-coil set BVH
5. `1353d0ae5` — Retain matched complete coil-set qualification

## Exact performance results

All ratios below use results from the same machine/model/thread/source contract within each row. Results from different contracts are not combined.

| Case | Path | Raw histories/s | Median | Result |
|---|---|---:|---:|---|
| Built-in torus | exact OpenMC `ZTorus` quartic | 726,602; 821,641 | 774,121.5 | baseline analytic specialization |
| Spline torus | exact periodic-torus quartic specialization | 346,566; 355,900 | 351,233 | 0.4537× built-in; 5.9046× fine DAGMC torus |
| Forced-general torus | general periodic patch path | OpenMC timing not run | — | 100,000 random + 4,099 adversarial correctness rays passed |
| Shaped axisymmetric | intended specialization | not run | — | NOT RUN |
| Synthetic helical | general periodic path | distance/OpenMC timing not run | — | evaluate/normal baseline only |
| WISTELL-D plasma | general periodic patch CSG | 26,640.6; 26,347.0; 26,766.6; 26,643.8; 27,147.2 | 26,643.8 | 1.2386× fine DAGMC; minimum PASS; preferred 1.3× FAIL |
| WISTELL-D plasma | fine direct DAGMC | 21,536.0; 21,511.8; 21,495.6; 21,524.1; 21,464.2 | 21,511.8 | reference |
| Representative WISTELL-D coil 031 | general swept CSG | 437,242; 430,810; 432,436; 432,159; 431,245; 437,937; 438,816 | 432,436 | 0.4749× fine DAGMC; Gate F FAIL |
| Representative coil 031 | fine direct DAGMC | 910,031; 920,409; 876,754; 910,634; 893,160; 917,139; 930,594 | 910,634 | reference |
| Complete WISTELL-D 48-coil set | shared BVH native CSG | 282,641; 290,018; 293,974; 285,629; 276,564; 289,656; 294,127 | 289,656 | Gate G PASS |
| Complete set | coarse direct DAGMC | 69,991.3; 70,287.4; 69,975.2; 69,868.9; 68,273.2; 69,198.3; 65,293.7 | 69,868.9 | native is 4.146× faster |
| Complete set | fine direct DAGMC | 47,690.1; 46,870.8; 48,408.6; 50,935.4; 49,189.5; 52,433.8; 51,821.0 | 49,189.5 | native is 5.889× faster |
| Complete set | Double Down / Embree | unavailable | — | BLOCKED; pinned binary is `nompi_nodoubledown` |

The complete-set OpenMC coefficients of variation were 2.05% native, 2.37% coarse DAGMC, and 3.99% fine DAGMC. Each repetition used 100,000 histories, one thread pinned to CPU 2, identical source/materials/seed, and randomized method order.

## Geometry-kernel results

WISTELL-D periodic plasma: 11,826.72 ns/distance, 6.696 candidate patches/ray, 66.713 BVH nodes/ray, 16.953 Newton iterations/ray, and 0.464 local subdivision calls/ray.

Representative WISTELL-D coil 031: 631.624 ns/distance, 213.908 ns/classification, 0.728 candidate spans/ray, 7.978 BVH nodes/ray, 2.015 Newton iterations/ray, and 3.7% local bounded fallback.

Complete 48-coil set: 1,060.176 ns/distance in the scaling sweep, 2.858 candidate coils/ray, 0.766 candidate spans/ray, 23.585 combined top-level/span BVH nodes/ray, 1.105 Newton iterations/ray, and 0.657% local bounded fallback. Increasing the set from 1 to 48 coils increased cost only 2.29×. Production global-oracle calls were zero.

Across 13 stellarator configurations—FPP11.5, HELIAS 5B-like, Landreman–Paul QA, NCSX, QA nfp=1–7, W7-X, and WISTELL-D—the selected most-nonplanar coil passed 100 independent-oracle rays. Total: 1,300 rays, zero mismatches. The single-pass 1,000-ray times ranged from 0.850 to 7.993 microseconds, with median 1.147 microseconds; these short timings show shape coverage and should not be treated as stable cross-device ranking.

## Correctness and geometry-debug

- Forced-general exact torus: 100,000 randomized plus 4,099 adversarial rays; zero misses, false roots, or wrong nearest roots; maximum distance error `5.5531e-9 cm`.
- Representative non-planar coil 031: 1,000 oracle rays; zero mismatches.
- Complete 48-coil set: 1,000 rays versus brute per-coil fast scans plus 100 rays/4,800 per-coil broad-oracle solves; zero mismatches; maximum distance error `1.1162e-9 cm`.
- Thirteen selected real coils: 1,300 independent-oracle rays; zero mismatches.
- Native WISTELL-D plasma, representative coil, and complete set geometry-debug: PASS; zero lost particles.
- Ordinary DAGMC transport: zero lost particles. OpenMC geometry-debug: FAIL with explicit-volume/implicit-complement overlap (`10049, 10001` for the set). Independent mesh validation still reports watertight, nonoverlapping mesh volumes; both facts are retained.

## Common geometry accuracy

The complete native set evaluates the authoritative compiled swept surface directly. Fine DAGMC uses 2,359,296 triangles and has sampled maximum/RMS/p95 surface deviations of 0.10262/0.02704/0.06363 cm. Its enclosed-volume error is -0.30365%. Coarse DAGMC uses 73,728 triangles, sampled maximum/RMS/p95 deviations of 6.24965/1.60475/3.57005 cm, and -6.33494% volume error. All mesh surfaces have zero boundary edges.

The requested symmetric two-sided Hausdorff and maximum normal-angle metrics were not run; the retained chordal samples are not relabeled as those metrics. Quantitative minimum clearance was also not retained. Therefore WISTELL-D coil speed is compared against mesh approximations of the same authoritative surface, but the full common-accuracy campaign is incomplete.

## Build and test commands

```text
cmake -S dev/stellarcsg -B build/stellarcsg-release -DCMAKE_BUILD_TYPE=Release -DSTELLARCSG_BUILD_TESTS=ON
cmake --build build/stellarcsg-release -j2
ctest --test-dir build/stellarcsg-release --output-on-failure

cmake -S dev/stellarcsg -B build/stellarcsg-gcc-sanitize -DCMAKE_BUILD_TYPE=Debug -DSTELLARCSG_ENABLE_SANITIZERS=ON -DSTELLARCSG_BUILD_TESTS=ON
cmake --build build/stellarcsg-gcc-sanitize -j2
ctest --test-dir build/stellarcsg-gcc-sanitize --output-on-failure

PYTHONPATH=dev/stellarcsg/python python -m pytest dev/stellarcsg/python/tests -q

cmake --build build/openmc-stellarcsg-enabled --target test_stellarcsg_surface -j2
./build/openmc-stellarcsg-enabled/bin/test_stellarcsg_surface

docker run --rm -v <repository>:/work -w /work/build/openmc-stellarcsg-dagmc-container --entrypoint /bin/bash parastell-openmc:0.16.0 -lc "cmake --build . --target openmc -j2"

python dev/stellarcsg/benchmarks/run_wistell_coil_set_openmc.py --histories 100000 --repetitions 7 --debug-histories 10000
python dev/stellarcsg/benchmarks/run_multiconfig_coil_microbench.py
python dev/stellarcsg/benchmarks/plot_wistell_coil_set_results.py
```

Final counts: standalone Release 2/2 pass; GCC ASan/UBSan 2/2 pass; Python 13 pass and 1 optional-ENDf skip; OpenMC adapter 3 cases/22 assertions pass; broader enabled OpenMC suite 12/13 pass, with only `test_mcpl_stat_sum` failing because optional `libmcpl` is absent; default-OFF OpenMC build pass.

## Gate table

| Gate | Status | Basis |
|---|---|---|
| A — forced-general exact torus | NOT RUN | initial correctness passed; OpenMC performance not run |
| B — shaped axisymmetric | NOT RUN | no current OpenMC gate |
| C — synthetic helical | NOT RUN | no distance/OpenMC gate |
| D — WISTELL-D plasma | PASS minimum / FAIL preferred | 1.2386× fine DAGMC; accuracy closure incomplete |
| E — planar coil | NOT RUN | initial 100-ray correctness only |
| F — non-planar coil | FAIL | native 0.4749× fine DAGMC |
| G — complete coil set | PASS | native 5.889× fine DAGMC; zero native lost/wrong roots |
| Embree / Double Down | BLOCKED | unavailable in pinned binary |
| Tier 3 materialized | NOT RUN | deferred after incomplete gates |
| Blanket layer family | NOT RUN | not implemented |

## Retained artifacts

- `dev/stellarcsg/reports/PERIODIC_PATCH_KERNEL_REPORT.{json,md}`
- `dev/stellarcsg/reports/COIL_PATCH_KERNEL_REPORT.{json,md}`
- `dev/stellarcsg/reports/DAGMC_MATCHED_COMPARISON.{json,md}`
- `dev/stellarcsg/reports/COMMON_GEOMETRY_ACCURACY.json`
- `dev/stellarcsg/benchmarks/raw/wistell_coil_set_openmc_20260831.json`
- `dev/stellarcsg/benchmarks/raw/wistell_coil_set_scaling_20260831.json`
- `dev/stellarcsg/benchmarks/raw/multiconfig_coil_local_kernel_20260831.json`
- `dev/stellarcsg/plots/performance_redesign/wistell_coil_set_geometry_comparison.png`
- `dev/stellarcsg/plots/performance_redesign/wistell_coil_set_scaling.png`
- `dev/stellarcsg/plots/performance_redesign/wistell_coil_set_openmc_speed.png`
- `dev/stellarcsg/plots/performance_redesign/multiconfig_coil_geometry_atlas.png`
- `dev/stellarcsg/plots/performance_redesign/multiconfig_coil_kernel_speed.png`

The redesign answers the central performance question positively for WISTELL-D periodic plasma and especially for the complete coil set, while preserving the failed single-coil gate and incomplete adoption work without qualification inflation.
