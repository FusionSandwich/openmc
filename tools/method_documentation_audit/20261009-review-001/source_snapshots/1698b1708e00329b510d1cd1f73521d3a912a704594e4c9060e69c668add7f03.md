# StellarCSG continuation — 2026-09-13

Coordinator record. This is a partial implementation/qualification campaign, not
a declaration of production readiness. The user's explicit request governs;
the Downloads handoff is reference material. No remote compute is authorized
or used. Four total agent slots are available: coordinator plus three workers.

## Provenance and preservation

Repository origin: https://github.com/FusionSandwich/openmc.git. Git common
directory: `C:/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS/openmc-stellarcsg/.git`.
The outer `StellarCGS` directory is a separate unborn repository, not this fork.
Default `develop`: `9a62e431d3101799e6179a6d0cf3b37440062e23`.

All six original worktrees were clean, with no upstream divergence. `ls-remote
--symref origin HEAD 'refs/heads/*stellarcsg*' refs/heads/develop` confirmed live
remote tips. A bounded `fetch --no-tags` of A/B/neutral/composite archive found
the same tips. Baseline is an ancestor of all three continuation bases.

| Role | Original worktree | Original branch suffix after `codex/` | Full starting SHA |
|---|---|---|---|
| Baseline | openmc-stellarcsg-composite | stellarcsg-composite-blanket-interoperability-20260901 | 3041a938c3fb0bc349654f37b0b3ebcd3cd5a9bb |
| Neutral | stellarcsg-benchmark-arena | stellarcsg-ab-benchmark-20260901 | 7f41b6bf6c41ef13b843200669cc98e4329ef7b9 |
| A | stellarcsg-track-a | stellarcsg-legacy-v2-20260901 | 6ee8f74a358c5dc3b8f1e10ff93b079eb3f1e30c |
| B | stellarcsg-track-b | stellarcsg-bezier-hybrid-v2-20260901 | 68ab1c3054645e2f49586de3729fa2081e19eb20 |
| Foundation, preserved | openmc-stellarcsg | stellarcsg-native-csg-foundation-20260828 | 5faf87421d5d2066278c7ae02e38138fc22ec894 |
| Torus, preserved | openmc-stellarcsg-torus-class | stellarcsg-torus-class-fastpath-20260901 | c0290b257e879d16762b072e0b6ee3e43a519e8e |

Expected composite archive exists as `origin/archive/stellarcsg-composite-3041a938-20260901`
at the baseline SHA. Qualified archive remains
`c67b68fdaf7be2049308db7da449f14a25123847`; torus archive remains the torus SHA.
The protected-ref snapshot is retained outside Git in the raw evidence directory.

Additive worktrees `stellarcsg-cont-{a,b,neutral}` use branches
`JS/stellarcsg-{a,b,neutral}-20260913-01a09` from the respective exact bases.
No original branch, archive, worktree, or output is overwritten. No PR or merge.

## Host and execution contract

Raw evidence: `D:/codex-verification/stellarcsg-20260913-01a09/`.
`host-preflight.json` records Windows RAM/drives/processes, toolchains,
environments, caches, existing checkouts, zero-download acquisition plan and
rollback. Host: Windows 11, i9-10850K, 10 physical/20 logical cores, 31.91 GiB
RAM; initial available approximately 11.1 GiB; C: approximately 64.1 GiB and
D: approximately 98.0 GiB free. User browser/desktop/OneDrive processes remain
untouched. Docker daemon stopped. Existing `OpenMC-Dev-D` WSL2 is available.

Explicit tools: `/usr/bin/g++` 14.2.0, `/usr/bin/cmake` 3.31.6,
`/usr/bin/ninja`, `/opt/openmc-venv/bin/python` 3.13.5. Python runtime already
has numpy/scipy/h5py/pytest/matplotlib. Its default editable OpenMC points to an
unrelated HPGe project; every test must override PYTHONPATH with the selected
continuation root and `dev/stellarcsg/python`. Never use its embedded version
as source identity. WSL source paths map the same Windows files under `/mnt/c/`;
raw builds/logs map D: under `/mnt/d/`. Windows Git controls worktree metadata.

