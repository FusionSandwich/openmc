# Matched native coil total elapsed time, dispatches 005/006

The accepted immutable cache reduces observed total elapsed time by **27–28%**
on this 1,000-history workload. It still takes about **1.96–2.02 times** the
similarly sized built-in torus control. The user's final dispatch-007/008 contract
separates cold geometry build from transport; **the acceptance gate concerns
transport, not total wall time**. This round-tube diagnostic cannot qualify the
full winding pack. Against its torus diagnostic, cached transport is about
1,037x/1,208x native (on/off), with a short native denominator. The required
full-target/flat-ring comparison and cold build measurements remain NOT_RUN.
Read BENCHMARK_RECONCILIATION_007.md for the authoritative coil/plasma tables.

## Fixed completed work and actual wall time

Twelve serial workers completed 12,000 histories: two observations for each
original/cache/native condition with tallies on/off. Each worker uses 20 batches,
50 particles/batch, seed 1741, one thread, a final statepoint and the same summary
policy. Original and cache have identical geometry/source/material/data/world/
settings/tallies. Native changes only the swept near-circle boundary to ZTorus
R=100 cm/r=5 cm, inside the same radius-150 cm vacuum world. Fe56 is unchanged
at 7.8 g/cm3 and 300 K, with the same FENDL-3.1d data and 256-site source bank.

Supporting end-to-end time starts before preparing each worker's XML and stops after the child
has exited and its bounded-command receipt is recorded. It includes actual
copy/export of existing XML, OS native-process launch, initialization, transport,
tallies, statepoint/summary output and process teardown. It excludes the later
raw-HDF5 audit and development/preflight accuracy tests. Process wall is measured
independently with a monotonic stopwatch around subprocess.run, not reconstructed
from histories/s or OpenMC active calculation rate.

| Tallies | Variant | Median preparation-to-result seconds / 1,000 histories | Median external process wall seconds |
|---|---|---:|---:|
| on | Original restricted offset | 18.662684 | 18.496480 |
| on | Accepted-cache same offset | **13.389543** | **13.233891** |
| on | Built-in circular ZTorus | 6.829973 | 6.664609 |
| off | Original restricted offset | 18.874457 | 18.724102 |
| off | Accepted-cache same offset | **13.757851** | **13.594015** |
| off | Built-in circular ZTorus | 6.799551 | 6.665971 |

Cache/original total-time fractions are 0.717450 (on) and 0.728914 (off).
Cache/native fractions are 1.960409 (on) and 2.023347 (off). The acceptance
condition from dispatch-005 originally used wall time; dispatch-007/008 supersedes
that wording with transport time <=1.25*built-in. SUMMARY.json's legacy
`native_80_percent_time_test` field is a wall-time observation, not the current
transport acceptance test. These are workload-specific elapsed-time observations;
native geometry is an approximate shape comparator and no physical equivalence
is implied. No throughput metric is used for the final acceptance report.

Individual times and all source/input/output identities are in
total-time-ab-005-02/{condition}/receipt.json and SUMMARY.json. There are only two
observations per condition, no confidence interval or portable ranking. Significant
Windows browser/Codex/ChatGPT/OneDrive/Defender activity and WSL shared-memory
observations were retained; CPU contention was not experimentally removed.
Order alternates original/cache/native across the two tally states/repetitions.
The tally-on observation being slightly faster overall than off does not mean
scoring has negative overhead; initialization/host variation dominates that delta.

## Observable phases; never sum nested timers

| Tallies | Variant | XML preparation/copy median s | Native initialization s | Transport s | Recorded statepoint-writing s |
|---|---|---:|---:|---:|---:|
| on | Original | 0.132310 | 6.095015 | 12.262501 | 0.034353 |
| on | Cache | 0.123142 | 6.446416 | 6.648469 | 0.030074 |
| on | Native | 0.133114 | 6.555626 | 0.006410 | 0.029898 |
| off | Original | 0.112344 | 6.194355 | 12.394476 | 0.013644 |
| off | Cache | 0.118622 | 6.720835 | 6.755644 | 0.013812 |
| off | Native | 0.098325 | 6.579427 | 0.005591 | 0.012176 |

PHASE_MEDIANS.json preserves the raw phase medians. Reading XS takes about
1.97–2.23 s and is **inside initialization**, not additional to it. Geometry
construction/compilation, loading coefficients and material preparation occur
inside initialization but have no separately observed timers: their individual
times are UNKNOWN. Transport contains event-level score work; the available
"accumulating tallies" timer is batch accumulation, not total scoring cost.
"simulation" and "active batches" include nested work and must not be added
to transport/output. Statepoint timers are sampled while the final file is still
being written, so the recorded output timer does not prove all finalization cost.

External process wall minus recorded native total has medians 0.068–0.120 s.
This residual includes launch/teardown and work outside the native timer snapshot;
it cannot be identified as pure launch overhead. Bookkeeping/command-receipt
overhead is recorded separately in each worker receipt. The one-off WSL/Python
dispatcher launch/import cost was not separately measured and is UNKNOWN;
it is not silently assigned zero or inferred from active rate.

