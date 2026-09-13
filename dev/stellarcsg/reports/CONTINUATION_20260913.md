# StellarCSG continuation — 2026-09-13

## Follow-up 02: implemented and executed, not final qualification

This section supersedes the gate/status claims in the preserved first-session
record below. Raw evidence is additive under
`D:/codex-verification/stellarcsg-20260913-02/` (`RAW2` below); the older
`stellarcsg-20260913-01a09` directory remains unchanged. The user's follow-up
governs; historical handoffs are references, not new execution authority.

### Verified continuation and ownership

Root directory: `C:/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS`.
Origin remains `https://github.com/FusionSandwich/openmc.git`; the outer unborn
repository was not used. Four actual slots were used: coordinator/integrator,
independent numerical reviewer, coil implementer, and plasma implementer.
Freed slots were reused for native/cache review, attribution checks, and
matched-runtime preparation. No claim of 8–12 available slots is made.
After the user's model-cost clarification, a Luna worker checked literal
receipt/report consistency; Astra retained orchestration and scientific review.

| Role | Worktree | Branch | Full source/tip SHA |
|---|---|---|---|
| Frozen A control | stellarcsg-cont-a | JS/stellarcsg-a-20260913-01a09 | 4e1efc947c5aa713a36c81d650a35ca71e60d2e1 |
| Preserved B start | stellarcsg-cont-b | JS/stellarcsg-b-20260913-01a09 | 4774434f10ab922411a0b3eefc243d07ea4adb17 |
| Preserved neutral start | stellarcsg-cont-neutral | JS/stellarcsg-neutral-20260913-01a09 | 6949794947d06a37e4d9ea30b04138b2c6823132 |
| Integrated implementation | stellarcsg-next-b | JS/stellarcsg-transport-20260913-02 | 5614f9cacfd9bb1acba4cf6683d9b1da16c06067 |
| Independent coil lane | stellarcsg-next-coil | JS/stellarcsg-coil-20260913-02 | d57c1cc302bd34c83e785299d7a12c88804b2665 |
| Plasma experiment lane | stellarcsg-next-plasma | JS/stellarcsg-plasma-20260913-02 | 221faceda4972f2718ed3cba6545b5064e389eb2 |
| Neutral evidence before this record commit | stellarcsg-next-neutral | JS/stellarcsg-neutral-20260913-02 | 287448682bb24d2a91643c549d60f85e45d85619 |

All new lanes descend from the verified B/neutral starts; no old branch was
advanced. Final record-commit SHA, clean/dirty/upstream map and push results
are in `RAW2/finish-map.json` and `push-*.log`, avoiding a self-referential SHA.
All 14 protected references matched before/after audit, including baseline
`3041a938c3fb0bc349654f37b0b3ebcd3cd5a9bb`, its archive and `develop`.
The original three continuation worktrees were clean. Final checks are retained
separately in `protected-refs-final.json` and `remote-refs-final.txt`.

Coordinator owned shared headers/CMake, actual root OpenMC wrappers, Python
surface API, neutral synchronization, Git operations and execution. Workers
owned separate CPP/test files in separate worktrees/build directories. The
numerical reviewer did not own the production algorithm. A remains a frozen
legacy control with its known remaining candidate-completeness limits; the B
repair was not relabeled as A. Common neutral fixtures, harness and contract
were synchronized after the isolated plasma ablation (`neutral-sync-02.json`).

### Nearest-hit repair and independent disposition

Coil production commit: `935a28e8367b2c9b8d029cd3ca9fe96a92532cfe`;
integrated as `da7a5417f1ca697c439bb5c5892058c48b29a7eb`.
The supported general path is a constant-radius circular tube around a regular
periodic cubic centerline, subject to explicit sufficient curvature/separation
certificates and a 512-control resource bound. The authoritative controls are
the exact input binary64 B-spline coefficients, not rounded power coefficients
or a triangulation. Elliptical/frame-dependent and variable-radius general
queries explicitly reject unsupported operation. Certificate failure is not a
proof of invalid geometry or self-intersection.