At most two aggregate compiler processes. Tests/oracles use one thread each; no
competing task jobs ran during the isolated profile slot.
No accepted performance measurements while this task builds/tests. No accepted
timing claim from diagnostic or instrumented runs. Experimental OpenMC remains
OFF by default. No package installation, upgrade, download, or SSH occurred.

## Ownership and interfaces

| Agent | Exclusive files / role | Constraints |
|---|---|---|
| Coordinator | This record, shared CMake/headers, Track A C++ implementation and integration | Owns Git integration and scheduling |
| numerical_review | New neutral `tests/test_swept_adversarial.cpp`, optional new independent oracle script | Never owns production algorithm; independent review |
| track_b_assessment | B coil compiler/tests, root Python surface/geometry API/tests, independent B swept seed repair/tests | No A production patch access; numerical reviewer remains independent |
| neutral_audit | Neutral harness, matching contract/schema, harness tests | Shared harness only; no production algorithm transfer |

All assignments use full verified SHAs above. Shared neutral test/harness
changes may be synchronized byte-for-byte; production algorithm commits must
remain within each lane before comparison. Raw logs are outside conversations.

## Implementation and independent review

This checkpoint is **partial implementation, not final qualification**. Track B's
anchor differs from baseline only in five harness/evidence files; no distinct
Bezier production candidate was present. Both lanes retain smooth radial
bicubic plasma patches and finite cubic swept coils. Root
`src/surface_*_spline.cpp` wrappers are authoritative; adapter copies are stale.

Track A commit `722c305a1ee41a5b89da8056260e73925aa95379` repairs proxy-entry
seeding: add the admissible span-entry seed, permit zero/minimum starts, and
remove pruning based on seed guesses rather than admissible interval bounds.
It also prevents double-counting exact dispatch distance/evaluate/normal calls.
Tests retain independently constructed planar and nonplanar near entries and
non-unit directions. Exact-torus geometry dispatch and default OFF option remain.

Track B commits:
- `6dbd64275486e1dfcb5b7ca1623d53746067b9bc`: finite coefficient/input gates,
  section and frame validation, exact rigid transforms of finite circular or
  elliptical coil coefficients, parent hash provenance, unique collection IDs.
- `338b57d764ba1356b7920607f6147838724796ad`: collection Python/XML/HDF5
  round trips, collection bounds, payload-aware equality and redundant-surface
  elimination. Four original equality/merging failures are retained.
- `81211f7baed824b4745954cec006ff320532af22`: independently authored
  inside-capsule admissible-start seed, preserving all original proxy slots.
  Tests include transforms, scaled rays, inside starts, and coincident exits.

B's numerical repair was designed from neutral failing geometry, without A
production commits. Both received independent numerical review: ACCEPT as
scoped repairs, not as nearest-hit completeness proofs. B retains unsafe
existing seed pruning and exact-dispatch counter duplication. No new plasma
accelerator was implemented; plasma work here is payload identity protection,
native integration checks, and measured profiling. No triangle mesh replaces
the authoritative smooth surface.

Neutral commit `7b90c498fd7f1bbec8afc2bd504b04e7a0895bce` implements contract v2:
shared physical inputs/settings versus per-method binary/payload hashes,
pre/post-attempt drift checks, identical H5M requirement for DAGMC/Double Down,
durable attempted-run journals, invalid-run retention, bounded timeouts, and
complete-pair bootstrap requirements. User clarified coil and 48-coil >=0.50
denominators as matched fine Double Down/Embree throughput. The separate
outperform-Embree requirement still applies. Other ambiguous denominators remain
unresolved. No transport performance gate is automatically certified by harness.

Neutral fixtures/oracle/profile/plot source commit
`9612765efc75d9c640880ed934ba7dc6b911442d` and plot commit
`a867a951923d66c64886e7307e84f2368c17d4d9` were synchronized to both lanes.
Contract/schema were absent in A and B anchors; modify/delete cherry-pick
conflicts were resolved by adding the complete incoming neutral documents.
Canonical shared Git blobs match. Working-file LF normalization is local and
per-file; no global Git settings changed. See shared-interface-hashes receipts.

