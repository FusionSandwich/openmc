# Reproduce the third idea set

See [METHOD_LEDGER.md](../METHOD_LEDGER.md) for FT-007/008, every saved result,
development failure and limitation. Input text and actual incumbent bicubic
source are frozen under `attempts/0003-direct-fourier-algebraic-20261009/inputs`.

From `tools/fourier_torus_prototype`, using existing local Python/NumPy/SciPy:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python experiments/run_direct_trials.py --run-id run-003
```

Use a new `run-NNN`. Existing directories are refused before output writes.
Append registration and outcomes to `METHOD_EVENTS.jsonl`. Keep completed,
failed and superseded runs immutable. Run 001 preserves candidate loss on
later singular scalar refinements; run 002 corrects that narrow case and
strengthens provenance checks. Sample-grid singularities can still abort a
query, and oscillatory crossings can still be missed. Every result remains
UNRESOLVED, including empty searches and floating polynomial candidates.

The runner freezes seven sources, logs 29 combined controls, saves a 76-ray
bank, compares three actual incumbent bicubic resolutions with a three-mode
direct Fourier radius, and fits 96/384 local full quartic patches. Signed
normal-offset labels prevent zero-polynomial fits. Random holdouts and
interior midpoint seams are diagnostics, not complete surface bounds.

The Fourier target uses a geometric radial theta chart by construction.
Arbitrary raw VMEC coefficients need independent reparameterization. This
trial has no real WISTELL-D input, native build, acquisition, coil work,
transport run or accepted native speed result. The frozen comparator is the
Python radius evaluator in a common constant-axis wrapper; it is not a
matched measurement of the whole incumbent tracker.