Reusable coil/source/data fixtures were already local. XML reuse/export is timed
per worker; original HDF5 fixture creation/export time is historical and UNKNOWN
for this new comparison. There was **no software build** in this dispatch, so
no fresh build cost is claimed. Retained standalone DSO build receipts remain
historical, not a fresh compilation comparison. Per-run times above are not
amortized across multiple runs; any fixture/software development amortization
requires an explicit deployment scenario rather than deleting setup costs.

Native transport remains only roughly 6 ms. Total native process time lasts
about 6.7 s, supporting the requested total-elapsed sizing comparison; it does
not establish a precise native **transport-only** ratio or large-history scaling.
A production-sized strict-offset campaign is not admitted by these short bounded
workers. Extrapolating away initialization would not be a measured result.

## Accuracy gate, failures and crossings

Before timing, fresh original/cache adversarial and native entry/exit/sense/normal
workers pass. Both prefix modes replay all 160 frozen queries unchanged against
their retained accepted records, including all non-timing diagnostics/error
fields. Each variant/mode has zero frozen wrong-root/failure cases and **nine
unchanged normal gaps**. Restricted certificates remain the correctness service;
the old local solver's four independently observed wrong-root cases are not
reintroduced. Expected unresolved/budget controls in the adversarial suite remain
unresolved, rather than counted as misses or omitted successful work.

All twelve transport workers exit zero, have the required final statepoint and
complete counts, and have zero raw lost/unresolved/fatal diagnostics. Wrong-first-
root counts are not inferable from uninstrumented transport; the recorded zero
refers specifically to the frozen contract gate. No rate is computed after
dropping a failed/unresolved worker.

For both repetitions, original/cache XML hashes match exactly in each tally state.
The checker compares **both complete tally dataset sets**, then every raw value
and metadata dataset. Tally-on checks include all six energy bins and cell/material
scoring arrays: 64 sum/sum-square values per repetition, 128 total. They are
identical. Tally-off dataset sets/metadata also agree. This is sampled implementation
regression, not a proof of physical equivalence, statistical adequacy of sparse
bins or universal spatial-mesh compatibility. Native torus tally arrays are
retained descriptively and are not required to equal the different offset shape.

**Crossings per history: UNKNOWN / NOT_RECORDED** for all uninstrumented workers.
No boundary-event counter or particle-track bank was enabled. Distance-call counts,
flux or leakage do not supply that measurement. Any future full curved/configuration
comparison must include an independently reviewed compact event counter or
matching surface-current records in a separately admitted observation.

The first attempt, total-time-ab-005, stopped after a passing original adversarial
worker on a duplicate UTC logging keyword, **before any transport**. The runner
snapshot and failure are retained. After diagnosis, a separate explicit invocation
used total-time-ab-005-02; no output was overwritten and no automatic rerun was
embedded. All failures and leases remain in append-only ATTEMPTS.jsonl.

## Identity and selected next method

Root's previously accepted cache SOURCE is already integrated, SHA256
5f71bb5054f74c0e83815bcaf9a75f8509ff0ad59026ea4c551af245b20e6008. It was neither
reapplied nor edited by this dispatch. Production libopenmc remains original
f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6.
The experiment reuses source-identical complete original/cache DSOs, respectively
577dbee3d416b1e518fcad9dc403a26e38643918d3fee60d17a7ffb1f6789b54 and
b3f2aeea1b80c00b806b6bb96435e4e0acc3e7a6b94beaea565ccde733387e68, in fresh
processes using the independently reviewed -Bsymbolic-functions link structure.
No mixed live objects or partial helper interposition are introduced. It remains
an isolated experimental route; a coherent production library rebuild is NOT_RUN.

The next performance direction is the **old balanced span/shared-coil BVH
architecture with strict new hull bounds**, retaining exact built-in torus dispatch
only for genuinely exact circular definitions. BVH_SOURCE_PROPOSAL_005.md and its
single-file patch give a concrete immutable hierarchy for minimum/projection on
the same admitted constant-metric offset. It is uncompiled and unaccepted;
its speed/accuracy are NOT_RUN. The total-time block consumed this milestone's
execution; no second native campaign or build is launched automatically.

BUILTIN_CONTROL_PLAN_006.json records the current torus comparator plus missing
flat-ring, matched built-in 48-coil and nonaxisymmetric-plasma controls. DAGMC is
secondary. The historical 48-coil 2.45968 s result against DAGMC is not a built-in
48-torus total-time benchmark, and standardized 1 cm tubes are not 30x30 cm packs.
No approximate circle/rectangle is used to weaken custom geometry correctness.

All work was local, one CPU, 1 GiB per worker, explicit 60/90 s timeouts, atomic
exclusive campaign lease; existing capabilities only and zero acquisition. Fresh
host/RAM/drives/process and WSL environment/cache/source observations are retained.
The lease is released and no child remains. HEAD/branch and other owners' files
were preserved; there was no stage, commit, push, SSH, schedule or new chat.