The derived counter-coverage correction is neutral commit
`10df232b57d8ecbcc15065db1245e9c8f726f0bc`; raw snapshots and images are unchanged.
Finishing implementation tips (including synchronized neutral evidence):

| Role | Worktree | Branch | Full tip | Dirty state before push |
|---|---|---|---|---|
| A | stellarcsg-cont-a | JS/stellarcsg-a-20260913-01a09 | 4e1efc947c5aa713a36c81d650a35ca71e60d2e1 | clean |
| B | stellarcsg-cont-b | JS/stellarcsg-b-20260913-01a09 | 4774434f10ab922411a0b3eefc243d07ea4adb17 | clean |
| Neutral | stellarcsg-cont-neutral | JS/stellarcsg-neutral-20260913-01a09 | 10df232b57d8ecbcc15065db1245e9c8f726f0bc plus this record commit | this new record only |

## Reproductions and unresolved numerical limits

Two independent 64-control cardinal-seam constructions establish an admissible
surface intersection at 0.002 cm, whereas baseline returned approximately
0.502 cm. One is planar; one has z=0.4 sin(3 theta). This proof of a missed
earlier hit does not reuse production classification. A and B now return
approximately 0.002 cm. Original captures and negative test logs are retained.

The independent floating-point polynomial oracle reconstructs cubic spans from
raw controls and enumerates polynomial roots without the production BVH or
projection. Degenerate, ill-conditioned, near-real, or unsuccessfully corrected
candidates are BLOCKED, not discarded. This is sampled evidence, not a
certified complete root isolator.

| Capture | PASS | FAIL | BLOCKED | NOT_RUN |
|---|---:|---:|---:|---:|
| Strict baseline polynomial-05 | 273 | 88 | 23 | 0 |
| A repair polynomial-01 | 361 | 0 | 23 | 0 |
| B repair polynomial-01 | 361 | 0 | 23 | 0 |

87 baseline failures belong to explicitly unqualified high-curvature shape 2;
one belongs to smooth nonplanar shape 1. Planar direct-hit failure is separately
proven even though its polynomial result is BLOCKED by an uncertain candidate.
All 1,536 sampled projection upper-bound checks pass, which does not establish
global projection completeness. Both repaired C++ adversarial runs still exit
with two exact-tangent transform discrepancies (~1.35e-7 versus a strict 2e-8
metamorphic threshold). They remain unresolved, not silently reclassified PASS.
Earlier less strict oracle outputs and a wrong-default-WSL attempt are retained;
only explicit OpenMC-Dev-D strict results above support this checkpoint.

Static remaining defects/limits:
- Unresolved-span fallback runs only when no finite best hit exists, stops on
  first success, uses eight sign-change segments, retains only seeded spans,
  and can truncate its 64-entry unresolved list. Nearest-hit completeness FAIL.
- The 64-entry traversal-stack exhaustion concern was not reproduced; a median
  uint32 BVH has depth about 32. Do not equate it with unresolved-list truncation.
- Local projection is not globally certified; reference distance shares its
  classification, so it cannot serve as an independent oracle.
- B sample-based frame checks are not self-intersection/clearance proofs.
  Finite rectangular winding packs, broad chart folds, and twist closure
  qualification remain unsupported/unqualified.
- Shared OpenMC coil union acceleration still loses individual coil hit/cell/
  material/tally identity. Collection serialization does not fix that.
- OpenMC surface rotate/translate APIs remain unimplemented; compiler rigid
  coefficient transforms are a distinct, tested capability.
- C++ spline arrays transitively reject nonfinite values. Remaining static
  concerns include positive-infinite scalar metadata, independently read HDF5
  attributes versus canonical metadata, non-SHA IDs bypassing digest checks,
  and XML collection integer-range validation. No failing history is claimed.

## Tests, native binding, and exact replay commands

