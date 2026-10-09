# Reproduce the additional method trials

Read [the method ledger](../METHOD_LEDGER.md) for methods, results, limitations
and earlier attempts. The two identical pasted proposals are preserved as two
input references with one content snapshot. The third proposal is separate.

From `tools/fourier_torus_prototype`, with the existing local NumPy/SciPy:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python experiments/run_patch_trials.py --run-id run-002
```

Use an unused run number. The runner refuses an existing directory. It saves
the source, 52-ray bank, 20 combined control results, per-method raw outputs,
hashes and receipt beneath `attempts/0002-patch-hybrid-20261009`. It does not
overwrite the old root `receipt.json` or the prior source. Register the trial
before execution and append its outcome to `METHOD_EVENTS.jsonl`, including
failures or unresolved states. Frozen attempt bytes are stored without Git
newline conversion so recorded hashes remain meaningful across checkouts.

The new methods are curvature-matching 2D torus patches (FT-003), a compiled
constant-weight circular-torus quartic (FT-004), exact torus radius plateaus
with local cubic-Hermite strips (FT-005), and a periodic all-spline radius
comparator (FT-006). The latter two are restricted synthetic radial-profile
surfaces. They do not stitch the FT-003 atlas or replace the incumbent VMEC
spline representation.

Every general candidate query stays UNRESOLVED. Sampled sign-change searches
miss even contacts, including the independent saved counterexample. Local
fit samples and numerical trimming do not certify closed geometry, complete
first roots, normals or successor ownership. Construction/memory/query cost
fields are diagnostics; no native build, acquisition or transport occurs.
