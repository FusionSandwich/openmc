# StellarCSG independent method handoff - 2026-09-15

## Start here

Repository: https://github.com/FusionSandwich/openmc

Handoff branch: `JS/stellarcsg-root-repair-20260915-07`.
Repair evidence checkpoint: `54977b51d` (later commits add this dispatch handoff).
Isolated, less expensive acceptance repair: branch
`JS/stellarcsg-acceptance-only-20260915-07`, commit
`9dab4041670fa835153c1a9c367595d4be7c3d3b`.
The handoff branch contains ALL repair experiments, including rejected ones;
its production head is NOT the preferred starting kernel.

Read `REPAIR_07_CHECKPOINT.md` for detailed attempts, results and remaining gaps.
Read `RUN_COMPARE_06_CHECKPOINT.md` for the prior transport diagnostic, and
the inherited recovery04 reports for historical evidence. Do not silently
reuse their desktop paths or compare timings measured on different machines.

The user's latest request authorizes separate parallel exploratory sessions
for the methods below. This supersedes earlier sequential experimentation
only; no correctness, fidelity, performance or promotion gate is waived.

## What was tried

| Attempt | Result | Disposition |
|---|---|---|
| Recovered seed repair vs old fast | .002 cm earlier-entry fixture repaired; strict wrong 4 to 3 | unqualified control |
| Recompute actual final Newton residual | no strict fix; exposed real23 false hit .19916695971482617 cm | retain negative evidence |
| Process all queued nearer unresolved spans | no observed fix; 2.87x old cost | rejected for promotion |
| Broad suspect-crossing bracket/fail-closed | 21/160 strict rays blocked | overblocking experiment |
| Outward span bounds + necessary center-box exclusion | reduced blocks to17; conditional ideal-spline algebra reviewed | no full certificate |
| Narrow guard to residual-qualified candidates | fixes a15 to about1.1e-11 cm error; a06/a08 still wrong | partial repair |
| Combined narrowed guard + ordering + bounds | 4.15x old | rejected for promotion |
| Isolated residual + narrowed acceptance guard | latest paired old/seed/new1.280/1.807/2.423 us; strict wrong4/3/2 | experimental, not promoted |
| Prior2D interval cover |90 root-free/70 unresolved, ~106397 ns/query | rejected hot path |
| Exact/GMP-heavy common path | stronger root reference, severe speed regression | offline oracle/rare fallback candidate |

Isolated acceptance still has12 wrong +3 explicitly BLOCKED on the separate
160-ray real stress bank, and2 failures among256 admitted retained rays.
The remaining128 retained geometry BLOCKED states are not PASS, are not
necessarily physically invalid, and are not enforced by recovered production.
Strict a06 is origin contact; a08 is an even-multiplicity tangent; real23 is
still a wrong finite hit. No fully corrected fast baseline exists yet.

Bounds review: regular center tangent and independent supplied normal must
be admitted over whole spans; raw radius bounds do not enclose floating
Horner/frame/trigonometric error; retained/zero-proxy/solved-prefix ordering
is still unresolved. The focused bounds test is now wired into CTest with
Release assertions enabled. It is not a whole-solver certificate.

## Independent lanes

| ID | Scope | Production starting point |
|---|---|---|
| fast-original | original fast architecture, minimal correctness and optimization | c67b68fd; selectively compare seed/acceptance patches |
| bernstein-coils | fixed-size floating/interval Bernstein exclusion/isolation, rare fallback | old architecture, not combined repair07 |
| torus-arcs | automatic circular-arc/biarc fitting and finite torus-segment quartics | isolated prototype and original control |
| bezier-plasma | Cartesian bicubic atlas with measured conversion error and edge ownership | original periodic patch control |
| swept-fiber | ray-centric swept-fiber candidate solving plus independent ordering | isolated prototype and original control |
| period-import | actual periodic sector, finite images, fidelity, generic import and heldout fold | compiler/integration code; no kernel mathematics ownership |

Each lane's complete task brief is in `cloud-methods/<ID>.md`. Keep a separate
JS/ branch, return hashes/commands/results and a patch/commit; do not merge,
force-push, create a PR or publish new experimental work without authorization.
Never advance archive, develop/default, reference or original checkpoint refs.

## Portable inputs and controls

All paths below are REPOSITORY-RELATIVE and tracked in this handoff branch:

- `dev/stellarcsg/qualification/recovery04_frozen_bank.csv`:160 unique strict rays;
  SHA2567348483e39128259a844d22a7618869a3f111604ea48d01e196a87fe0d396af7.
- `dev/stellarcsg/reports/product05/real-bank/rays.csv`: separate160 real stress rays.
- `dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5`: frozen compiled coil input.
- `dev/stellarcsg/reports/recovery04/retained-input.txt` and
  `retained-exact-reference.jsonl`:384 retained rays and reference dispositions.
