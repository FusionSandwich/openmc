# Local recovery preflight, 2026-09-13

Root assignment: GPT-6 Astra, as explicitly requested. Available children:
Sol, Terra, Luna, Astra, GPT-5.5; four total concurrency slots. Historical
inventory assigned to Luna/Medium; numerical decisions remain with Astra.

Verified local and live origin refs before work:

- archive/stellarcsg-qualified-c67b68fd-20260831: c67b68fdaf7be2049308db7da449f14a25123847
- codex/stellarcsg-native-csg-foundation-20260828: 5faf87421d5d2066278c7ae02e38138fc22ec894
- JS/stellarcsg-a-20260913-01a09: 4e1efc947c5aa713a36c81d650a35ca71e60d2e1
- JS/stellarcsg-fast-20260913-03: 5ed327ade33b31ecdb5e3b4b4111c55f321991fd
- develop: 9a62e431d3101799e6179a6d0cf3b37440062e23

New local worktree: StellarCGS/stellarcsg-fast-recovery-04, branch
JS/stellarcsg-fast-recovery-20260913-04, based directly on c67b68fd.
No fetch, reset, protected-ref update, dependency install, or SSH performed.

## Computer and existing capabilities

Windows RAM: 33,457,440 KiB total, 2,310,792 KiB free at initial inspection.
System/worktree drive C: 61,564,395,520 bytes free; data drive D:
59,406,127,104 bytes free. Largest resident processes: Chrome (several
0.5-1.1 GB processes), ChatGPT 882 MB, Codex 699 MB, OneDrive 629 MB,
Explorer 506 MB, Defender 502 MB. Other user processes were not stopped.

Local WSL OpenMC-Dev-D was stopped initially and started for this task.
It reports 25,200,046,080 bytes RAM, 24,361,074,688 available after startup;
the host's physical headroom remains the limiting resource. Root filesystem:
1,021,377,482,752 virtual bytes available, physically backed by D: above.
No preexisting WSL numerical/build process was running after startup.

Existing toolchain: GCC 14.2.0, CMake 3.31.6, Ninja 1.12.1, HDF5 1.14.5,
Python 3.13.5, /opt/openmc-venv (606 MB). Existing packages include numpy
2.5.1, scipy 1.18.0, h5py 3.16.0, pytest 9.1.1, clang-format 18.1.8.
The venv's editable OpenMC points to an unrelated project: set PYTHONPATH
explicitly for this work; do not alter the environment.

Windows Python 3.12 and CMake 4.4 also exist; no native C++ compiler was on
PATH. Windows Conda package caches D:/conda-pkgs and D:/conda-pkgs-linux
contain cache metadata; D:/miniforge3/envs is absent. Local Windows caches
include pip, .cache/codex-runtimes and .cache/codex-tools. WSL apt archive
cache: 24 MB; root pip cache: 152 MB. Other local /opt installations are
g4gate7 and g4native. No additional home Python environment matched the
bounded inspection. Existing StellarCSG checkouts and numerous release,
instrumented, sanitizer and OpenMC build directories are already local.

## Planned build

Acquisition bytes: **0**. Existing local capabilities are sufficient.
A fresh build is needed to bind the reproduced binary to the preserved
source rather than trusting mutable historical build directories.
Target: build/recovery-04-baseline in the new worktree on C:; expected
incremental storage below 250 MB for the standalone library/tools.
Use one compiler process and one benchmark process at a time. No dependency
environment creation or modification. No full-machine transport.
Rollback: retain the isolated source/evidence branch; generated files are
confined to this new build directory and may be removed explicitly later.
No automatic cleanup or deletion is part of this task.
