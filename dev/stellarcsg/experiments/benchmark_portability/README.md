# Portable benchmark receipts — experimental, default OFF

Scope: the `benchmark-portability / initial-20260915-001` dispatch at OpenMC
commit `c08eea92ca3fb63eb8adbf44cfb4ea8612639e30`. This directory is additive;
it does not modify a kernel, frozen evidence, CMake defaults, or production APIs.
No package installation, compilation, mesh acquisition, SSH, Bateman job, WISTELL
replay, or transport launch is part of these tools. See `MATCHED_PROTOCOL.md`.

## Run the fixtures

Use an already audited environment. Python 3.11+ and its standard library are
sufficient. Execution has been tested on Linux/Python 3.13.5. The runner requires
POSIX process groups and CPU affinity; an unavailable capability blocks execution
rather than silently weakening it. Native Windows execution is not qualified.
No C++ analytic control or production geometry executable was built or run in
this dispatch. The new fixtures are exact-rational sphere/slab controls, not
native OpenMC ZTorus, spline-torus, or WISTELL performance measurements.

From the repository root, choose output directories that do not exist:

```sh
D=dev/stellarcsg/experiments/benchmark_portability
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 "$D/test_portability.py"
python3 "$D/portable_bench.py" discover
python3 "$D/make_fixture_plan.py" mock-plan --repetitions 3
python3 "$D/portable_bench.py" run --enable-experiment --plan mock-plan/plan.json --output mock-run
python3 "$D/portable_bench.py" validate mock-run/receipt.json
python3 "$D/make_fixture_plan.py" diagnostic-plan --repetitions 3 --mode diagnostic
python3 "$D/portable_bench.py" run --enable-experiment --plan diagnostic-plan/plan.json --output diagnostic-run
python3 "$D/runtime_probe.py" --output local-runtime.json
python3 "$D/gate_validator.py" "$D/matched_readiness.blocked.json"
```

The last command deliberately exits **2**: current readiness is BLOCKED.
Execution without `--enable-experiment` also fails closed. No transport launcher
exists. On a restart, use a new output directory; completed receipts and raw
logs are never overwritten. Input snapshots make receipts relocatable.

### Exit and status contract

| Code | Meaning |
|---|---|
| 0 | Children and validated candidate records passed. Performance can still be INCOMPLETE. |
| 1 | A child failed or a validated record reported failure. The failed attempt remains recorded. |
| 2 | Invalid input/receipt or explicit BLOCKED result/capability. |
| 3 | `run --require-native-control` was requested, but performance comparison is INCOMPLETE. |

The JSON result always separates execution, performance, and transport status.
An intact receipt can have `receipt_integrity=VALID` and `execution_status=FAIL`.
Integrity is not scientific qualification. Logs and journals are retained even
for nonzero exits, timeout, signal, output cap, or invalid JSON. A killed child
cannot be converted into a successful sample merely because it emitted JSON.

## Plan and child contract

`make_fixture_plan.py` provides an executable, hash-bound example; `check_plan`
and `analyze_log` in `portable_bench.py` are the normative validators. Plans use
`stellarcsg.portable-benchmark/v1`, specify primary/diagnostic mode, timing origin,
repetitions, timeout, stream bound, artifacts, and named lanes. Each artifact has
a relative path and SHA256. Duplicate names, unbound Python scripts, NaN/Infinity,
unknown fields, invalid domains, and repeated input tuples are rejected.
Commands are argv arrays, never shell strings. Whole-argument placeholders bind
`{python}`, `{repeat}`, or named artifacts. Inputs are copied into a new run;
child binaries are hashed before and after execution. The original frozen files
are not rewritten. A binary/script manifest is not a transitive dependency lock;
additional linked/input dependencies must also be recorded for native qualification.

Each query has a stable ID, declared geometry domain, origin, direction, origin
suppression flag, and optionally exact fixture expectations. Uniqueness is tested
on numeric geometry/query inputs, not ID/category labels. Direction zero and
nonfinite coordinates are invalid. Declared-domain validation is schema checking,
**not** geometric admissibility or physical-fidelity certification.

The portable child emits one JSON query per bank ID and one final summary.
It separately reports:

