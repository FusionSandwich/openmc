- One-period model generated from supplied inputs: PARTIAL. Native plasma and 16 finite members, 90-degree vacuum-clipped diagnostic; NOT validated periodic geometry.
- Plasma and finite-coil shape errors, section assumptions and clearance: sampled radial max 0.20422 cm / 0.11974% local radius; standardized 1 cm circular coil envelopes; source winding-pack error and clearance NOT_MEASURED.
- Known numerical/navigation defects and geometry-domain exclusions: recovered strict 3/160, retained 2/256 and real stress 14/160 discrepancies remain; 128 reference geometry blocks are not enforced by recovered production.
- Actual recovered-candidate one-period transport throughput: clipped diagnostic measured 8,179.8 histories/transport-second, median of 3 x 8192-history non-debug runs. Validated periodic throughput NOT_RUN.
- Ratio to defined toroidal reference: NOT_RUN. Separate native ZTorus query sentinel: 181.545 ns/query.
- Ratio to matched Double Down/Embree: NOT_RUN.
- Simple API and held-out automated conversion: previously demonstrated public helical-plasma/finite-coil example and WISTELL preparation/export; held-out ParaStell geometric-theta fold remains rejected.

# Run and compare 06

## What was actually run

Fresh full native recovered build from the product-05 production source, then
an isolated old-fast control relink. No production C++ or geometry was changed.
The only production C++/header difference from c67b68fd is the existing
compiled_swept_surface.cpp seed repair (73 added, 44 removed lines). The old
control replaces that one object with the byte-verified preserved source,
reuses the other objects and keeps the recovered library untouched. The
executable is identical; each lane's different shared library is hash-bound
and verified by ldd with its own LD_LIBRARY_PATH.

All lanes use the unchanged product05/model-02 XML and absolute HDF payloads:
NFP=4, 90-degree vacuum sector, 16 individually attributed finite coil members,
native plasma, H1 density 1e-6 atom/b-cm, sixteen equal source boxes,
isotropic 14 MeV neutrons, one batch, one OpenMP thread, seeds 17/19/23.
There is no blanket, mesh substitution, whole-device transport or periodic
boundary claim. Per-cell and unfiltered global track-length flux are paired
on identical input hashes and seeds. Reference is exact-03, not an independent
oracle for shared classification, normal or adapter semantics.

| Workload | Old fast | Recovered seed repair | Exact reference |
|---|---:|---:|---:|
| Debug, 3 x 64 histories: median transport s/run | 0.0198075 | 0.0206138 | 12.9160 |
| Non-debug, 3 x 256 histories: median transport s/run | 0.0337905 | 0.0347802 | 30.4038 |
| Same 256 workload: histories/transport-second | 7576.1 | 7360.5 | 8.4200 |
| Non-debug, 3 x 8192 histories: median transport s/run | 0.9766704 | 1.0014935 | NOT_RUN |
| Same 8192 workload: histories/transport-second | 8387.7 | 8179.8 | NOT_RUN |

These are model-specific observed timings, not qualification or uncertainty
estimates. Initialization and active-batch timing, including statepoint I/O,
are retained separately in receipts; transport-only time is used above.
The 8192 median recovered rate is about 2.5% below old-fast (ratio of medians).
Paired recovered/old transport-time ratios are 1.0478, 1.0722, 0.9551; their
median is 1.0478 and the range crosses parity. Per-seed timing variation
prevents a precise small-overhead conclusion. The exact-reference
cost is about three orders of magnitude larger on the matched 256 workload;
this does not make an incorrect floating solver eligible for promotion.
No ratio is formed between different history workloads or between this model
and historical single-coil/full-48-coil transport. No owned build or numerical
job overlapped the serial timing campaigns. Seeds reuse prefixes between
campaigns, so their history counts must not be summed as unique coverage.

## Correctness evidence and limits

All 24 primary attempts completed with exit 0, requested batch/particle counts,
finite statepoint metrics, unchanged external HDFs, leakage 1, and no lost-
particle or maximum-event warning. All 16 coil bins have positive support
in each lane's campaign aggregate, alongside plasma/exterior bins. Tally closure is a
realized-track check, not proof of all surfaces or periodic geometry.