`compiled_swept_surface.cpp` now uses exact rational polynomial construction,
conservative interval exclusions and local square-free Sturm isolation for
all candidate span resultants, including exceptional/gcd cases. It compares
root enclosures before accepting the nearest hit. Seed-only pruning, fixed
eight-sample completeness, first-success fallback and silent unresolved-list
truncation no longer determine this path. Exact stationary-point projection
and conservative public bounds were also repaired. Exhaustion, ambiguous
associations and unsupported states throw; the active wrapper converts them
to explicit fatal diagnostics, never ordinary infinity/no-hit. No independent
Python broad oracle runs in the production hot path. GMP was already installed;
no software was acquired. Main-build GMP linkage is conditional on the
experimental option, which remains OFF by default.

The reproduced rounded crossing/coincidence failure led to a bounded,
unique-root association window: negative candidates are retained; an enclosure
must lie wholly inside the window; missing, competing or straddling associations
fail explicitly. This is a restricted query contract, not universal proof for
arbitrary rounded tangent starts. Universal coincidence remains BLOCKED.
The old median uint32 BVH depth issue was not reproduced; depth/capacity checks
were added without presenting it as a discovered failure. Auto exact-torus
dispatch remains preserved; its historical near-circle recognition tolerance
is not an exact coefficient-identity guarantee. Strict torus tests force general.

| Independent check | Result |
|---|---|
| All original 384 rays, unchanged input values | 256 PASS / 0 FAIL / 128 BLOCKED |
| Original 23 ambiguous cases, exact independent isolation | 23 PASS |
| Those 23 versus production at unchanged 2e-8 cm threshold | 20 PASS / 0 FAIL / 3 BLOCKED |
| Original two rigid nominal tangencies | 2 PASS |
| Exact oracle arithmetic controls | 8 PASS |
| Input replay identity | 387 records / 2,739 binary64 values identical |

All 128 blocked rays are stress shape 2, whose sufficient embedded-tube
separation certificate fails. This neither establishes self-intersection nor
an engineering-device failure probability. Its formerly ambiguous indices
7, 8 and 9 remain BLOCKED in production comparison although independent
algebraic isolation succeeds. Every ID and reason is retained in
`exact-coil-replay-01.jsonl` and `exact-coil-oracle23-01.json`.
The exact Fraction oracle does not reuse production pruning/classification;
it handles coefficient zeros without float trimming, degeneracies, near-real
recovery and exact discriminants. Earlier failures remain in
`exact-oracle-blocked23-final-02.json`.

Both nominal tangent distance errors fell from about 1.375e-7 cm to
1.862e-12 cm without loosening 2e-8. Independently reconstructed C++ transformed
inputs match all 396 binary values; geometric perturbation was a few 1e-16 cm,
while old root error dominated. See `exact-coil-rigid-tangencies-01.json` and
the original `exact-rigid-tangencies-01.json`. The independent reviewer accepts
the ordinary supported circular path as implemented/tested, with the limitations
above; this is not global arbitrary-geometry qualification.

### Actual transport and coil identity

Root implementation commits `64b308f1a`, `ac57816288c4012bd1a6d57f63aeeaf87b4df509`
and `223ea7a1c57439ff6141604b72b0ce026846cd5f` introduce collection `member_id`
surfaces backed by one immutable geometry context. Member hits feed distinct
OpenMC cells 101/102 and materials 11/12; parent cell 201 independently measures
the union. Parsed payload arrays, scalar attributes and coil IDs bind context
identity. The dataset suffix must match payload coil_id. Query keys contain
owning context, every ray component, coincidence flag and coincident member.
Only that member receives coincidence semantics. Explicit wrapper error
propagation covers distance, classification and normal queries.

The final cache has 32 distance entries and 32 classification entries per
thread, owns context lifetimes, and publishes only successful results. It
reuses identical numerical queries without approximating nearby rays. It may
retain multiple geometry contexts per thread; broadly distributed-source miss
cost and memory scaling are not qualified. Native controls exercise 40 one-ULP
queries/eviction (48 misses, 112 hits), two threads (96/224), changed contexts,
real hits/classification signs, wrapper lifetimes, and coincidence/member-key
discrimination: 5/5 PASS in `shared-cache-controls-03/receipt.json`.
Classification-cache eviction is statically reviewed, NOT_RUN dynamically.
The earlier three native negative controls also PASS: valid-hash ID permutation
rejected, missing coincidence fatal, and member/lifetime queries. Failed test
launchers caused by Windows Git pointers remain retained separately.

