# Local continuation receipt — 2026-09-25

## Isolation and resource gate

- Actual repository: `openmc-stellarcsg`; continuation worktree/branch: `stellarcsg-local-continuation-20260925` / `JS/stellarcsg-local-continuation-20260925`.
- Starting production commit: `c67b68fdaf7be2049308db7da449f14a25123847`. Evidence-only control: `c92ae5a6c497650f0cbf0218a5ec00ae59817d00` in a separate clean worktree.
- Windows RAM: 33,457,440 KiB visible, 3,668,704 KiB free at audit. C: 89,636,298,752 B free of 998,965,768,192 B; D: 506,377,859,072 B free of 2,000,397,791,232 B. C: is system and target; D: is local data drive.
- Largest resident processes at audit: Memory Compression 2.20 GB, ChatGPT 1.13 GB, Chrome 0.98 GB, Codex 0.67 GB, Explorer 0.67 GB; further Chrome/ChatGPT/OneDrive processes were active.
- WSL `OpenMC-Dev-D`: MemTotal 24,609,408 KiB, MemAvailable 23,799,396 KiB after startup; root filesystem 1,021,385,912,320 B available; C: and D: mount space agreed with Windows. No significant WSL compute process appeared in the top RSS list.
- Existing tools: Windows Git 2.55.0, Python 3.12.10, CMake 4.4.0; WSL Git 2.47.3, GCC 14.2.0, CMake 3.31.6, Python 3.13.5. Existing `/opt/openmc-venv` is 606 MB; WSL pip cache is 152 MB. Windows pip cache and `.cache` exist; no Windows `.conda` or `C:/ProgramData/miniconda3` was found. Existing `OPENMC_CROSS_SECTIONS` points to a present local `cross_sections.xml`.
- Existing source/build checkouts are present in the StellarCGS directory, including the actual OpenMC repository, root-repair evidence and benchmark arena; `openmc-stellarcsg/build` and `stellarcsg-root-repair-07/build` already exist. They are controls, not write targets.
- Acquisition decision: no external software or data needed for the present patch/test milestone; planned download/install bytes: 0. The isolated local worktree uses already-local Git objects on C:. Any later build must use the existing compiler/HDF5/toolchain, be bounded by free RAM/disk, and record its exact output target and rollback before starting. The worktree and its branch are retained for review, not automatically removed.
- No SSH, remote jobs, protected-ref changes, or publication occurred in this task.

## Portable benchmark runner recovery

- Chat artifact `benchmark-portability.patch` was downloaded through the saved ordinary ChatGPT conversation after the local resource gate. Its SHA-256 is `a86eb95596b462b60eb062b2889245e69619ee6e98953498bd6bfd669ba8dc8d`, matching the review. `git apply --check` succeeded against this full local checkout.
- The additive patch creates `dev/stellarcsg/experiments/benchmark_portability/` only. It does not change the production solver or adapter.
- Test command: `PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /opt/openmc-venv/bin/python dev/stellarcsg/experiments/benchmark_portability/test_portability.py` from this worktree inside WSL `OpenMC-Dev-D`.
- Result: 76 tests passed in 10.535 s, exit 0. These use analytic/mock fixtures and validate receipt mechanics; they are not native WISTELL-D or ZTorus measurements. The new runner remains opt-in.

## Outstanding qualification

Native ZTorus, recovered-old and any corrected candidate have not yet been measured in the same session here. The root, floating enclosure, adapter, physical fidelity, period transport and source interface gates remain open. No benchmark or physics pass is inferred from the 76 runner tests.
