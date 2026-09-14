# Product 05 restart (PowerShell)

Use the current local product branch, not a remote checkout. Preserve 04 and all
older controls. These commands acquire no software. Recheck resources before
any rebuild. Output suffixes must be new; no overwritten evidence is required.

```powershell
$R = '/mnt/c/Users/joshu/OneDrive/Documents/ChatGPT/StellarCGS/stellarcsg-product-05'
$PY = '/opt/openmc-venv/bin/python'
git -C stellarcsg-product-05 status --short --branch
wsl -d OpenMC-Dev-D -- env "PYTHONPATH=$R/dev/stellarcsg/python" $PY -m pytest -q "$R/dev/stellarcsg/python/tests/test_one_period.py" "$R/dev/stellarcsg/python/tests/test_swept_exact_oracle.py"
wsl -d OpenMC-Dev-D -- $PY "$R/dev/stellarcsg/qualification/product05_model_probe.py" model-03
```

The last command compiles input data, runs the simple example and held-out
rejection, and launches at most 120 seconds of 16-history clipped exact-reference
diagnostic transport. It is NOT recovered-candidate or periodic qualification.
It binds the existing reference binary/library and local Windows H1 data.
Inspect `receipt.json`, `transport.stderr`, completion and tally dispositions;
the recorder may finish successfully while recording a failed wrapped process.
`product05_transport_summary.py` reduces the retained model-02 specifically;
change its output/input suffix deliberately for a new run. Do not run another
mesh comparison for these diagnostics.

To reproduce the rejected exclusion probe after resource review:

```powershell
wsl -d OpenMC-Dev-D -- $PY "$R/dev/stellarcsg/qualification/product05_probe.py" product05-cover-03
```

Expected controlled-bank outcome: 90 ROOT_FREE / 70 UNRESOLVED, not 160 passes.
No production library rebuild occurs. The baseline static library is linked
only to reuse fixture/HDF5 code; the probe does not call a distance solver.

For real hit-rich replay use the preserved `recovery04_measure.py` with the
exact lane/binary commands in `product05/real-replay-01/receipt.json`, replacing
only the output directory. Its new bank is `product05/real-bank/rays.csv`;
do not regenerate either frozen CSV during kernel tuning. One repetition was
used for stress evidence, not a seven-repetition performance claim.

Remaining numerical work is specified in PRODUCT_05_CONTRACT.md and the
checkpoint. Bounded alternatives are permitted immediately. Do not require
perfect old-spline qualification before investigating a better representation;
do require common correctness/fidelity gates before any promotion.