The demonstration has helical plasma and two transformed nonplanar circular
coils of radius 0.25 cm. Conservative AABB gaps are 33.5397532 cm between coils
and 4.5539315/4.5623131 cm from plasma. There is no blanket. Physics is an
explicit synthetic one-group pure absorber (Sigma=0.1/cm), not fusion nuclear
heating/damage validation. Asymmetric source illumination and distinct material
scores test attribution. The explicit bank repeats three deterministic point/
direction source definitions; this cache-friendly verification workload is
not representative throughput qualification.

| Actual run | Completed histories | Evidence directory under RAW2 |
|---|---:|---|
| Checkpoint torus, plasma, one coil, two coils, combined separate-cell controls | 5 x 10,000 | transport-control-*-01 |
| Shared combined before full isolation repair | 10,000 | transport-shared-pre-isolation-01 |
| Exact repaired shared, one-entry cache | 100 | transport-shared-exact-100-01 |
| Exact repaired shared, bounded cache | 100 | transport-shared-cache-100-01 |
| Exact repaired shared, one thread | 10,000 | transport-shared-exact-10000-02 |
| Exact repaired shared, two threads | 10,000 | transport-shared-exact-10000-thread2-01 |
| Exact repaired separate-surface control | 100 | transport-separate-exact-100-01 |
| Native ZTorus timing-host sentinels | 8 x 10,000 | plasma-ablation-01 |

All listed runs returned zero with requested counts in statepoints and no
lost-particle diagnostic. Zero lost is inferred from those checks, not an
independent instrumentation counter. The final 10,000-history runs retained
100 tracks and 204 observed cell transitions each; this is a sample, not total
crossing completeness. Six deterministic native C-API cell/material boundary
checks also pass. One-thread coil fluxes are 0.35563450348552317 and
0.10319611144207044; union flux 0.45883061492759103; closure error
2.55e-15. Two-thread closure is 2.44e-15, with scores differing only at rounding
level. Source-bank SHA256 for both runs is
`4b86725ecc02d547f4fb1ab6feb200aa1183710208607ff3d11bb28a67985b0c`.
Native material bins match the respective cell bins, with nonzero scores for
both coils. Independent comparisons are in `transport-attribution-review-final.json`.

Cold versus cached 100-history source bank, tallies, global tallies and retained
tracks are identical (`preservation-review-01.json`). Cold active time was
76.9323 seconds (~1.30 histories/s); bounded-cache active time 2.1227 seconds.
The final repeated-source 10k runs took 55.9900 active / 56.1618 total seconds
on one thread and 31.9646 / 32.1122 seconds on two. These single-run diagnostic
times are not accepted speed ratios. Exact rational coil work remains a severe
cold-query bottleneck; caching does not establish near-torus performance.
The first 10k launcher failed before execution because a SHA-file argument was
missing; `transport-shared-exact-10000-01.log` is retained. The successful retry
used a literal verified SHA and a new directory. No particle failures were
discarded to obtain the listed PASS diagnostics.

### Implemented plasma ablation and matched comparison blocker

Plasma production commit `1620263e1866e035ca293d270b10a193330dc104` reuses an
unchanged converged parametric sample and removes two redundant evaluations
in a bracket already collapsed to one point. Exhausted iterations still
resample changed parameters. It preserves the authoritative radial spline,
tolerances, traversal and torus specializations; it is not a Cartesian Bezier
fit or a new atlas. The change targets repeated correction cost seen in the
retained profile. The measured counter reduction is 22,152 to 21,200 evaluations
per helical bank (-4.30%), and 8,118 to 7,856 for WISTELL-D (-3.23%).