- Candidate state PASS/FAIL/BLOCKED, result HIT/MISS/UNRESOLVED, distance, and reason.
- Optional reference state and strength (`none`, `sampled`, `exact_oracle`).
- Distance/classification/normal times and the actual point inputs for the latter two.
- Candidate/Newton counts, recovery/fallback counts and times, allocations/bytes;
  unavailable fields are explicit nulls. Setup, warmup, and peak memory are separate.

A reference lane's **candidate authority** is distinct from the optional second
reference solve. In particular, `exact_reference` candidate results survive an
optional legacy `SKIPPED`. Authority labels require external provenance; a label
or finite-bank agreement is not proof that an implementation is an exact oracle.
Cross-lane comparisons preserve reference BLOCKED reasons and report nonzero
float-distance differences without silently imposing/inflating a tolerance.

`recovery04_jsonl` also parses the pinned harness format, including its compact
geometry/hash BLOCKED record. The original CSV must have 160 distinct queries.
This adapter is tested with synthetic compatibility logs, not a new WISTELL run.
The harness does not serialize classification/normal point banks, so their
unique-bank qualification stays unavailable; raw per-repeat means are retained,
but qualified primary aggregates/ratios for those metrics are null. Its optional
legacy `distance_reference` is treated as sampled, independently of the candidate
lane's declared authority. FNV coefficient IDs are never passed off as SHA256.

## Metrics and comparisons

A cold distance result is the median over repetitions of **complete unique-bank
means**, not the median single-query time. Pooled per-query median/P95/P99 use
linear interpolation at `(n-1)*p` (type 7). Repeat min/max, sample standard deviation,
coefficient of variation, per-repeat means, and available counts remain explicit.
A failed, BLOCKED, missing, or otherwise incomplete bank has no survivor-only
primary mean. Classification and normal require their own unique input points;
unique rays alone do not establish point-bank uniqueness.

Instrumented counters and recovery/fallback time are forbidden in primary runs.
Use a separate diagnostic run. Count fraction means affected calls / distance
calls; time fraction means corresponding measured time / measured distance time.
Unavailable instrumentation is null, not zero. Setup/warmup are not subtracted
from wall time to manufacture an unmeasured kernel time. Fresh processes avoid
in-process repeated-query cache reuse; this is **not** a claim of cold CPU caches,
OS page caches, or uncached filesystem inputs. Per-call timer overhead is included.

Native OpenMC CSG ZTorus must be measured in the **same receipt/session/environment**
as each candidate and recovered-old lane. A native lane requires measured timing,
compiler metadata, binary hash, and hash-bound source/binary review metadata.
The structured review is an external assertion, not an automatically generated
proof. Geometry cost ratios are candidate ns/query / ZTorus ns/query. Transport
throughput ratios would be candidate histories/s / ZTorus histories/s, but all
transport fields are null here. Unlike banks/geometries/point inputs yield only
`SENTINEL_COST_RATIO`, never a matched-fidelity speedup. Repeat variability is
reported with paired-repeat ratios where available.

A missing native lane leaves native ratios null and performance INCOMPLETE.
The deterministic mock cannot impersonate native ZTorus. Its synthetic timings
and ratio tests are arithmetic/receipt fixtures, **not** performance evidence.
Old-fast ratios retain the 1.25x preferred / 2x temporary cost guardrails; the
latter additionally requires an independently demonstrated correctness fix.
Neither cost threshold promotes a numerically unqualified method.

## Limits, provenance, and review

Receipts rehash snapshots and raw logs, bind argv/session/journals, and recompute
statistics/status/ratios. They are unsigned local consistency records, not a
third-party attestation. Moved receipts do not require or execute original paths;
original executable identity is the recorded pre/post hash, not a later rehash.
Interrupted runs may leave journals without a final receipt; those are incomplete,
not valid successful runs. Process-group cleanup covers descendants remaining in
the group; this runner is not a sandbox for malicious executables that escape it.

The read-only runtime collector never executes the target or invokes `ldd`.
ELF metadata, build records, and optional already-running local PID maps are
collected as evidence. Backend identification remains UNVERIFIED until active
code-path and binary-linked/static provenance are reviewed. Package versions
cannot be inferred from a build ID or filename. No live Bateman inspection occurs.

See `SOURCE_READS.json` for pinned files inspected, `test_portability.py` for the
regression suite, and the delivery's `RUN_REPORT.md` for actual results and limits.
