# Exact restart commands

Run from PowerShell on this workstation. These reuse existing dependencies,
preserved build artifacts and verified source worktrees. Recheck resources
before any new build. No SSH, installation, PR or protected-ref update is needed.

```powershell
$R = '/mnt/c/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS/stellarcsg-fast-recovery-04'
$PY = '/opt/openmc-venv/bin/python'
git -C stellarcsg-fast-recovery-04 status --short --branch
git -C openmc-stellarcsg rev-parse archive/stellarcsg-qualified-c67b68fd-20260831
Get-FileHash stellarcsg-fast-recovery-04/build/recovery-04-seed/stellarcsg_recovery04_bank
```

Expected archive SHA is c67b68fdaf7be2049308db7da449f14a25123847; expected seed
benchmark SHA256 is 908900465f2b032a537a1fcc3703220b85fb6b34cd94d3f5bd9eec496faf694e.
Choose a new output suffix if a restart directory already exists. Scripts retain
failed attempts and reject overwriting campaign directories.

## Reproduce retained failures

```powershell
wsl -d OpenMC-Dev-D -- $PY "$R/dev/stellarcsg/qualification/recovery04_replay.py" --binary "$R/build/recovery-04-seed/stellarcsg_retained_replay" --input "$R/dev/stellarcsg/reports/recovery04/retained-input.txt" --reference "$R/dev/stellarcsg/reports/recovery04/retained-exact-reference.jsonl" --output "$R/build/restart-retained-01"
wsl -d OpenMC-Dev-D -- ctest --test-dir "$R/build/recovery-04-seed" --output-on-failure
wsl -d OpenMC-Dev-D -- $PY "$R/dev/stellarcsg/python/tests/test_swept_exact_oracle.py"
```

The first command records two admitted retained mismatches and 128 reference
blocks. Its wrapped C++ process exits 1; the recorder itself exits 0 after
successfully writing the negative evidence. Read comparison.json, not just the
recorder exit code. CTests pass because they assert only their stated scope.

## Repeat the fixed comparison

```powershell
wsl -d OpenMC-Dev-D -- $PY "$R/dev/stellarcsg/qualification/recovery04_measure.py" --lane "old=$R/build/recovery-04-controls/old" --lane "experimental=$R/build/recovery-04-seed/stellarcsg_recovery04_bank" --lane "previous_A=$R/build/recovery-04-controls/previous_A" --lane "exact_reference=$R/build/recovery-04-controls/exact_reference" --bank "$R/dev/stellarcsg/qualification/recovery04_frozen_bank.csv" --coils "$R/dev/stellarcsg/reports/recovery04/wistell-coils-1cm.h5" --output "$R/build/restart-off-01"
wsl -d OpenMC-Dev-D -- $PY "$R/dev/stellarcsg/qualification/recovery04_reduce.py" --campaign "$R/build/restart-off-01" --output "$R/build/restart-off-01/reduced.json"
```

Do not regenerate the comparison CSV while repairing the kernel. Primary timing
requires 160 unique complete queries, seven complete repetitions, correct binary
and payload hashes, and independent reference dispositions. Preserve negative
results. The current exact control uses its default filtered/monotone mode 2.

## Rebuild controls safely

**Do not rebuild build/recovery-04-baseline against the changed root source.**
It contains the immutable pre-edit library used for this session. For a fresh
old control, use the separate bank worktree, whose production sources remain
identical to c67b68fd. Validate that before compiling:

```powershell
git -C stellarcsg-recovery-bank-04 diff --exit-code c67b68fd -- dev/stellarcsg/src dev/stellarcsg/include dev/stellarcsg/CMakeLists.txt src/external/quartic_solver.cpp
wsl -d OpenMC-Dev-D -- cmake -S "$R/../stellarcsg-recovery-bank-04/dev/stellarcsg" -B "$R/build/restart-old" -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTELLARCSG_ENABLE_HDF5=ON
wsl -d OpenMC-Dev-D -- cmake --build "$R/build/restart-old" --target stellarcsg_reference --parallel 1
wsl -d OpenMC-Dev-D -- g++ -std=c++17 -O3 -DNDEBUG -DSTELLARCSG_HAS_HDF5 "-I$R/../stellarcsg-recovery-bank-04/dev/stellarcsg/include" -I/usr/include/hdf5/serial "$R/dev/stellarcsg/qualification/recovery04_frozen_bank.cpp" "$R/build/restart-old/libstellarcsg_reference.a" -L/usr/lib/x86_64-linux-gnu/hdf5/serial -lhdf5_hl -lhdf5 -o "$R/build/restart-old/old-bank"
wsl -d OpenMC-Dev-D -- cmake --build "$R/build/recovery-04-seed" --target stellarcsg_recovery04_bank stellarcsg_retained_replay stellarcsg_swept_seed_regression --parallel 1
```

The A Release build and current exact-reference linkage commands/hashes are
recorded in build/recovery-04-controls/receipt.json. The executable builder is
qualification/recovery04_build_controls.py; it requires the preserved baseline
library to remain present and unchanged. The exact static library is at
D:/codex-verification/stellarcsg-20260913-03/kernel-off/libstellarcsg_reference.a,
SHA256 05aac9abab48fbfc89506fe99b294b88475f2a79245369cc791dff8da49762cf.
Instrumented build commands are in qualification/recovery04_profile_build.py.

## Next scientific task

Resolve common-bank a06/a08/a15 and retained shape0/1 index3 without loosening
tolerances or silently declaring no hit. Preserve the fast BVH/local architecture
but account for every interval that might beat the current root. Restore explicit
geometry admission and projection correctness, then rerun these exact controls.
Only after a usable corrected baseline passes the gates should method competition
and the one-period distributed OpenMC/material/tally diagnostic begin.