Four isolated builds (`plasma-{baseline,candidate}-{on,off}`) passed both CTests.
512 distinct ray records (256 each helical/WISTELL-D) are bit-identical across
old/new and counters ON/OFF. Helical has no sampled oracle failures/blocks;
WISTELL-D grazing IDs 144, 150, 156, 180 and 186 remain BLOCKED, unchanged.
The oracle is sampled validation, not nearest-root proof for all plasma rays.

`plasma-ablation-01` retains one warm-up and seven balanced measured repetitions
for eight kernel methods plus the native sentinel: 72 attempted runs, all valid,
144 output hashes, durable start/finish journals and source/library drift checks.
Each kernel run contains 128 banks of 256 frozen rays. CPU affinity 0, one
thread; all other owned builds/tests/oracles were paused for that slot.
Ordinary desktop interference is uncontrolled. The sentinel median is
185,377 histories/s with 9.9% CV; its low first measured run is retained.

| Counters OFF | Baseline ns/query | Changed ns/query | Baseline / changed ratio, paired bootstrap 95% interval |
|---|---:|---:|---|
| Helical | 31942.48 | 30882.13 | 1.0343 [1.0137, 1.0629] |
| WISTELL-D | 18292.82 | 18124.48 | 1.0093 [0.9480, 1.1705] |

ON ratios are 1.0272 [1.0073, 1.0459] and 0.9856 [0.9777, 1.0548].
ON/OFF overhead intervals include 1; apparent negative overhead is timing noise.
Helical shows a modest measured improvement, WISTELL-D is inconclusive. Neither
is an A/B transport or Embree ratio. The older 512-ray profile is a different
bank and must not be used as this ablation's denominator. Raw grazing/slow tails
are retained. [Measured figure](../plots/dual_track/continuation_20260913/plasma_ablation_02.png)
and adjacent JSON are generated from these retained data, not illustrative data.

Today's OpenMC-Dev-D cannot bind DAGMC/MOAB/Double Down/Embree libraries or
pymoab. Docker's daemon pipe is absent and its distro is stopped. Existing
stopped runtime disks and a local Embree source archive were identified, but
do not constitute a linked executable. No large disk/runtime was started under
low host RAM; no install, download, unrelated distro job or remote compute was
performed. The exact blocker is a currently accessible, verified DAGMC/DD
runtime plus an eligible common H5M geometry-error ladder. Identical H5M bytes,
two-sided finite-surface errors, normals/volume/area/seams and accuracy selection
have NOT_RUN for this new model. Old ordinary-DAGMC 5.8886x evidence is not
Double Down evidence and is not imported here. The amended contract now names
native ZTorus as the forced-general denominator; coil/set denominators remain
matched fine Double Down/Embree, with separate >1 advantage requirements.

### Final gate scope, validation and restart

| Gate | State | Scope or blocking issue |
|---|---|---|
| Ordinary supported circular nearest-hit invariant | PASS | Exact candidate/root treatment, retained independent review |
| All retained stress geometry admitted and tracked | BLOCKED | 128 rays fail sufficient geometry certificate |
| Universal native coincidence and elliptical general sections | BLOCKED | Restricted association contract / unsupported section |
| Plasma + finite coils actual shared attribution diagnostic | PASS | Two 10k repaired runs, cell/material/union checks |
| Implemented helical plasma distance improvement | PASS | Fixed-ray ablation; modest effect, sampled correctness |
| WISTELL-D plasma improvement/closure qualification | BLOCKED | Five oracle blocks; performance interval includes no gain |
| Fresh exact >=0.95 / forced-general >=0.25 ZTorus gates | NOT_RUN | No eligible repeated torus-equivalent campaign |
| Coil and 48-coil >=0.50 fine Embree gates | BLOCKED | Bound comparator and matched accuracy ladder absent |
| Near-torus >=0.8 aspiration / proposed >=2x Embree ambition | NOT_RUN | Not achieved; severe cold exact-coil cost |
| Broad 1/12/48 scaling and supplied WISTELL-D finite set | NOT_RUN | No eligible campaign in this follow-up |
| Materialized fusion heating/damage S4 | NOT_RUN | Synthetic MG only; verified physics not supplied here |

