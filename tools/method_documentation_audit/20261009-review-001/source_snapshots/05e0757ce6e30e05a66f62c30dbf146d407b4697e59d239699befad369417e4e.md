# Plasma and coil proxy qualification — 2026-09-26

Both surface families ran in native OpenMC CSG transport. The new certified
Bernstein-prefix accelerator is for `exact_control_offset` swept **coil**
surfaces; plasma uses the separate periodic-surface implementation and its
exact-torus specialization. These results do not make the general plasma or
physical magnet-pack models production-ready. The 80% native-throughput goal
was **not met** by either tested spline proxy.

## Matched experiment

The fixed plan in `ACCEPTANCE_PLAN.md` completed all 18 runs, sequentially on
one local CPU thread, with the same executable/library, nuclear data, paired
seeds, source bank, material, estimator and counts within each comparison.
There were no lost-particle/unresolved diagnostics or nonzero transport exits.
The six plasma runs total 120,000 source histories; the twelve coil runs total
2,400. Each comparison has three seeds and 20 paired batches per seed.
Pilots are excluded from timings and statistical comparisons.

Plasma is a void R=100 cm/r=20 cm torus inside an identical 1 cm Fe56 shell.
The native ZTorus and constant-coefficient PeriodicSplineSurface describe the
same boundary. Coil material is a radius-5 cm round tube around a 64-control
near-circular R=100 cm spline, compared with a native round torus. Exact
Fraction/Bernstein bounds prove centerline radial deviation below 0.243
micrometres. An additional ring uses two cylinders at radii 95/105 cm and
planes at z=±5π/4 cm: it has the native tube's volume but a different section.

All material is Fe56, 7.8 g/cm3 at 300 K, using the already-local FENDL-3.1d
file with MT444. The source is a fixed bank of 256 isotropic directions at
(100,0,0), 14.1 MeV. Statistical statements are conditional on that empirical
source distribution. These are controlled material proxies, not the full
multi-material magnet or fusion-device source model.

## Results

Throughput is histories per recorded OpenMC transport time, excluding startup,
data loading and statepoint writing. Values below are the mean of three paired
ratios; `analysis-summary-02.json` also records ratios of summed times.

| Comparison | Relative throughput | Observed equivalent bins / 32 | Sampled implementation check |
|---|---:|---:|---|
| Plasma spline / native torus | 62.08% (58.50–65.04%) | 28; 4 insufficient | Pass |
| Coil accelerated / native torus | 0.1299% (0.1141–0.1395%) | 24; 8 insufficient | Different represented geometry |
| Coil accelerated / unaccelerated | approximately 2.49× | 24; 8 insufficient | All 1,920 batch-bin values identical |
| Annular ring / native torus | 125.14% | 4; 8 insufficient, 20 not equivalent or underpowered | Different section; descriptive only |

The native coil timing is only about 3 ms per run, versus 2.33–2.73 s for the
accelerated spline. Three short pairs do not establish a portable precise
speed ratio, but the observed gap is much larger than the 80% acceptance
margin. Plasma comparison exercises the exact specialization, not a general
stellarator boundary. No general-shaped plasma speed claim follows.

All four integral scores (flux, total, absorption, damage-energy) satisfy the
planned 1% paired equivalence criterion for plasma and coil/torus comparisons.
Plasma integral relative differences are below 3.4e-15. Coil/torus relative
differences are below 1.21e-7; damage-energy differs by -1.08287e-7. Every
spectral sum closes to its integral, and cell/material ownership tallies agree.
These are sampled results. The simultaneous Bonferroni Student-t intervals
are a finite-batch approximation, not a rigorous sparse-event guarantee.
Four plasma and eight coil low-energy score bins have insufficient coverage;
**complete spectrum equivalence remains unqualified**.

