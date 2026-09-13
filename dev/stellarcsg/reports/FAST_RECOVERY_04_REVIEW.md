# Independent review and experiment scope

Sol/High reviewed the candidate loop before implementation, the final source
diff after implementation, and the sector hull-membership script. Astra retains
the numerical interpretation and promotion decision. Review outcome:
**approved for an experimental seed-regression checkpoint only**.

At the retained seam ray c(0)+(.252,0,0), radius .25, direction -x, the true
surface has a hit at .002 cm. The inflated capsule contains the ray origin;
discarding its backward entry leaves a forward exit seed that converges to
.502 cm. The repair adds the admissible interval start only when it is inside
the capsule, keeping ordinary box misses cheap. It also removes both unsafe
best-distance filters on seeds: Newton may move a distant guess to an earlier
root. The existing six capsule roots plus one start fit the seven-slot buffer.
Final accepted roots still require positive distance above the coincidence push.

Stack and unresolved-span capacity now throw before writing or silently
truncating. This does not resolve the other incomplete candidate states.

## Rejected claims

The patch does not prove that every earlier candidate has been resolved or
excluded. One converged seed may conceal another root in the same span.
Zero-proxy cases, fixed eight-bin sign scans, unordered local recovery,
tangent/even roots, and floating AABB/slab pruning remain unproved. The legacy
solver-path name and certified_excluded_intervals field are not a certificate.
Classification's golden/Newton projection also lacks exhaustive stationary-root
proof. The root-level production flag remains OFF by default.

The retained384 comparison changed from four admitted mismatches to two.
The two .502/.002 entries are repaired, including their direction-scaled and
rigid-transform replays. Both nominal tangent cases remain failures at the
unchanged 2e-8 cm comparison threshold. All128 reference geometry blocks remain
reference BLOCKED; the experimental kernel still returns values on those inputs
and therefore has not implemented the reference's geometry admission contract.
No preferred production candidate or new-method eligibility is claimed.

## Harness corrections retained as negative evidence

Preparation v0 used incorrect physical direction-scaling semantics, mislabeled
ordinary rays as tangents, and mixed candidate/reference exception status.
Preparation v1 corrected those issues but accidentally duplicated a07 and a14.
Both CSVs are retained under qualification/recovery04_rejected_preparation_v*.csv.
The final bank changes only the duplicate outer-miss offset (a07 z=.25001)
and validates all160 input tuples. The kernel was not tuned against that change.
The pre-edit v1 timing is retained but is excluded from primary unique-bank
measurements. The full old/new/reference comparison uses the final bank only.

Primary distance timing excludes offline reference, classification and normal
calls. Classification/evaluation and normal use distinct compiled instances to
avoid the one-entry point cache, and physical hit points use normalized ray
directions. Allocation/memory and unavailable fallback telemetry remain unknown,
not reported as measured zero. No GMP or exact fallback was added to this kernel.

## Incremental local build preflight

Before seed/control builds, free host memory was 1,446,916 KiB, C: free space
61,932,941,312 bytes and D: 59,302,469,632 bytes. Significant desktop processes,
existing GCC14.2/CMake3.31/HDF5/Python environments, and caches remain as recorded
in FAST_RECOVERY_04_PREFLIGHT.md. No dependency acquisition is needed (0 bytes).
Use serial compilers. New outputs are confined to this recovery worktree's
build/recovery-04-* directories, plus the worker's initial small standalone
helper in C:/Users/joshu/AppData/Local/Temp (documented, no running process).
Build/benchmark logs are retained; no automatic cleanup is performed.
Previous A is rebuilt Release because its retained HDF5 probe had no build
type and cannot serve as a matched optimized performance control.
