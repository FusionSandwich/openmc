- One-period model: PARTIAL, unchanged 90-degree vacuum-clipped diagnostic; NOT validated periodic geometry.
- Fidelity: prior sampled plasma max 0.20422 cm / 0.11974% local radius; 1 cm circular coil envelopes; winding-pack error and clearance NOT_MEASURED.
- Numerical status: isolated acceptance repair has 2/160 strict wrong results, 12 wrong + 3 BLOCKED stress results, and 2/256 admitted retained failures. The 128 reference geometry blocks remain distinct and are not enforced by recovered production.
- New repaired-candidate one-period throughput: NOT_RUN because kernel gates fail. Prior seed-control clipped diagnostic: 8179.8 histories/transport-second (3 x 8192); not attributable to this repair.
- Toroidal-reference transport ratio: NOT_RUN. Fresh separate ZTorus sentinel median 178.712 ns/query, repeated 64-ray bank, not the cold comparison bank.
- Matched Double Down/Embree: NOT_RUN.
- API/import: prior simple API and WISTELL export retained; held-out ParaStell geometric-theta fold remains rejected.

# Repair 07: partial repair, no promotion

Resumed compare06 at 9c6cc86e0a6543334c973cf5610e58bdb6ad2197 on
2026-09-15. No protected checkout was modified. No acquisition, remote work,
push, PR, mesh run, full-device transport, or new representation experiment.
The historical audit and qualified-fast recovery remain in the inherited
recovery04 reports; this checkpoint does not replace their unlike-bank caveats.

## Branches and ownership

All paths are under C:/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS.

| Worktree | Branch suffix after JS/ | Source SHA / purpose |
|---|---|---|
| stellarcsg-root-repair-07 | stellarcsg-root-repair-20260915-07 | 203948e1439ae0fa51426cb7ad26dddf8975f502, combined experimental production; later test/report-only commit |
| stellarcsg-acceptance-only-07 | stellarcsg-acceptance-only-20260915-07 | 9dab4041670fa835153c1a9c367595d4be7c3d3b, isolated residual + acceptance repair |
| stellarcsg-local-repair-07 | stellarcsg-local-repair-20260915-07 | 48c65bf0ce2d2c41ab1c7e3f19b84b4f67bc9bfc, Terra implementation |
| stellarcsg-crossing-repair-07 | stellarcsg-crossing-repair-20260915-07 | 29ce99ee0b3eca3c0cf78fa07da4cf9cbc0d00b2, Sol crossing experiment |
| stellarcsg-run-compare-06 | stellarcsg-run-compare-20260913-06 | 9c6cc86e0a6543334c973cf5610e58bdb6ad2197, unchanged prior checkpoint |

Luna/Medium performed inventory/reduction, Terra/Medium bounded implementation,
Sol/High independent numerical review and separate crossing implementation.
Root reviewed Sol's implementation; Sol independently reviewed Terra's bounds.
Four available slots, no worker used for redundant full-repository discovery.
Machine/toolchain and zero-byte acquisition audit: REPAIR_07_PREFLIGHT.md.

## Fresh strict-bank scoreboard

Same frozen 160 unique queries, seven fresh-process repetitions per lane,
single CPU affinity, no owned concurrent build/benchmark, counters disabled.
Distance is median of seven complete bank means, not median single-query cost.
P95/P99 are pooled per-query times. The exact_reference lane's candidate is
the exact oracle; its SKIPPED field only disables a second legacy reference call.
Harness PASS is not oracle agreement. All times below are ns/query.

| Method | Distance | P95 / P99 | Classification | Normal | Strict wrong / blocked | Decision |
|---|---:|---:|---:|---:|---:|---|
| Preserved old-fast | 1138.75 | 3800 / 6881 | 1410.625 | 1629.375 | 4 / 0 | mandatory control, incorrect |
| Recovered seed control | 1650.625 | 5100 / 8643 | 1512.5 | 1623.74375 | 3 / 0 | prior control, unqualified |
| Final residual only | 1728.125 | 5305 / 8100 | 1476.875 | 1820.625 | 3 / 0 | no correctness gain; regression exposed |
| All queued nearer fallback | 3266.25 | 11600 / 15000 | 1454.375 | 1615 | 3 / 0 | REJECTED for promotion |
| Broad suspect crossing | N/A | N/A | N/A | N/A | 0 / 21 | overblocking; EXPERIMENTAL |
| Broad crossing + outward bounds | N/A | N/A | N/A | N/A | 0 / 17 | overblocking; EXPERIMENTAL |
| Narrow acceptance + ordering + bounds | 4726.25 | 16105 / 22943 | 1506.875 | 1740.625 | 2 / 0 | 4.15x old; REJECTED for promotion |
| Isolated acceptance repair | 2319.375 | 8400 / 15300 | 1513.125 | 1721.25 | 2 / 0 | 2.0368x old, 1.4051x seed; EXPERIMENTAL |
| Exact reference | 15097177.04375 | 144738601.85 / 230143714.19 | see raw reduction | see raw reduction | oracle lane | correctness reference only |

