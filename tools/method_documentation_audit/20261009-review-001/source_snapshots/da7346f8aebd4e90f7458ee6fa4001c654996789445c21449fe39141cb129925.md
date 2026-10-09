# StellarCSG exact-control offset continuation

## State and ownership

Owner: this chat, isolated branch `JS/stellarcsg-astra-kernel-20260926`.
Draft PR: https://github.com/FusionSandwich/openmc/pull/5.
Pinned base: `63359cb83d36b419a7e9ba60c45f867073703c21`.
Baseline source/evidence commits: `3f8703db2`, `c4e72753a`.
The PR's subsequent acceleration commit carries final build14 source/evidence.
Do not modify the original checkpoint branch/worktree or PR3.

Workspace:
`C:\Users\joshu\OneDrive\Documents\ChatGPT\StellarCGS\stellarcsg-astra-kernel-20260926`.
Local WSL distribution: `OpenMC-Dev-D`; corresponding /mnt/c workspace.
No job, compiler, bank replay, verifier or scheduled monitor is intentionally
left running by this work.

## Accepted milestones and decisive identities

- Explicit changed geometry: constant circular or admitted xy-planar elliptical
  exact-control offset solid; legacy default preserved.
- Native surface plus Region entry/exit, normal/sense/containment smoke passes.
- Both build14 modes: 69 hits, 91 no-hits, zero unresolved, all 160 independent
  exact scalar certificates at 1e-11 cm.
- Three clean A/B pairs show 4.05x lower summed distance-query time enabled;
  no native-comparator/80% or particle-transport claim.
- `RESULTS.md` is the human-readable result and limitation record.
- `build-receipt-14.json` SHA-256:
  `376e0f5d4420db086b07b719155b52148af05a5b39892f04735ccfc13e8d83d8`.
- `final-acceptance.json` SHA-256:
  `8210d88c008055ea8e948e463c5aac7bf4f0461ebebcdfd2d2cc76878fecc8be`.
- Frozen CSV:
  `fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723`.
- Build14 bank executable:
  `765894acc822bfe4b215b6e5faf321ba48d986c74cc434f48189c773f3e03e4b`.
- Exact aggregates04/05 and their bound per-query/contact proofs are named in
  `final-acceptance.json`. Performance repeats reuse only identical same-mode
  scientific rows; raw observations and exclusions are in `PERFORMANCE_AB.md`.
- `publication-source-binding.json` maps raw compiler-input hashes to Git
  content hashes/blob IDs. Two source files have only CRLF-to-LF normalization.
  Reports use a scoped `-text` attribute so linked evidence hashes survive Git.

## Reproduction and resource gates

Use existing /opt/openmc-venv/bin/python, GCC14.2, CMake3.31.6, Ninja1.12.1
and installed dependencies. No acquisition is needed for this state.
Build directories `build/astra` and `build/astra-native` are ignored local
artifacts; final configuration/input identities are in build14's receipt.
Native flags include experimental StellarCSG/offset probe/strict FP enabled
and MPI/OpenMP/DAGMC/tests/submodule update disabled. Cached fmt/pugixml came
from the already-local sibling OpenMC build.

Before any new build, refresh the full operator-required RAM, drive, process,
executable, environment, cache and source inventory. The last observations
are `prebuild-09.txt` / `prebuild-10.txt`, not current resource authorization.
Prior builds used one job and a 1.5 GiB virtual-memory cap; replays/oracles used
1 GiB caps and bounded timeouts. Do not acquire software or start remote work
without satisfying the current user gates.

The bank runner is `qualification/run_offset_bank.py`; required arguments:
`--binary build/astra/stellarcsg_recovery04_bank --wistell <hash-matched H5>
--output <new directory>`, with `--no-bernstein-prefix` for the off variant.
It preserves launch/candidate/stderr/receipt artifacts and refuses reused output
directories. Use bounded execution and avoid concurrent CPU loads for timings.
The independent verifier and aggregator are
`verify_offset_bank.py` and `aggregate_offset_qualification.py`.
Inspect their CLI before use; preserve existing reports.

Local HDF5 inputs (not duplicated in PR):
- Analytic: sibling `stellarcsg-local-continuation-20260925/dev/stellarcsg/qualified/analytic_swept_coils.h5`,
  SHA `39f77da5ab1fe427cce58b153e9b52cf8915e9973a9b8f3dfad5ab3b00a9e46d`.
- Coil031: sibling `stellarcsg-root-repair-07/dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5`,
  SHA `9bb178c308e7f3ec659e1651a7d57e0ecbff734d3320000df1c2bf79fcf3262b`.

## Next work and blockers

1. Keep the draft's changed-representation claim explicit. Extend positive-hit
   qualification to nontrivial real-coil offset cases before any wider claim.
2. Investigate nine fail-closed normal queries and allocation/projection costs.
   Preserve conservative rejection on ambiguous normals; do not reinterpret
   missing telemetry as success.
3. Define a matched native comparator and workload before attempting the 80%
   throughput claim; follow `PERFORMANCE_PLAN.md`.
4. Physical rectangular/varying-frame packs, collections, periodic boundaries
   and neutron/photon histories need separate geometry/transport qualification.
5. The legacy source-loader swapped-hash false-PASS remains a known issue.
   Do not treat the newly strict comparator as a repair of that loader.

Build13 is a rejected changed-input binding; runs06-09 are excluded from clean
timing because they overlapped verification. Both remain preserved. There are
no automatic successors, schedules, remote authorizations or merge instructions
in this handoff.