The frozen absolute reporting threshold remains 1e-12. The debug comparison
retains 25 aggregate tally-metric exceedances versus exact; the non-debug
256 comparison retains 16; the 8192 old-versus-recovered comparison retains 4.
These are NOT root-failure counts, independent failing histories, or a physics
acceptance test. Debug maximum cell delta is 1.35e-11 (absolute) and 2.58e-10
relative in a small bin. No test tolerance was loosened to obtain agreement.
The separate seed-19 track replay completed 64 histories per lane with matching
history identifiers, 234 recorded steps, cell IDs, cell instances and material IDs:
zero discrete sequence differences against exact for either floating lane.
The largest absolute coordinate-component difference is 2.20894e-10 cm.
Direction, energy and weight match bit-for-bit. Every floating lane first
differs from exact at event index 1 in position/time only. Zero-tolerance
floating comparisons differ in every history; the raw first
divergence and per-field maxima are retained, not rounded into a PASS. This
supports common realized path topology for this subset only. It neither
validates every ray in the 8192 campaign nor removes any strict-kernel defect.
All three tracked attempts completed cleanly and their timing is excluded.

Independent Sol review verified paired hashes, completion, leakage and tally
evidence for the debug campaign and reviewed the final numerical comparison.
Focused harness/control/reducer/track tests: 9 passed. `git diff --check` passed.

## What did not work

- The retained seed fix repairs the demonstrated earlier-entry case but does
  not clear the existing strict tangent, boundary-origin and grazing failures.
  This turn changes no solver mathematics and promotes no candidate.
- Exact-reference common-path cost remains unsuitable as the preferred fast
  transport path on this diagnostic. It remains valuable reference evidence.
- The earlier bounded interval-cover prototype retained 70 unresolved cases
  and cost about 106 microseconds/query; it was not promoted into the hot path.
- Earlier coarse plasma fits failed fidelity checks. The selected 256x128 fit
  has sampled radial evidence only, not Hausdorff/normal/volume certification.
- Periodic preparation still rejects the approximately 0.00020307 cm source
  rotation mismatch. Vacuum clipping is not a fix for periodic consistency.
- The first old-control dry run rejected CMake's post-link copy wrapper. The
  corrected builder validates that wrapper but never executes its copy, and
  redirects its dependency file to the isolated control directory. No base
  object/library was overwritten. Earlier loader/source-path harness defects
  were fixed before numerical execution and are retained in commit history.

## Reproducibility and preservation

New branch: JS/stellarcsg-run-compare-20260913-06, starting at product-05
7a8c465e3fd1410e2b59bab4c40d48a61513bd3e. Explicit worker assignments: Terra
Medium for harnesses/reducers, Luna Medium for bounded ref checks (Spark is
not exposed for these subagents), Sol High for independent numerical review.
Four slots are available; no attempt was made to fill idle slots.

Verified unchanged refs: archive c67b68fdaf7be2049308db7da449f14a25123847;
recovery-04 57cb1fbf75a54a0fa75e70386922ad9cfecf06b1;
bank-04 fe3392b9f563bd66f67b31ca51385ffb100f3780;
product-05 7a8c465e3fd1410e2b59bab4c40d48a61513bd3e;
develop/origin-develop 9a62e431d3101799e6179a6d0cf3b37440062e23.
Exact-03 remains 5ed327ade33b31ecdb5e3b4b4111c55f321991fd and continuation-A
4e1efc947c5aa713a36c81d650a35ca71e60d2e1. No push, PR, reset, fetch,
dependency installation, remote execution or protected-branch update.