The NRT test convention is 0.8×damage-energy/(2×40 eV×atoms), per source.
Mean plasma-shell indices are 4.85167524784306e-26 (native) and
4.85167524784308e-26 (spline). Mean common-reference coil indices are
3.20406563332938e-25 (native) and 3.20406528637153e-25 (spline), with accelerated
and unaccelerated values identical. This checks conversion consistency, not
physical device DPA/time. The exact prepared spline-tube volume lies in
[49348.01506445773, 49348.01618459467] cm3, compared with native
49348.02200544679 cm3. Actual-volume correction is recorded separately in
`analysis-summary-02.json`; its interval covers geometry normalization only,
not Monte Carlo uncertainty. No irradiation rate, DPA/s or DPA/year is claimed.

## Correctness tests and repaired issues

- Fresh independent exact certificates accept all 160 frozen rays in each
  accelerator mode: 69 first hits and 91 complete no-hit exclusions, absolute
  hit-distance error bounded by 1e-11 cm. See `qualified-on.json` and
  `qualified-off.json` with their bound oracle/support certificates.
- Added 48 translated/scaled seam crossing checks and thin-chord cases missed
  by all 128 initial proposals. The latter must use the ordered fallback.
  `offset-tests-03.txt` passes. Native entry/exit, sense and normal checks in
  `native-probe-02.jsonl` also pass on the final library.
- A tight bounding-box endpoint could prevent sign certification. The repaired
  search expands the eligible interval outward while preserving the initial
  coincident exclusion and all certificate/acceptance conditions. Failed
  pre-fix tests are retained as evidence.
- Plasma exact specialization previously accepted almost-constant coefficients
  and replaced them with averages. It now requires exact coefficient equality;
  one-ULP perturbations must use the general path. Added checked-dimension
  multiplication before spline allocations. Compiled-surface tests pass.
- The on/off option now round-trips through Python/XML/HDF5 and rejects invalid
  values or explicit use with the legacy representation. Final Python checks:
  14 tests and 16 subtests pass (`python-final-tests.txt`).
- Eleven actual-artifact forgery controls are rejected, including altered
  timing, redistributed spectral bins with unchanged totals, wrong seed in
  both launch/receipt, missing statepoint, MT444, Ed, NRT, uncertainty, nonzero
  exit, timeout and raw unresolved diagnostics. See `artifact-audit.json`.
- Pilot tracks contain 61 recorded states across plasma and both coil modes;
  all recorded material/cell ownership is consistent. This is not independent
  certification of every collision. Production tally closure provides a
  separate check.

The first comparison attempt rejected OpenMC's zero-padded statepoint names;
the checker was corrected and the existing transport files revalidated.
The first native-probe invocation named a nonexistent target; it did not run.
Both failed invocations are retained. Only the successful suffixed results
above are used for acceptance. Source and transport inputs were frozen during
the campaign; build-04 binds the executable/library to observed input hashes.

## Remaining upstream gates

1. Profile and reduce general coil certificate/projection/allocation costs;
   profile plasma evaluate/normal/distance dispatch. Repeat isolated longer
   native timings after changes. Neither path currently meets the speed goal.
2. Add independent tests for non-axisymmetric plasma transport and more real
   coil positive hits. This proxy campaign does not validate all supported
   geometry or the inherited general periodic solver.
3. Qualify full physical rectangular/varying-frame magnet packs, collections,
   material interfaces, periodic/reflective boundaries, photons, multithreading,
   and representative energy/source distributions separately. Unsupported
   exact-offset representations must continue to fail closed.
4. Resolve the previously known nine ambiguous/unsupported normal queries and
   legacy source-loader swapped-hash false-PASS; this work does not repair them.
5. Populate the sparse spectral bins and test real material compositions with
   an appropriate displacement model and source normalization. Passing the
   present Fe56 proxy does not qualify production spectra or DPA.
6. Before upstream submission, reduce inherited experimental scope and format
   churn, settle public schema/API support, and run the full applicable OpenMC
   regression/portability matrix. The current PR remains a draft.

The independent review is `REVIEW_FINAL.md`. Raw HDF5, fixtures and build
products remain local ignored artifacts; committed receipts preserve hashes
and numerical observations, not a self-contained distribution of nuclear data.
