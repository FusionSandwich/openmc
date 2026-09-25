# StellarCSG GitHub savepoint

This savepoint supersedes the failed staged-materializer handoff with a complete, hash-locked source snapshot and patch for the tested periodic-axis/OpenMC-adapter milestone.

## Repository boundary

- Repository: `FusionSandwich/openmc`
- Branch: `codex/stellarcsg-native-csg-foundation-20260828`
- No pull request or draft pull request is part of this savepoint.
- The feature remains experimental and is not enabled in the root OpenMC build by this savepoint.

## Revalidation performed before this savepoint

```text
GCC Release standalone CTest: 3/3 passed
Python tests: 9/9 passed
```

The retained standalone benchmark compares the bounded patch-BVH path against the same kernel's broad reference search. It is not an end-to-end OpenMC or DAGMC speed result.

## Restore instructions

From a clean checkout of this branch:

```bash
python dev/stellarcsg/tools/restore_verified_milestone.py --force
cmake -S dev/stellarcsg -B build/stellarcsg-savepoint \
  -DCMAKE_BUILD_TYPE=Release -DSTELLARCSG_BUILD_TESTS=ON
cmake --build build/stellarcsg-savepoint --parallel
ctest --test-dir build/stellarcsg-savepoint --output-on-failure
PYTHONPATH=dev/stellarcsg/python python -m pytest -q dev/stellarcsg/tests/python
```

Then execute `dev/stellarcsg/docs/LOCAL_CODEX_COMPLETION_PROMPT.md`.

## Known remaining boundary

The next agent must apply and adapt the experimental adapter to the live OpenMC source, complete the full OpenMC and swept-coil integration, acquire and hash-lock the authoritative WISTELL-D inputs, execute fair built-in/native/DAGMC benchmarks, and retain actual histories-per-second results.
