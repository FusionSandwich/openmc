# Local preflight, 2026-09-26 21:18 UTC

Observed Windows free RAM 7,296,608 KiB; C system/target drive free
104,228,012,032 bytes; D data drive free 496,465,088,512 bytes.
The authoritative host observations/processes are in inventory-windows.json.
WSL OpenMC-Dev-D: 25,200,037,888 bytes configured RAM, 24,274,157,568 available,
no swap used. This is not additional host RAM. Root filesystem free
1,021,383,884,800 bytes. No compiler/transport process was present in the
bounded largest-process snapshot.

Existing executables: GCC14.2.0, CMake3.31.6, Ninja1.12.1, Python3.13.5 at
/opt/openmc-venv/bin/python, pip26.1.2, clang-format18.1.8,
h5py3.16.0 and NumPy2.5.1. OpenMC imports from this isolated checkout.
Windows Python3.12, Git2.55 and CMake4.4 are also present.
WSL /opt contains g4gate7, g4native and openmc-venv; no matching root Conda
or .virtualenvs paths and no CONDA_PREFIX/VIRTUAL_ENV were reported.
Existing environment/cache sizes: openmc-venv606MB, pip152MB, apt116MB,
other /root/.cache40KB. Local source checkout inventory is in the JSON.

The existing native libopenmc and offset probe are available; the main OpenMC
executable target has not yet been built in this build directory. Existing
local fmt/pugixml/HDF5 dependencies suffice. Nuclear data index is already local:
/mnt/c/Users/joshu/Documents/2026_DPA/openc-hts-dpa/.data/openmc/cross_sections.xml.
Nuclide/MT444 coverage will be checked before transport.

Acquisition: zero bytes; no dependency/environment changes. Planned incremental
outputs: <=512MiB in own ignored builds/report runs. One build job, <=1.5GiB
virtual memory; bounded sequential transport using <=2GiB. Existing capabilities
are sufficient; compiling changed tests/adapters and the existing executable
target is necessary to execute this follow-up. Rollback preserves evidence
and touches only this follow-up's source changes and generated outputs.
