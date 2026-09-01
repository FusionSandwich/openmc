# Exact-torus framework-overhead result

Status: **accepted — 85% hard gate and 95% stretch gate both pass**

The exact periodic-spline torus improved from **350,821** to **730,255 histories/s** (2.082×). In the same randomized seven-repetition run, built-in ZTorus measured **749,597 histories/s**, putting the data-driven exact specialization at **97.42% of built-in**.

| Measurement | Before | After |
|---|---:|---:|
| Periodic exact torus (median histories/s) | 350,821 | 730,255 |
| Paired built-in ZTorus (median histories/s) | 782,555 | 749,597 |
| Periodic / built-in | 44.83% | 97.42% |
| 85% hard gate | FAIL | PASS |
| 95% stretch gate | FAIL | PASS |

## What changed

The adapter caches the exact torus’s major radius, minor radius, and vertical offset during model initialization. Its distance call now goes directly to `openmc::torus_distance`, the same quartic kernel used by `SurfaceZTorus`. Exact-torus classification and normals also use direct algebraic expressions.

This removes per-ray string dispatch, option construction, wrapper conversion, diagnostics/result construction, counters/timers, direction renormalization, and redundant spline residual evaluation. Disassembly confirms that the selected exact branch loads cached values and tail-jumps to the shared OpenMC quartic helper. The reference and all generic periodic paths are unchanged.

## Correctness and regression gates

- OpenMC adapter test: 3 cases, 24 assertions, PASS.
- Standalone C++ tests: 2/2, PASS.
- Python tests: 14/14, PASS.
- Fresh default-OFF build and built-in-torus smoke: PASS, zero lost particles.
- Double Down-linked OpenMC native exact-torus smoke: PASS at 742,169 histories/s, zero lost particles; linkage resolves DAGMC, Double Down, Embree 4, and MOAB.
- Forced-general independent campaign: 100,000 randomized plus 4,099 adversarial rays; zero missed, false, wrong-nearest, or adversarial failures.
- Built-in and periodic OpenMC geometry-debug: PASS, 1,036,642 checks per cell, zero lost particles.

The maximum independent-oracle distance difference was `1.2658900594431088e-9 cm`; the maximum fast residual was `1.2279066652354231e-13 cm`.

Hardware performance counters were not collected because `perf` is absent from the pinned local image and this phase did not justify acquiring software. The paired end-to-end gate is nevertheless decisive: the specialization is now in the same performance class as built-in ZTorus.

One negative observation is retained: a proposed coincident-outward unit expectation assumed infinity, while OpenMC’s shared torus helper returned a finite root for that exact-boundary case. The adapter deliberately preserves the shared helper’s semantics; the invalid expectation was removed, not hidden by a special-case change.
