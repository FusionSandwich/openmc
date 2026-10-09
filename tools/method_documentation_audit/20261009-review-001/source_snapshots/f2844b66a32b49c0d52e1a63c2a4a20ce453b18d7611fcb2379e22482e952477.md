# Torus-class pre-change baseline

Status: **PASS — baseline frozen before algorithm changes**

The research branch was measured at `5faf87421d5d2066278c7ae02e38138fc22ec894`. The preserved qualified commit and archive ref remain `c67b68fdaf7be2049308db7da449f14a25123847`. No geometry-algorithm source had been changed when this baseline was recorded.

## Clean matched exact-torus result

Both cases used the same OpenMC executable, one OpenMP thread pinned to CPU 2, the same point source, seed 918273645, five batches of 200,000 particles (1,000,000 histories per repetition), one warm-up, seven measured repetitions, and randomized case order. No unrelated Docker workload was running.

| Geometry | Raw histories/s | Median histories/s | Relative to built-in | Lost | Geometry debug |
|---|---:|---:|---:|---:|---|
| Built-in OpenMC ZTorus | 793337, 799357, 774555, 782555, 788791, 773037, 762976 | 782,555 | 1.0000 | 0 | PASS |
| Periodic-spline exact-torus specialization | 348925, 354951, 344174, 351321, 352789, 350821, 347503 | 350,821 | 0.4483 | 0 | PASS |

Each debug run completed 1,036,642 overlap checks for each of the two cells. This reproduces the retained qualified result (351,233 versus 774,121.5 histories/s, or 45.37%) and shows that the current slowdown is not a geometry mismatch.

## Retained qualified end-to-end evidence

| Case | Native histories/s | Fine DAGMC histories/s | Native / mesh |
|---|---:|---:|---:|
| WISTELL-D plasma | 26,643.8 | 21,511.8 | 1.2386 |
| Representative non-planar coil | 432,436 | 910,634 | 0.4749 |
| Complete 48-coil set | 289,656 | 49,189.5 | 5.8886 |

The forced-general torus oracle rerun on the current source retained zero missed, false, or wrong-nearest roots across 100,000 randomized and 4,099 adversarial rays. Its maximum distance difference was `5.553125514978774e-9 cm`, and maximum residual was `9.990860164587628e-11 cm`.

The machine-readable record, including raw initialization and transport times, is `dev/stellarcsg/reports/TORUS_CLASS_BASELINE.json`.
