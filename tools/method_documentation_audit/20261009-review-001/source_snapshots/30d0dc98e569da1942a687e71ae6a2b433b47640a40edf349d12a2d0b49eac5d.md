# Repair 07 preflight, 2026-09-15

Root branch JS/stellarcsg-root-repair-20260915-07 and isolated implementation
branch JS/stellarcsg-local-repair-20260915-07 start at compare06
9c6cc86e0a6543334c973cf5610e58bdb6ad2197. Existing worktree was clean.
Archive c67b68fd, recovery04 57cb1fbf and product05 7a8c465e remain unchanged.
Repo AGENTS.md and local reviewing-openmc-code skill read. Frozen banks and
reference dispositions must not change. Experimental default remains OFF.

## Current machine audit

Windows RAM 34260418560 bytes, free 6867496 KiB; 20 logical processors.
C: free 54.6 GB (system/source/target); D: free 53.9 GB (WSL/data).
Largest residents: Memory Compression 1819 MB, ChatGPT 1082 MB, Chrome 959 MB,
Codex 818 MB, OneDrive 468 MB, MsMpEng 414 MB. No Windows numerical/build
process. WSL OpenMC-Dev-D has 23 GiB total / 22 GiB available memory, mounted
C: and D: each about 51 GiB free. Only root's bounded baseline replay was
running during the final audit; no WSL compiler, CMake, Ninja or OpenMC process.

Existing GCC 14.2, CMake 3.31.6, Ninja 1.12.1, Python 3.13.5 and local HDF5
suffice. /opt/openmc-venv is 606 MB (pip 26.1.2), /root/.cache/pip 152 MB,
/var/cache/apt 116 MB. Known /opt/conda, /usr/local/conda, /root/miniconda3 and
/root/anaconda3 paths absent. Existing source/builds: compare06 full native
recovered/old controls; recovery04 old/seed/A/exact standalone controls;
product05 frozen real stress bank; exact03 local kernel and native builds.
OPENMC_CROSS_SECTIONS is unset; matched transport can explicitly bind the
already-local H1 XML recorded in compare06 without acquiring nuclear data.

## Build scope

External acquisition 0 bytes; no environment changes, installs, upgrades or
remote work. Existing preserved binaries cannot execute source repairs.
New standalone Release/HDF5 builds under root-repair-07/build only, serial
one compiler, expected below 100 MB per isolated stage. Reuse existing runtime
and standard standalone CMake targets; no vendored dependency materialization.
Rollback is confined to new generated outputs, not protected sources/refs;
negative evidence will be retained, no cleanup is requested.
Finish baseline timing before building. Finish builds before timing. Compare
old-fast, seed control, each repaired stage and the existing exact reference
on unchanged banks; replay retained 384 reference statuses separately.
Do not promote an incomplete nearest-root proof based on a Newton residual.

Resolved child roles: Luna/Medium inventory, Terra/Medium bounded edits,
Sol/High independent numerical review; four available slots including root.
