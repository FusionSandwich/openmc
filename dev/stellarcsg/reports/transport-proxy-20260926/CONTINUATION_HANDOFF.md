# Continuation after matched plasma/coil proxies

State: completed finite local test campaign; no active simulation, remote job,
automatic successor or schedule was created. The native throughput goal and
full-spectrum/upstream qualification remain unmet. Read RESULTS.md and the
independent REVIEW_FINAL.md before making broader claims.

Source: JS/stellarcsg-astra-kernel-20260926, existing managed checkout; draft
PR5 at https://github.com/FusionSandwich/openmc/pull/5. Do not alter PR3 or the
original checkpoint. Final native binary/library and static tests are bound by
build-04/receipt.json; campaign-plan.json fixes all 18 transport identities.

The only new geometry production changes since the earlier milestone are exact
plasma specialization checks/dimension guards, explicit coil prefix-option
serialization, and outward offset search endpoint guards. Refer to source
diffs and failed-before/passed-after tests. Neither kernel was approximated to
obtain a faster timing.

Reproduction tools in dev/stellarcsg/qualification:
- proxy_transport.py prepares fixtures or executes one bounded named run.
- run_proxy_campaign.py executes the fixed finite plan in fresh directories.
- compare_proxy_transport.py validates raw artifacts and paired results.
- audit_proxy_artifacts.py tests forged receipts and pilot tracks.
- proxy_coil_geometry.py independently bounds the prepared coil geometry.
- run_offset_bank.py / verify_offset_bank.py / aggregate_offset_qualification.py
  reproduce the frozen exact-control certificates.

Use new output directories; retain existing results. Current output paths are
fixed by the campaign driver and would need an explicit fresh report-root edit
before a rerun. Do not blindly relaunch or overwrite. Timings must be isolated
from builds/oracles/other deliberate heavy work. The completed campaign used
one thread, 2 GiB per transport process and a 180-second process timeout.

All dependencies and FENDL Fe56 data were already local. No acquisition or
environment mutation occurred. Before any future build/acquisition, refresh
the operator-required RAM, drive, process, environment, executable/version,
cache and local-source inventory; this report's inventory is historical.
Local WSL memory is shared host RAM, not extra capacity. Prior builds used one
job and 1.5 GiB; no remote execution is authorized by this handoff.

Next substantive work: profile the measured performance gaps and design a
bounded optimization with independent acceptance. Improve sparse-bin sampling
and add non-axisymmetric/real-material transport qualification. Preserve every
unsupported state and keep the physical-pack and old loader issues explicit.
