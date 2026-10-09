# StellarCSG handoff recovery report

## Classification

The starting branch head
`9adb7c4bd8a97c88f4a4e614b80637d6043c202b` contained a working first-slice
C++ kernel, but both artifacts advertised as the verified later milestone were
truncated. This is a stale/corrupt handoff-artifact failure, not a failure of
the original standalone kernel.

The required milestone-only documents
`MILESTONE_PERIODIC_AXIS_OPENMC_ADAPTER_REPORT.md`,
`NORMAL_DISTANCE_LAYER_COMPILER.md`, `PAPER_REVIEW_AND_ADOPTION_NOTES.md`,
`openmc_adapter/INTEGRATION.md`, and
`openmc_adapter/openmc_periodic_spline.patch` were not recoverable from those
truncated blobs. They are not represented as reviewed or restored.

## Artifact observations

| Artifact | Declared bytes | Observed bytes | Declared SHA-256 | Observed SHA-256 |
|---|---:|---:|---|---|
| `periodic_axis_openmc_adapter_source.zip` | 100,273 | 15,008 | `5043bcd871b07067468ca9ba094e6da4b9fb2cc03f21f714248c71f1a9ecc44a` | `4800cfc48bb575835489c05b42e29c10ccac4a182987156f8b6e6fb30e2f5241` |
| `periodic_axis_openmc_adapter_milestone.patch` | 221,090 | 7,892 | `7f89f70568283868eeb91954c2aeae2fa207b4ccddffc7aa03daa284704fc922` | `5b41cb1bf0d0ff81da39d76552418a4fdf4d93f55bebeff71abdd3ca86989782` |

## Provenance-preserving recovery

Commit `913860056e3653b24b72b9fca4fe4245b7538c08` retains nine
`dev/stellarcsg/.materialize-v2/part-*` blobs. Concatenating and Base64-decoding
them produces a 73,624-byte gzip tarball with SHA-256
`35e89d84cf821d842a0cc42537c4b3fe1ae11a099a97f92c1043c79ac8e1e6ae`,
matching the workflow's preregistered value. GitHub Actions run `33297036204`
reported the archive `OK`, extracted it, validated its required files, and
failed only because `git diff --cached --check` found trailing spaces in
Markdown.

The exact recovery source was extracted over `dev/stellarcsg`. The corrupted
artifacts remain retained as negative evidence and are not used by builds.

## Validation after recovery

```text
GCC 14.2 Release standalone CTest: 2 passed, 0 failed
Python 3.12 pytest: 12 passed, 1 skipped
Skipped test: full OpenMC import unavailable because the existing Windows
Python environment lacks the endf package.
```

The earlier untouched kernel baseline also passed its sole CTest. Its requested
Python path was absent, and collection through the repository conftest stopped
on the same missing `endf` environment dependency.

This recovery restores the earlier runnable v2 prototype only. It does not
claim to restore the later periodic-axis bounded-solver milestone.
