# StellarCSG performance-redesign baseline

Recorded 2026-08-31 from source commit `379850112dad4f89645005b27e40468e7c89413a` on the isolated performance branch. All transport comparisons used one OpenMP thread and the same local pinned OpenMC/DAGMC image. The exact-torus and coil reproductions were constrained to Docker CPU 2; turbo was not disabled.

## Result

The baseline confirms an algorithmic split, not a small optimization problem:

| Representation | Median histories/s | Relative result |
|---|---:|---:|
| Built-in OpenMC ZTorus | 774,121.5 | reference |
| Periodic-spline exact-torus specialization | 351,233.0 | 45.4% of built-in; 5.90x fine DAGMC |
| Coarse DAGMC exact torus | 70,646.5 | 9.13% of built-in |
| Fine DAGMC exact torus | 59,484.8 | 7.68% of built-in |
| WISTELL-D generic periodic CSG | 89.11265 | fine mesh is 197.04x faster |
| WISTELL-D fine direct mesh | 17,558.65 | reference for this matched plasma pair |
| WISTELL-D representative swept coil | 0.2376435 | fine mesh is 840.68x faster |
| WISTELL-D representative fine coil mesh | 199.783 | short three-history reproduction |

The exact torus specialization delegates to one quartic solve and passes geometry debug. The generic WISTELL-D periodic path calls the complete reference ray scan. The generic swept path combines a complete ray scan with a complete centerline scan and 48 golden-section steps for every surface evaluation. These structures explain the two-to-three-order-of-magnitude gaps.

The WISTELL-D generic periodic run had no lost particles or detected geometry errors, but leakage was 0.93 rather than 1.0. It therefore fails both the performance and leakage-closure gates. The representative coil runs had zero lost particles, zero detected geometry errors, and leakage 1.0, but fail performance.

Both DAGMC torus meshes reproduced the retained OpenMC geometry-debug complaint between the explicit DAGMC volume and its implicit complement. Normal transport completed with zero lost particles and leakage 1.0. This remains an explicit qualification failure rather than being discarded.

## Tests and environment boundary

The clean standalone Release build passed 2/2 C++ tests. The Python suite passed 13 tests and skipped one optional OpenMC-Python import test because that installed package lacks `openmc.data.endf`. The joint experimental OpenMC/DAGMC executable rebuilt successfully. The native torus geometry-debug cases passed; the DAGMC torus debug status is classified above.

A sampling profile could not be collected without changing the frozen environment: Linux `perf` is absent and performance events are restricted (`perf_event_paranoid=2`), while Windows WPR does not reliably attribute optimized Linux-container user symbols. The two profile text files retain this blocker, the exact call graphs, source-level work accounting, and measured transport timings.

Raw repetitions, hashes, commands, environment details, and caveats are in `PERFORMANCE_REDESIGN_BASELINE.json` and `PERFORMANCE_REDESIGN_STARTING_STATE.json`.