Use explicit Windows entry point
`C:/Windows/System32/wsl.exe -d OpenMC-Dev-D --exec /bin/bash -lc`.
Inside it define:
```bash
ROOT=/mnt/c/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS
RAW=/mnt/d/codex-verification/stellarcsg-20260913-01a09
A="$ROOT/stellarcsg-cont-a"
B="$ROOT/stellarcsg-cont-b"
N="$ROOT/stellarcsg-cont-neutral"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
```
Use new output filenames for reruns; oracle and native smoke reject overwrite.

| Executed validation | Result | Retained log |
|---|---|---|
| A baseline Release HDF5 OFF CTest | 2 passed | a-baseline CTest output |
| A baseline Python | 21 passed | a-baseline-python.log |
| A repaired counters ON CTest | 2 passed | a-profile-ctest-03.log |
| A HDF5-enabled CTest | 2 passed | a-hdf5-probe CTest log |
| A final Python | 38 passed | a-final-dev-python-01.log |
| B repaired Release HDF5 ON CTest | 2 passed | b-repair-ctest-01.log |
| B finite coil Python before harness sync | 52 passed | b-coil-tests-01.log |
| B final Python | 69 passed | b-final-dev-python-01.log |
| B root OpenMC API tests | 83 passed, 1 deselected, 5 warnings | b-payload-api-tests-03.log |
| Neutral final harness suite | 38 passed | neutral-python-02.log |
| Native B full then incremental build | 142/142 then 3/3 completed | b-openmc-build-01/02.log |
| Actual native init and summary round trip | PASS, zero histories | b-native-smoke/run-02.log |

Standalone build pattern (A counters directory adds
`-DSTELLARCSG_ENABLE_PERFORMANCE_COUNTERS=ON`):
```bash
/usr/bin/cmake -S "$B/dev/stellarcsg" -B "$RAW/b-repair" -G Ninja \
  -DCMAKE_CXX_COMPILER=/usr/bin/g++ -DCMAKE_BUILD_TYPE=Release \
  -DSTELLARCSG_ENABLE_HDF5=ON -DSTELLARCSG_BUILD_TOOLS=OFF \
  -DSTELLARCSG_BUILD_BENCHMARKS=OFF -DSTELLARCSG_BUILD_CAMPAIGNS=OFF
/usr/bin/cmake --build "$RAW/b-repair" --parallel 1
/usr/bin/ctest --test-dir "$RAW/b-repair" --output-on-failure
PYTHONPATH="$A/dev/stellarcsg/python:$A" /opt/openmc-venv/bin/python \
  -m pytest -q -p no:cacheprovider "$A/dev/stellarcsg/python/tests"
PYTHONPATH="$B/dev/stellarcsg/python:$B" /opt/openmc-venv/bin/python \
  -m pytest -q -p no:cacheprovider "$B/dev/stellarcsg/python/tests"
PYTHONPATH="$B/dev/stellarcsg/python:$B" /opt/openmc-venv/bin/python \
  -m pytest -q "$B/tests/unit_tests/test_stellarcsg_surface.py" \
  "$B/tests/unit_tests/test_surface.py" "$B/tests/unit_tests/test_geometry.py" \
  -k 'not test_volume'
```
The deselected volume test requires a separate transport calculation; this is
not a claim that the entire OpenMC test suite passes.

Native CMake used explicit C/C++ compilers, Release, Ninja,
`GIT_SUBMODULE=OFF OPENMC_USE_MPI=OFF OPENMC_USE_OPENMP=ON
OPENMC_USE_DAGMC=OFF OPENMC_BUILD_TESTS=OFF
OPENMC_ENABLE_EXPERIMENTAL_STELLARCSG=ON`.
Existing exact local fmt/pugixml/Catch2 gitlinks were exported to empty vendor
directories; zero acquisition bytes and no dependency upgrades.
The Linux build cannot interpret Windows worktree Git pointers and reports
version 0.0.0; actual source/binary hashes are authoritative.
Final native library SHA256:
`6bfa57724907e264c3c5c353ff408aa11a5cc66ea9b3b7050b80172377b2d2f0`.
Executable SHA256:
`874bd283c398163fbe901d160462be50870b50180b1b5a24e8f3c139cf73595a`.
The executable dynamically links the changed library; both identities matter.
Linked-library evidence and older binary hashes remain in raw receipts.

