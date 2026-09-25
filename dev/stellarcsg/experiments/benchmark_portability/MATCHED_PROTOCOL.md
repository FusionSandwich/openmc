# Gated matched one-period protocol — NOT EXECUTED

Baseline: `c08eea92ca3fb63eb8adbf44cfb4ea8612639e30`.
Authority: `reports/cloud-methods/benchmark-portability.md`,
`reports/CLOUD_METHOD_HANDOFF.md`, `reports/REMAINING_WORK_DISPATCH.md`, and
`reports/REPAIR_07_CHECKPOINT.md`, relative to `dev/stellarcsg/` at that commit.
This document prepares a protocol, not another transport campaign. The accompanying
validator checks evidence identity; it does not launch jobs or certify the evidence.

## 1. Admission and authorization before any future execution

Run `gate_validator.py matched_readiness.blocked.json` now: all twelve gates are
BLOCKED. The present runner test success completes none of these gates. A future
readiness manifest must retain every gate, with PASS supported by hash-bound
files, reviewer identity, and explicit scope. A syntactically complete manifest
returns EVIDENCE_PRESENT_REQUIRES_FINAL_REVIEW, not permission to launch.

Required gates cover whole-span geometry admission; binary64 bound/completeness
and nearest-root obligations; explicit origin-contact/transport suppression;
even roots, zero-proxy spans and exclusion of earlier unresolved prefixes; exact
reference provenance and preserved negative cases; recovered-old cost guardrails;
and same-session native ZTorus control. Finite ray samples alone cannot certify
the solver. No tolerance inflation or silent unresolved-to-miss conversion is allowed.

Independently require a qualified physical assembly, periodic sector and
fidelity/clearance evidence, matched physics configuration, frozen native/H5M
payloads, separately verified ordinary-DAGMC and Double Down/Embree runtimes,
lost-history/closure contracts, explicit execution authorization, and a fresh
resource audit. Unknown required audit observations block acquisition. No mesh
stack, nuclear library, or remote runtime is acquired under this dispatch.

## 2. Correct geometry and historical provenance

The tracked raw inputs match the accepted source repository
`FusionSandwich/wistell-d-openmc`, commit
`58363040ebb0fa5ee5ca7f6f6c3a96e2b2cfc1c7`, branch
`fix/linux-coil-input-integrity-20260828`:

| Input | SHA256 |
|---|---|
| wout_wistell-d.nc | `9231969001203a8133255ee0a275bf552b114cc12524dda0608ab2f12047f7ac` |
| coils.wistell-d | `7748369407d28a70f35b5c4a7c0ab860495a08fd0030002112ea933fe570159b` |

This is source-byte provenance, not engineering-geometry equivalence. The accepted
historical explicit-coil diagnostic was `90deg_direct_explicit_coils_offset40_smoke`,
with a **40 cm blanket offset** and H5M SHA256
`237fbd562acac918c239073e95e3b0db75cda4fe25363a9a925efa53e307a34c`.
The 25 cm prototype intersected three square coils. The separate production model
uses a continuous 30 cm winding-surface layer. Current StellarCSG's **1 cm circular
coil envelopes, no blanket, vacuum-clipped 90-degree diagnostic** are neither model.
Do not infer physical winding-pack clearance or mesh superiority from them.

Historical accepted Bateman workflow provenance is a 10,000-history smoke of the
accepted diagnostic, as reported in the pinned dispatch. It is **not** a matched
native versus Double Down benchmark. The retained `nompi_nodoubledown` runtime
lacked Double Down. Current live Bateman linkage is unknown and was not inspected;
that historical absence does not establish current machine capability. Recent
native comparisons in the dispatch were local WSL work. No historical ordinary-
DAGMC ratio may be relabeled as a Double Down measurement.

The eventual geometry must explicitly establish NFP=4 and one 90-degree field
period, required finite members and neighbor images, seam ownership and periodic
transforms, unique coil identities/materials/tallies, and geometric/transport
closure. Do not assume the first twelve coils or confuse a vacuum-clipped sector
with periodic qualification. Freeze all transforms, member selections, mesh
settings, tessellation errors and native coefficients. Include absolute-cm and
local winding/minor-size normalized errors and the applicable 0.1/0.5/1/2 percent
approximation ladder. Keep heldout ParaStell theta-fold tests separate. Engineering
clearance must account for total representation/error bounds and physical pack
shape; a sampled max deviation is not automatically a certified clearance margin.

## 3. Identify the actual runtime without running transport

In a separately authorized local environment with existing binaries, gather:

```sh
python3 runtime_probe.py --binary /existing/openmc --component /existing/libdagmc.so \
  --component /existing/libdouble-down.so --component /existing/libembree.so \
  --build-record /existing/CMakeCache.txt --build-record /existing/link-map.txt \
  --output NEW-runtime-evidence.json
# Optional only for an already-running, explicitly identified LOCAL process:
python3 runtime_probe.py --binary /existing/openmc --pid EXISTING_PID --output NEW-maps.json
```