Build preflight: RUN_COMPARE_06_PREFLIGHT.md. Release GCC 14.2, CMake 3.31.6,
Ninja 1.12.1, local HDF5 1.14.5; serial build; experimental enabled only in the
build, default remains OFF. WSL Git cannot interpret the Windows worktree
gitdir, so embedded version metadata is blank/0.0.0; verified Windows Git
source SHAs and file/binary hashes, not embedded version text, bind the build.
Recovered libopenmc SHA256:
630f71801795b18f0fe858ee6d557ce9dec905f3adc6b5fdec25d6137730faa4.
Exact libopenmc SHA256:
451b21536d4178a81c4ec5c9a44f6e04eac194c58c87a639d643441ff2717d48.
Preserved swept source SHA256:
93b4723fd1f18dea0f6db6a006eccbf636ef06d5519c2ed2a7bb78008d53b51c.
The H1 file FENDL-3.1d_H1.h5 is 85376 bytes, SHA256
a28ee9ad6fc9e5ce1e6d0c88acb93378c2054ab65f55b9a52bd42abee4d00083.
Native ZTorus sentinel binary SHA256:
9ec5ecf208507fd0a39e87e79a3cc36cbed236ed9c2ea63361e1b5554d34486d;
run with --banks 10000 (640000 calls over 64 fixed rays). It is a repeated-bank
absolute-cost sentinel, NOT the primary cold-query comparison bank.

Compact evidence is in product06/*/receipt.json and reduction.json. Raw XML,
stdout/stderr, statepoints, summaries and track outputs remain in seed-* run
folders, deliberately ignored from Git, not deleted. The old-control build
receipt preserves compile/link commands and object/library SHA256s. Build
logs and binaries remain in build/native-recovered-06 and native-old-control-06.
No classification/normal microbenchmarks, allocation counts, query counters,
P95/P99 or fallback instrumentation were collected in this transport-only
turn; none is implied by these rates.

## Exact restart commands

Use existing local WSL distribution OpenMC-Dev-D and existing runtimes; no
installation is needed. These Bash commands refuse an existing output folder.
Run serially, without a competing build or numerical workload:

```bash
R=/mnt/c/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS/stellarcsg-run-compare-06
W=/mnt/c/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS
E=/mnt/d/codex-verification/stellarcsg-20260913-03/native
P=/opt/openmc-venv/bin/python
Q=$R/dev/stellarcsg/qualification
M=$W/stellarcsg-product-05/dev/stellarcsg/reports/product05/model-02
O=$R/build/native-old-control-06
F=$R/build/native-recovered-06
COMMON=(--model "$M" --lane "old=$O/openmc" --library "old=$O/libopenmc.so"
  --lane "recovered=$F/bin/openmc" --library "recovered=$F/lib/libopenmc.so")
EXACT=(--lane "exact=$E/bin/openmc" --library "exact=$E/lib/libopenmc.so")
$P "$Q/product06_compare_transport.py" "${COMMON[@]}" "${EXACT[@]}" \
  --output "$R/dev/stellarcsg/reports/product06/rerun-debug-64" \
  --histories 64 --seeds 17 19 23 --timeout 120 --debug
$P "$Q/product06_compare_transport.py" "${COMMON[@]}" "${EXACT[@]}" \
  --output "$R/dev/stellarcsg/reports/product06/rerun-transport-256" \
  --histories 256 --seeds 17 19 23 --timeout 120
$P "$Q/product06_compare_transport.py" "${COMMON[@]}" --baseline-lane old \
  --output "$R/dev/stellarcsg/reports/product06/rerun-floating-8192" \
  --histories 8192 --seeds 17 19 23 --timeout 120
$P "$Q/product06_compare_transport.py" "${COMMON[@]}" "${EXACT[@]}" \
  --output "$R/dev/stellarcsg/reports/product06/rerun-tracks-64" \
  --histories 64 --seeds 19 --timeout 120 --debug --track
$P "$Q/product06_compare_tracks.py" \
  --campaign "$R/dev/stellarcsg/reports/product06/rerun-tracks-64" \
  --output "$R/dev/stellarcsg/reports/product06/rerun-tracks-64/tracks-comparison.json"
```

Inspect each receipt's completion, clean_navigation, comparison status and
differences; the runner's exit 0 alone is NOT a successful numerical verdict.
The 8192 campaign intentionally has no exact lane and must not be represented
as exact-validated coverage. Next engineering work remains nearest-root/contact
repair, source-period symmetry and fidelity/clearance qualification; neither
new mathematical methods nor mesh comparison were run in this turn.

All build, transport, track, reduction and test commands have ended. Final
exact-name process checks found no openmc, cc1plus or ninja process. The
recovered library hash was rechecked unchanged after old-control relinking
and every campaign. Raw negative and positive results are retained.
