# Periodic root correctness

The forced-general periodic patch kernel passed 100,000 deterministic randomized exact-torus rays and 4,099 adversarial rays with zero missed roots, false roots, wrong nearest roots, or adversarial failures. The exact-torus specialization was forcibly disabled and the production path made zero calls to the broad global oracle.

The maximum distance difference from the independent broad oracle was `5.553125514978774e-9 cm`; the maximum accepted fast residual was `9.990860164587628e-11 cm`.

The larger campaign exposed and fixed a periodic ownership defect: `atan2` can return a negative poloidal angle equivalent to a patch in the upper half of `[0, 2π)`. Local recovery found the correct root but rejected it until patch membership canonicalized both periodic angles.

Evidence: `dev/stellarcsg/benchmarks/raw/periodic_forced_general_100k_20260831.json`.

The preregistered 10-million-ray target and a randomized WISTELL-D-versus-oracle campaign remain not run; this is a milestone report, not final qualification.