Blocked-query exception time is not recorded by the existing harness, so a
survivor-only mean must not be used as comparable full-bank performance.
An additional final interleaved seven-repeat confirmation (alternating lane
order, final-paired-strict) measured old/seed/isolated at 1280 / 1806.875 /
2422.5 ns/query. Their P95/P99 were 3600/7681, 5300/8362, and 8605/15581.
Classification was 1515/1555.625/1505.625; normal 1726.875/1833.75/1784.375.
Isolated/old is 1.89258 and isolated/seed 1.34071 in that confirmation.
The observed 1.89-2.04 old-fast ratio straddles the temporary 2x threshold
across campaigns; do not claim a robust margin either way. Correctness failures
independently prevent promotion. The first table preserves all earlier numbers.
Candidate spans, Newton counts, recovery fraction, exact fallback count/time,
allocations and memory are NOT_MEASURED (null, not zero). No GMP was introduced
in these repair lanes; bounded scalar evaluate-based recovery can still be
expensive. Representation remains the original spline, with no deliberate
approximation; this is not a proof of exact binary64 evaluation or winding-pack
fidelity. Native ZTorus is a separate absolute-cost sentinel, not an equivalent
geometry or bank, so no matched ZTorus speed ratio is asserted.

## What changed and what failed

1. Final-iterate residual recomputation fixes stale validation bookkeeping,
   but does not prove a root. Strict failures remained a06/a08/a15. It exposed
   real23's false finite hit at 0.19916695971482617 cm; exact reports no hit.
2. Processing all already-queued nearer unresolved spans removed the old
   first-finite/global-no-hit-only fallback restriction. It fixed no observed
   discrepancy and cost 2.8683x old-fast. It remains a negative experimental
   commit, not the preferred implementation. Zero-proxy and solved-prefix
   coverage were not fixed.
3. Broad crossing conditioning marked unconverged seeds as ambiguous and
   blocked 21 strict rays. Outward center/radius bounds plus necessary
   center-box distance exclusion reduced this to 17, without a new block.
   Neither is a usable baseline. An early single-nextafter Bezier conversion
   was rejected in review and replaced by per-operation interval propagation;
   a subsequent type error was fixed before compilation.
4. Restricting conditioning/refinement to candidates with acceptable residual
   repaired a15: 1.9527658734204012 versus exact 1.9527658734094704 cm
   (isolated lane), about 1.1e-11 cm error versus roughly 3.1e-7 previously.
   The retained .002 cm missed-entry fixture still passes at all three tested
   direction scales. a06 (origin contact) and a08 (even-multiplicity tangent)
   remain silent wrong no-hits. This is acceptance-quality repair, NOT a
   complete nearest-root solver.
5. The isolated lane removes the unhelpful ordering and bounds additions.
   It retains a15's improvement. Its two timing campaigns straddle the 2x
   guardrail; no promotion is justified with the remaining wrong roots.

The unchanged 160-ray real stress bank was replayed once per lane, not used
as a seven-repeat performance campaign. Old/seed/residual/ordering have
34/14/15/15 discrepancies. Both narrowed acceptance lanes have 12 wrong
nonblocked results and three BLOCKED queries (real02, real24, real29).
Thus their 15 discrepancies must not be described as only 12 failures with
everything else passed. real23 is still wrong. The 384-ray retained replay
still reports two wrong-root/metamorphism failures among 256 admitted cases;
the reference's 128 geometry BLOCKED states are preserved verbatim.