- `dev/stellarcsg/reports/repair07/baseline-strict/exact_reference-0.jsonl` and
  `stages-stress/exact_reference-0.jsonl`: exact lane outputs for these banks.
- `dev/stellarcsg/reports/product05/model-02/plan/plasma_boundary.h5`:
  existing plasma payload. XML/receipts may contain desktop paths; rebind a
  separate copy, retain input hashes and source provenance, never rewrite evidence.

Preserved old commit: `c67b68fdaf7be2049308db7da449f14a25123847`.
Recovered seed: `57cb1fbf75a54a0fa75e70386922ad9cfecf06b1`.
Intermediate A: `4e1efc947c5aa713a36c81d650a35ca71e60d2e1`.
Exact reference: `5ed327ade33b31ecdb5e3b4b4111c55f321991fd`.
These are controls, not blanket endorsements. Check fetched SHAs explicitly.
Git clone/build access and Pro model selection must be reported from the
actual destination environment, never inferred from a session's name.

Before cloning/installing/building, audit the destination environment under
the user-wide resource/acquisition rules in the task brief. Reuse installed
tools; do not acquire anything when required audit observations are unknown.
This handoff preparation does not install dependencies or run new builds.
The standalone HDF5 kernel does not need nuclear cross sections. Full native
transport does: the desktop's H1 library/binaries are NOT cloud inputs.

After a successful environment audit, clone the handoff branch and make a
new method branch. On Linux with existing C++17/CMake/Ninja/HDF5/Python:

```bash
git clone --single-branch --branch JS/stellarcsg-root-repair-20260915-07 https://github.com/FusionSandwich/openmc.git stellar-method
cd stellar-method
git rev-parse HEAD
# Create a unique JS/ method branch before edits; select the method's control
# production source instead of treating this experimental head as preferred.
cmake -S dev/stellarcsg -B build/cloud -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTELLARCSG_ENABLE_HDF5=ON -DSTELLARCSG_ENABLE_PERFORMANCE_COUNTERS=OFF -DSTELLARCSG_VERIFY_FAST_WITH_ORACLE=OFF
cmake --build build/cloud --parallel 1 --target stellarcsg_recovery04_bank stellarcsg_retained_replay stellarcsg_swept_seed_regression stellarcsg_reference_tests stellarcsg_compiled_surface_tests
ctest --test-dir build/cloud -R 'swept_seed_regression|reference_tests|compiled_surface_tests' --output-on-failure
python3 dev/stellarcsg/qualification/recovery04_measure.py --lane "candidate=$PWD/build/cloud/stellarcsg_recovery04_bank" --bank "$PWD/dev/stellarcsg/qualification/recovery04_frozen_bank.csv" --coils "$PWD/dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5" --output "$PWD/results/strict-01" --repetitions 7
python3 dev/stellarcsg/qualification/recovery04_replay.py --binary "$PWD/build/cloud/stellarcsg_retained_replay" --input "$PWD/dev/stellarcsg/reports/recovery04/retained-input.txt" --reference "$PWD/dev/stellarcsg/reports/recovery04/retained-exact-reference.jsonl" --output "$PWD/results/retained-01"
```

Known a08 regression failure is expected at the unmodified handoff, not a
successful qualification. The measurement wrapper exit0 only means it recorded
attempts: inspect child exit/status and compare exact roots. The exact_reference
lane's candidate is the exact result; SKIPPED refers to an optional second
legacy solve. Do not reuse `recovery04_build_controls.py` unchanged: it has
desktop-specific paths. Build each control's library in its own worktree and
link the same frozen-bank harness against that lane's public headers/library;
derive HDF5/GMP paths from the destination toolchain. Report a build blocker
if this cannot actually run, rather than inventing benchmark numbers.

## Qualification remains mandatory

No silent no-hit for unresolved states; every possible earlier-root interval
must be excluded or resolved. No cache advantage in unique-query timing,
global ray scans, wholesale GMP hot path, tolerance inflation, or blanket
Newton-iteration increases. Measure candidate/recovery/fallback counts AND
time, allocations and memory; unavailable remains null. Preferred<=1.25xold,
temporary<=2x only for a demonstrated correctness fix; slower stays experimental.

WISTELL NFP4 implies90 degrees. Existing16-member diagnostic is vacuum-clipped,
not periodic qualification and not first12 coils. Include necessary neighbor
images, per-coil identities/material/tallies and closure. No whole machine or
intersecting blanket. Fidelity must include absolute cm and local tube/minor
size normalization; use0.1/0.5/1/2% approximation ladder where applicable.
Source winding-pack fidelity, clearance, periodic rotation mismatch and
heldout ParaStell theta fold remain open. No matched Double Down result yet.
Only an eligible method advances to final transport/fidelity/mesh comparison.