Integrated native builds completed 142/142 then incremental builds through
`native-build-05.log`. Integrated standalone CTest: 4/4 PASS in 10.00 s;
selected root Python: 93 PASS, one transport-volume test deselected, five
inherited warnings; development Python after neutral sync: 77 PASS. Earlier
69-test run and all lane tests are retained. No entire OpenMC suite claim.
Independent native negative controls: 3/3 PASS; cache controls: 5/5 PASS.
clang-format 18 was unavailable; no version substitution or dependency upgrade.
Whitespace checks pass. User-wide resource/cache/toolchain review is retained
in preflight/resources receipts. Existing GCC 14.2, CMake 3.31.6, Python 3.13.5,
HDF5 and GMP were reused. Maximum compiler concurrency was two one-thread
processes; most builds used one. All execution was local in OpenMC-Dev-D.

`integration-source-binary-final.json` binds the final source to native build
production commit `223ea7a1c57439ff6141604b72b0ce026846cd5f`: subsequent changes
do not alter compiled production files. Executable SHA256 is
`05d1779730120d8f3f08bee477147d44c0dbc0941137582fa780d57ee82097c1`;
library SHA256 is
`189d72a5161897b84fbb4c9f84f5150eeb134c348d248ad9749f144c576a020e`.
The unchanged executable depends on the changing shared library, so both are
required. Actual ldd, CMake cache, per-source hashes and pre/post transport
binding are retained. Linux embedded version 0.0.0 is not provenance. The
unrelated editable Python installation is never used without explicit path
binding. No new proprietary supplied geometry was committed; synthetic inputs
and derived measurements are redistributable, supplied-input restrictions are
unchanged.

Reproduce from WSL OpenMC-Dev-D with fresh output names. These existing-build
commands require no acquisition; re-review live resources before a rebuild:

```bash
BASE=/mnt/c/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS
B="$BASE/stellarcsg-next-b"
N="$BASE/stellarcsg-next-neutral"
RAW2=/mnt/d/codex-verification/stellarcsg-20260913-02
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$B/dev/stellarcsg/python:$B"
export LD_LIBRARY_PATH="$RAW2/native/lib"
/usr/bin/ctest --test-dir "$RAW2/integration-tests" --output-on-failure
/opt/openmc-venv/bin/python -m pytest -q -p no:cacheprovider "$B/dev/stellarcsg/python/tests"
/opt/openmc-venv/bin/python -m pytest -q -p no:cacheprovider \
  "$B/tests/unit_tests/test_surface.py" "$B/tests/unit_tests/test_stellarcsg_surface.py" \
  "$B/tests/unit_tests/test_geometry.py" "$B/tests/unit_tests/test_stellarcsg_shared_member.py" \
  -k 'not test_volume'
/opt/openmc-venv/bin/python "$B/dev/stellarcsg/qualification/native_transport_smoke.py" \
  --output "$RAW2/transport-shared-exact-10000-restart-01" \
  --executable "$RAW2/native/bin/openmc" --source-root "$B" \
  --source-sha 5614f9cacfd9bb1acba4cf6683d9b1da16c06067 \
  --case combined --histories 10000 --threads 1 --shared --timeout 180
```

The exact ablation invocation is `plasma-ablation-command-01.json`; change its
output directory, refresh the host/resource snapshot and obtain an exclusive
owned timing slot before replay. Exact oracle/replay compile flags and all
hashes are in `exact-coil-replay-provenance-01.json`; 384-case replay correctly
returns nonzero while BLOCKED geometries remain. Retain that status.

Recommended continuation: use the improved existing radial plasma kernel for
further measured work. Keep the reviewed circular algebraic coil path as a
correctness reference and restricted diagnostic implementation, not a fast
production recommendation. Next numerical work is a conditioning-aware native
crossing receipt/association contract and certified bounded fast local solves
that avoid repeated exact rational cost. Next comparison work is to bind an
already-local DAGMC/DD runtime under sufficient resources and prepare the
frozen finite-surface H5M error ladder; this alone blocks matched timing.
Do not broaden to catalog/48-coil production first. No background completion
is promised. Final process and agent state is recorded in `finish-map.json`;
all owned work is collected before returning.

## Preserved first-session record (historical, superseded above)

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