Previously unsuccessful approaches also remain retained: 2-D interval cover
(90 root-free / 70 unresolved, about 106397 ns/query), exact-heavy hot paths,
periodic rotation mismatch around 0.00020307 cm, and held-out theta-fold
import. No negative result was deleted or relabeled as a successful repair.

## Tests and independent review

All five isolated stage builds completed with local GCC 14.2/HDF5 Release.
Broad crossing and bounds versions fail seed regression and compiled-surface
tests with explicit unresolved exceptions; reference tests pass. Narrowed
and isolated acceptance versions pass reference and compiled-surface tests.
Seed regression fails only its a08 explicit-unresolved expectation; all six
.002 cm checks and a15 pass. The failure is intentionally retained.
The focused outward-bounds test passes, including cancellation, translation,
parallel slabs, underflow/overflow and near-tangent retention. It is now wired
into CTest with assertions active in Release. Full native integration was not
rebuilt or rerun because the prerequisite kernel gates fail.

Independent Sol review found the outward operations conditionally sound for
the ideal regular spline surface, not a complete production certificate:
regularity of center derivative and supplied normal is not admitted over whole
spans; floating frame/Horner/trigonometric evaluation error is not enclosed by
the raw radius bound; retained spans, zero-proxy cases and earlier-root ordering
remain unresolved. Whole-span integrated bound validation also remains a gap.
The bounds lane is not promoted. The isolated lane deliberately excludes it.

## Restart and evidence

Raw JSONL, stderr, receipts and reductions are under reports/repair07. Receipts
bind binary, source payload and bank hashes. Primary strict bank SHA256:
7348483e39128259a844d22a7618869a3f111604ea48d01e196a87fe0d396af7.
The source/tree association is this table, not inferred from a build directory
name. build/bounds-07 was incrementally updated from b3456ba72 to 203948e14;
its original bank executable is retained as stellarcsg_bounds_control.
build/crossing-07 remains db52faf9c. build/acceptance-only-07 is 9dab40416.

From WSL OpenMC-Dev-D, using only the existing toolchain:

```bash
W=/mnt/c/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS
R=$W/stellarcsg-root-repair-07
A=$W/stellarcsg-acceptance-only-07
B=$W/stellarcsg-fast-recovery-04
P=/opt/openmc-venv/bin/python
cmake -S "$A/dev/stellarcsg" -B "$R/build/acceptance-only-07" -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTELLARCSG_ENABLE_HDF5=ON -DSTELLARCSG_ENABLE_PERFORMANCE_COUNTERS=OFF -DSTELLARCSG_VERIFY_FAST_WITH_ORACLE=OFF
cmake --build "$R/build/acceptance-only-07" --parallel 1 --target stellarcsg_recovery04_bank stellarcsg_retained_replay stellarcsg_swept_seed_regression stellarcsg_reference_tests stellarcsg_compiled_surface_tests
ctest --test-dir "$R/build/acceptance-only-07" --output-on-failure
$P "$R/dev/stellarcsg/qualification/recovery04_measure.py" --lane "acceptance_only=$R/build/acceptance-only-07/stellarcsg_recovery04_bank" --bank "$R/dev/stellarcsg/qualification/recovery04_frozen_bank.csv" --coils "$B/dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5" --output "$R/dev/stellarcsg/reports/repair07/restart-strict" --repetitions 7
$P "$R/dev/stellarcsg/qualification/recovery04_replay.py" --binary "$R/build/acceptance-only-07/stellarcsg_retained_replay" --input "$B/dev/stellarcsg/reports/recovery04/retained-input.txt" --reference "$B/dev/stellarcsg/reports/recovery04/retained-exact-reference.jsonl" --output "$R/dev/stellarcsg/reports/repair07/restart-retained"
```

Use a new output folder on subsequent restarts. Recheck the current machine
before rebuilding under the user-wide acquisition/build rule. Next technical
work is explicit origin-contact semantics and bounded even-root resolution,
then complete earlier-prefix exclusion/admission, not new representations.
Only after those gates pass should one-period transport, attribution/closure,
fidelity/clearance and matched mesh comparison resume. The preferred old/seed
controls are untouched; no corrected method is qualified by this checkpoint.
Preservation receipt checks 22 prior protected/checkpoint refs unchanged.
All owned build/benchmark processes finished and the idle WSL keeper shell
was closed. Experimental StellarCSG remains OFF by default. No push or PR.
