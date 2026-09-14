# Compare 06 Native Build Preflight

Date: 2026-09-13T20:49:36-04:00
Target: `C:\Users\joshu\OneDrive\Documents\ChatGPT\StellarCGS\stellarcsg-run-compare-06`
Requested build: `build/native-recovered-06`, Ninja, serial (`--parallel 1`)

## Host capacity

- Windows physical memory: 34,260,418,560 bytes; 20 logical processors.
- Free space: C: 60,550,127,616 bytes; D: 54,093,709,312 bytes.
- WSL memory: 23 GiB total, 22 GiB free/available, 32 GiB swap unused.
- WSL filesystems: `/mnt/c` 57G available; `/mnt/d` 51G available.
- Dominant running processes were OneDrive, ChatGPT, Chrome, Explorer; no build was running.

## Existing tool checks

- CMake: `/usr/bin/cmake`, version 3.31.6.
- GNU C++: `/usr/bin/g++`, version 14.2.0-19.
- Python: `/usr/bin/python3`, version 3.13.5.
- Ninja: absent from PATH and absent at `/usr/bin/ninja`, `/usr/bin/ninja-build`, `/usr/local/bin/ninja`, `/opt/ninja/bin/ninja`, and `/opt/openmc-venv/bin/ninja`; Windows `where ninja` also returned no path.
- Requested build directory did not exist or contain a CMake cache.

## Result

The worker initially did not attempt configuration, incorrectly interpreting
incomplete WSL checks as a missing executable. Root independently ran
`wsl -d OpenMC-Dev-D -- /usr/bin/ninja --version`, waited for session 80307,
and obtained exit 0, version 1.12.1. Ninja is AVAILABLE. The earlier absence
claim above is retained only as a rejected inventory conclusion.

## Root-authorized build plan

Root's pre-acquisition observation: total RAM 33457440 KiB, free 2268216 KiB;
C: free 60500766720 bytes, D: free 54101504000 bytes. Existing WSL OpenMC-Dev-D
has GCC 14.2, CMake 3.31.6, Ninja 1.12.1, HDF5 1.14.5, Python 3.13.5;
/opt/openmc-venv is 606 MB, pip cache 152 MB, apt cache 24 MB. No owned build
or transport was running. Root's full worktree map is retained in the earlier
checkpoint; source is 7a8c465e3 in a new comparison branch.

External acquisition 0 bytes. Reused local Git submodule objects (no fetch):
pugixml ee86beb30e4973f5feffe3ce63bfa4fbadf72f38 and fmt
0c9fce2ffefecfdce794e1859584e25877b7b592. Materialized by local git archive
and extraction into this new worktree, <25 MB. Existing exact native binary
cannot measure the recovered source, so a fresh native build is needed.
Target build/native-recovered-06, <500 MB expected, one compiler, no install.
Rollback is confined to new generated outputs; no cleanup is requested.
Configure with GIT_SUBMODULE=OFF, Release, experimental ON only in build,
OpenMP ON, MPI/DAGMC/counters/oracle-verification OFF. Source defaults stay OFF.

## Isolated old-control relink

Before the additional build, Windows free RAM was 2545728 KiB, C: free
59644420096 bytes, D: free 54065385472 bytes. Largest processes: vmmemWSL
2.15 GB, Chrome 0.94 GB, ChatGPT 0.93 GB, Codex 0.80 GB, Explorer 0.76 GB.
The serial recovered build was the only owned compute work. Existing tools,
environments and caches are unchanged from the audit above.

`git diff --numstat c67b68fd -- src include dev/stellarcsg/src
dev/stellarcsg/include` reports only compiled_swept_surface.cpp (73 additions,
44 deletions). Reuse the completed recovered native objects and replace this
one compilation unit with the preserved source from recovery-bank-04, after
verifying its equality to c67b68fd. This avoids a second full native build.
External acquisition: 0 bytes. Additional target: build/native-old-control-06,
under 100 MB planned. One compile followed by one relink, after the first build
ends. No existing objects, library, source or protected ref may be overwritten.
Rollback is confined to the new generated directory; no cleanup requested.

The matched diagnostic is serial: 64 histories, seeds 17/19/23, one OpenMP
thread, all three lanes use geometry-debug. Per-attempt timeout: 120 seconds.
No timing overlaps a build or another owned numerical run.