These are placeholder paths, not assumptions about available files or approval
to launch a process. Do not run the target, invoke SSH/ldd, or start a runtime just
to populate this evidence. The collector reads ELF DT_NEEDED/build IDs, component
hashes, selected build flags and optional local maps. Build IDs are not package
versions. Record actual OpenMC/MOAB/DAGMC/Double Down/Embree version/commit identities,
compiler and options, ABI, shared/static choices, and hash-bound build provenance.

For dynamic linkage, review the complete resolved chain and configuration to the
ray-tracing implementation. Relevant libraries in a search path or DT_NEEDED list
are insufficient to prove the active backend. Local maps add evidence of loaded
objects, not that a particular code path was used. For static linkage, require
hash-bound link map/object/archive provenance and corresponding source/build
configuration; absence of a shared-library name is not proof of absence. Review
conditional dispatch/backend selection and any environment overrides. Conflicting,
missing, or incompletely bound evidence leaves the backend UNVERIFIED.

Keep separate labels for verified ordinary DAGMC, verified DAGMC with actual
Double Down/Embree path, native CSG, and UNVERIFIED. Do not promote a filename,
`OPENMC_USE_DAGMC` flag, or a fabricated version string into backend verification.
Our collector intentionally emits UNVERIFIED pending that review.

## 4. Freeze a genuinely matched physics manifest

Before measuring, freeze hashes of native geometry, H5M, binaries and linked/static
components, coefficient/source inputs, XML/configuration files and nuclear-data
indices plus material data actually used. Match the sector normalization and
physical source rate separately from the normalized birth distribution. Freeze
source bank bytes, weights, space/energy/angle/time distributions, RNG algorithm
and seeds, materials/nuclides/densities/temperatures, physics settings, periodic
and exterior boundary behavior, tallies/filters/scores/normalizations, history
counts, batches, particles, threading/MPI settings and hardware placement.

Same input source histories do not imply identical collision streams or tracks
across geometry backends; record the reproducibility contract actually supported.
Count attempted, completed, aborted and lost histories separately. Match explicit
coil and sector tally attribution. Predeclare statistical comparison methods and
physics/error budgets from requirements; do not widen thresholds after results.
Set history-loss acceptance to zero unexplained lost/aborted histories for the
qualification run, and preserve any contrary result as failure, not a denominator
change. Closure must address sector boundary leakage/rotation, volume/material
identity and tally/source normalization; use appropriate physics balance equations
rather than treating interacting transport as simple particle-number conservation.

## 5. Measurements, controls, and ordering

Use a fresh audited session, single CPU initially, identical compiler/options where
meaningful, and no owned concurrent build or benchmark. Record other significant
processes; their presence is not hidden. Run at least seven fresh-process repeats
with alternating/interleaved lane order after an explicitly recorded setup/warmup
policy. Do not report a warmup/setup subtraction as an unmeasured kernel time.
Use the same frozen **unique** ray/query banks and explicit query classes. Point
classification and normal evaluations require their own bank hashes/uniqueness;
normal locations derived differently by each backend need a sentinel label or a
separate frozen matched point bank. Document timer overhead, cache policy and
instrumentation mode. Fresh process does not imply cold hardware/page caches.

In that same session, measure native **OpenMC CSG ZTorus** distance, classification,
and normal costs alongside every candidate and recovered-old control. This is not
a mock torus or the spline-tube torus. Report absolute ns/query, complete-bank mean
per repetition and its median, pooled per-query median/P95/P99, repeat variation,
bank/model/binary hashes, compiler/options, CPU/thread settings and process timing.
Keep instrumented candidate/Newton/recovery/fallback counts, count/time fractions,
allocations and peak memory in separate diagnostic runs; unavailable remains null.
A blocked/incomplete bank has no survivor-only full-bank performance value.

Geometry ratio = candidate ns/query / native ZTorus ns/query. Preserve the same-
session recovered-old ratio and 1.25x preferred / conditional 2x temporary limits.
Torus geometry/banks unlike a candidate yield a **sentinel cost ratio**, not a
matched-fidelity speedup. Never compare raw ns/query across computers.

For transport, after all gates and new authorization, independently record end-to-
end wall time, setup/load time, transport time and completed histories. Report
completed histories per transport second with the exact denominator; label any
end-to-end throughput separately. Transport ratio = candidate histories/s / native
ZTorus histories/s. Any reciprocal must be called an inverse slowdown. Unlike
Torus source/geometry settings stay sentinel-only. Ordinary-DAGMC and verified
Double Down comparison requires the same qualified physical model and matched
physics manifest, not merely approximately equal dimensions. Missing native
ZTorus gives null ratios and an incomplete comparison, never an exemption.

## 6. Retention and decision

Preserve every child exit, signal, timeout, stderr, raw output and failed gate.
Keep sampled reference, declared exact-oracle provenance, unavailable reference,
and BLOCKED geometry separate. A finite-bank PASS or a valid receipt never proves
nearest-root completeness. Record revisions and immutable hashes; do not overwrite
historical evidence. Re-review readiness after any binary, input, model, physics,
backend, or environment change. Return a decision with explicit gate coverage,
not a scoreboard winner when prerequisites remain unresolved.

**Current decision: NOT_RUN / BLOCKED.** The only executed jobs in this dispatch
are mock/analytic receipt tests and read-only environment/runtime inspection.