The actual init smoke uses helical plasma and two rigidly transformed nonplanar
finite elliptical coils, with conservative AABB gaps 14.9123, 14.5544, and
53.8902 cm. It writes and rereads real native summary.h5 and reexports XML.
All cells are void, zero histories executed, no blanket. The unused synthetic
zero-collision MG entry exists solely for initialization, not production
physics or materialized qualification. Reproduce with:
```bash
PYTHONPATH="$B/dev/stellarcsg/python:$B" /opt/openmc-venv/bin/python \
  "$RAW/b-native-smoke/initialize_summary.py" "$RAW/b-native-smoke/run-03"
```

Independent common fixture and oracle:
```bash
/usr/bin/g++ -std=c++17 -O2 -I"$N/dev/stellarcsg/include" \
  "$N/dev/stellarcsg/tests/test_swept_adversarial.cpp" \
  "$RAW/b-repair/libstellarcsg_reference.a" -o "$RAW/b-repair-adversarial-02"
"$RAW/b-repair-adversarial-02" > "$RAW/b-repair-adversarial-02.jsonl" \
  2> "$RAW/b-repair-adversarial-02.log"
/opt/openmc-venv/bin/python \
  "$N/dev/stellarcsg/qualification/swept_adversarial_oracle.py" \
  "$RAW/b-repair-adversarial-02.jsonl" --output "$RAW/b-repair-polynomial-02.json"
```
Expected current fixture exit is nonzero for the retained tangent checks;
oracle exit 2 means BLOCKED cases remain. Never count either as a complete pass.

## Measured profile and plots

One task-exclusive profile slot, CPU affinity 0, one thread, warmup plus seven
retained repetitions, instrumented A repair. No builds/tests/oracles competed;
ordinary desktop activity was uncontrollable. Failed initial /usr/bin/time
attempt remains recorded; existing Python resource supplied peak RSS instead.
No accepted transport timing or speed ratio was produced.

512 fixed rays per finite-coil/helical-plasma case, 100 repeats per phase:
51,200 evaluate, normal, and distance calls each. Median nanoseconds/query:

| Case | Evaluate | Normal | Distance |
|---|---:|---:|---:|
| Nonplanar finite coil | 708.613 | 831.145 | 2784.930 |
| Helical plasma | 268.025 | 281.025 | 21303.135 |

Coil distance averages: 5.396 nodes, 1.928 spans, 6.158 seeds, 27.609 Newton
iterations and 2.301 failed Newton attempts/query. Plasma distance averages:
10.734 nodes, 3.717 patches, 2.398 seeds, 51.648 Newton iterations, 13.984
failed attempts, 52.213 evaluate calls, 57.807 subdivision nodes and 1.398
subdivision calls/query. Repeated local correction and subdivision dominate
this diagnostic workload. Peak child RSS 17,488 KiB. This is not a full OpenMC
profile, before/after speed improvement, A/B comparison, or instrumentation
overhead qualification.

Missing counter coverage is unavailable/null, not zero. In particular,
evaluate/normal local searches do not increment all candidate/solve counters;
their raw zeros do not establish absence of work. Histories/crossings, cache
behavior, geometry CPU fraction, multithread aggregation and minimally
instrumented transport timing remain unmeasured.

Actual plots and numerical source data:
- [Query profile](../plots/dual_track/continuation_20260913/query_profile.png)
- [Root repair](../plots/dual_track/continuation_20260913/root_repair.png)
- [Derived measurements](../plots/dual_track/continuation_20260913/measurements.json)

Figures use retained data, with IQR and bootstrap median uncertainty in derived
records. Root figure describes A; B subsequently matches its strict state
counts but was not substituted into that historic figure. No invented
illustrative performance plot. All raw repetitions, failed launches, earlier
oracle outputs and original negative seeds remain immutable.

