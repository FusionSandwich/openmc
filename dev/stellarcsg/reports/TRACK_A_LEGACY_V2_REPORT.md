# Track A legacy v2 report

## Current outcome

Track A has reproduced the qualified exact-specialization baseline without changing its periodic-patch or swept-span algorithms. The fresh Release build passed 35 checks: 2 standalone CTests, 21 Python tests (14 qualified plus 7 neutral-harness tests), and 12 OpenMC custom-surface API tests.

| Baseline case | Result | Gate |
|---|---:|---|
| Exact periodic / built-in ZTorus | 734,820 / 722,938 histories/s = 1.01644 | PASS |
| Exact swept / built-in ZTorus | 771,724 / 735,064 histories/s = 1.04987 | PASS |
| Forced-general swept / built-in ZTorus | 69,320.6 / 735,064 = 0.09431 | FAIL |
| Combined WISTELL-D + blanket + 12 coils | 3,436.33 histories/s; 0 lost | diagnostic |
| Combined WISTELL-D + blanket + 48 coils | 2,440.47 histories/s; 0 lost | diagnostic |

The periodic bootstrap 95% interval is 0.97833–1.05872 and the one-sided 95% lower bound is 0.98111. Both exact-specialization non-regression gates pass with zero lost particles. The forced-general result remains a retained negative result and misses the 0.25 minimum.

## Evidence boundary

The build executable SHA-256 is `931099326a5d033f5f1564208b94486dd05e7cd1c92d654659b7cff0b21b791e`; `libopenmc.so` is `0c9dbf6324fa1f92cc6016536966c0eb0f35c7fb60997dbd7903cda4800fae96`. Linux could not resolve the Windows worktree Git pointer, so the embedded version is not authoritative; the branch commit and binary hashes are.

One C0 run had a 99.08 s initialization outlier caused by host activity. Active transport throughput is reported separately. The combined cases remain one-repetition diagnostics. Functional gates beyond the reproduced baseline are explicitly `NOT_RUN` in the gate-status JSON.