## Gate matrix and recommendation

| Gate | State | Evidence / next dependency |
|---|---|---|
| Standalone regression and selected API checks | PASS | Counts above, bounded scope |
| Proven 0.002 cm near-entry repairs A and B | PASS | Independent construction and permanent regressions |
| General swept nearest-hit completeness | FAIL | Remaining candidate/fallback invariant violations |
| Strict independent oracle full corpus | BLOCKED | 23 uncertain cases; two tangent metamorphisms unresolved |
| Native plasma + finite elliptical collection summary | PASS | Actual init, zero transport histories |
| Shared acceleration preserving individual coil attribution | FAIL | Union discards hit identity |
| Exact periodic and planar >=0.95 ZTorus | NOT_RUN | Historical results preserved, no fresh transport repetitions |
| Forced-general >=0.25 and aspiration >=0.8 | BLOCKED | Correctness and denominator resolution |
| Shaped axisymmetric >=0.50 | BLOCKED | Denominator/geometry qualification |
| Helical >=0.25 and matched Embree advantage | BLOCKED | Correctness, denominator and matched dependency binding |
| WISTELL-D plasma accuracy/closure and Embree advantage | NOT_RUN | No fresh matched geometry or timings |
| Nonplanar coil and 48-coil >=0.50 fine Embree | BLOCKED | Correctness, identity, matching and verified Embree build |
| 1/12/48 set scaling | NOT_RUN | No eligible common set replay/transport campaign |
| Matched A/B/DAGMC/Double Down timing | NOT_RUN | No eligible matched H5M ladder or bound Embree executable |
| Positive-clearance materialized S4 tallies | NOT_RUN | No verified physics campaign; prerequisite geometry gates |
| Near-torus and substantial (proposed 2x) Embree objective | NOT_RUN | Not demonstrated |

Retain A and B as independent comparators. A has the broader seed-pruning
repair and validated accounting; B has useful finite-coil validation/transforms
and native payload identity integration. Neither general kernel is qualified
for production nearest transport. Existing plasma kernel is a measurable
reference, not a demonstrated winning Bezier accelerator. No evidence supports
selecting a plasma or coil performance winner yet.

## Preservation, finishing identity, and restart

Original branches/default/archive tips are unchanged in
protected-refs-after.json and remote-refs-after.txt. Original worktree status is
recorded separately. Only new JS continuation branches may be pushed; no PR,
force push, merge, or remote compute. Final full tip/dirty/upstream identities
and push receipts are in finish-map.json and push-*.log under the raw root;
the coordinator record commit itself is identified there to avoid self-reference.

No owned build, test, oracle, profile or native process remains at checkpoint.
Agents are idle. No remote jobs exist. No background automation was created.
clang-format 18 was unavailable (19 present); no formatter version substitution
or dependency acquisition occurred. Git diff whitespace checks passed.

Next executable work:
1. Resolve remaining BLOCKED roots independently with interval/arbitrary-
   precision isolation, retaining uncertainty. Repair each lane's earlier-hit
   candidate invariant and explicit unresolved status before transport.
2. Add per-coil identity-preserving shared navigation and missing root OpenMC
   transforms; validate finite geometry, closure and clearance.
3. Establish a genuinely distinct B plasma/coil accelerator only after these
   correctness regressions, using measured correction/subdivision cost.
4. Verify existing DAGMC/Double Down dependencies and identical H5M tolerance
   ladder without downloads; unavailable resources block only matching.
5. Resolve remaining contract denominators, freeze cases, then run S1-S3
   transport with exclusive host slot, seven minimum / 11-21 decisive repeats,
   balanced order and native ZTorus sentinel. S4 requires verified physics.

Fresh reruns use new raw output names and refresh live host/resource preflight
before build/environment operations. No proprietary raw geometry was committed;
synthetic controls are retained. Catalog input redistribution permissions were
not requalified and must be checked before publishing supplied geometry.
