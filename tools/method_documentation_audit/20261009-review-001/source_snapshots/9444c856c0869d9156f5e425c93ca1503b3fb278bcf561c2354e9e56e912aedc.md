# Fourier torus prototype

This isolated, pure Python prototype tests the two ideas in the October 9
review packet. It is not wired into OpenMC and makes no transport speed claim.
Run it from this directory with:

```powershell
python run_tests.py
```

The only required runtime package is NumPy. `VmecBoundary.from_wout()` uses
SciPy's already-installed NetCDF reader; the tests construct synthetic
coefficients and do not read or copy a WISTELL dataset. No package was
installed and no native build or transport run was performed.

## Joshua's torus composition proposal

The four readings are kept distinct:

1. **Boolean solids:** union/intersection acts on complete torus volumes. For
   concentric tori sharing an axis, these operations remain axisymmetric and
   cannot reproduce a tube radius that varies with toroidal angle. This
   counterexample is limited to that primitive family; it does not rule out
   placed, trimmed, or otherwise generalized torus constructions.
2. **Weighted implicit sum:** define a boundary by `sum_i w_i F_i(x) = 0`.
   This creates a new implicit surface, generally with a ray equation more
   complicated than one torus quartic.
3. **Parametric displacement sum:** add Fourier displacement fields to a
   reference torus. `one_harmonic_radius()` reconstructs
   `a(phi) = a0 + epsilon*cos(N*phi)` exactly. The result still needs a
   coupled ray/surface solve; the summands are not independent torus crossings.
4. **Nonlinear coordinate map:** map a reference torus into the target. An
   exact inverse can preserve the surface, but physical straight rays generally
   become curved paths in mapped coordinates, with transformed lengths and
   normals to account for.

The prototype therefore demonstrates one exact parametric interpretation and
records why the other three do not inherit single-torus ray roots for free. It
does not claim to disprove the general proposal.

## VMEC reconstruction and torus residual

The boundary evaluator uses
`phase = xm*theta - xn*phi`; the `xn` array is consumed as stored in wout, as
it already includes `nfp`. It evaluates symmetric `rmnc/zmns` and optional
asymmetric `rmns/zmnc` coefficients, then converts metres to centimetres.
The synthetic tests distinguish the correct `xn` convention, check a field
period seam, and include nonzero asymmetric coefficients.

The initial fit uses the `(m,n)=(0,0)` major-radius coefficient and averages
the symmetric `(1,0)` R and Z minor-radius coefficients. For the fitted
axisymmetric torus, omitted/differing Fourier coefficients are bounded by the
sum of their absolute magnitudes. Combining the R and Z bounds gives a
pointwise Euclidean position bound at matching parameter coordinates. It does
not certify signed distance, inside/outside, normal error, ray intersections,
or an interval in physical space. Dense samples are a test of implementation,
not the proof; the proof is the coefficient triangle inequality.

## Torus candidates and refinement contract

`torus_ray_candidates()` forms the quartic obtained by squaring an elliptical
torus equation and filters its real roots against the unsquared implicit
surface. Floating polynomial roots are candidates only: repeated grazing
roots can be lost or perturbed, so an empty list never means `NO_HIT`.
Directions must be unit length so returned parameters are physical ray
distances.

`refine_ray_candidates()` accepts a partition of the full `[0, max_distance]`
ray range. `CERTIFIED_EXCLUDED` and `CERTIFIED_SINGLE_ROOT` windows must come
from sound external certificates. A sign-changing `CANDIDATE` remains
unresolved because it can contain multiple roots and bisection can converge to
a later one. A `CERTIFIED_SINGLE_ROOT` is accepted only if its endpoints
bracket a sign-changing root, and only after every earlier window is certified
excluded. Unknown or uncovered windows, tangencies, non-finite evaluations,
and coincident starts return `UNRESOLVED`. `NO_HIT` requires complete certified
coverage. This prototype does not yet generate these Fourier-boundary
certificates, prove conservative torus-to-boundary exclusion, compute
successor ownership, or solve a VMEC surface intersection globally.

The thin-chord and competing-root controls use direct Decimal equations with
60-digit precision as independent references. The test suite intentionally
does not use the existing spline solver as a completeness oracle.

## Evidence and cost status

`receipt.json` is emitted by `run_tests.py`. It contains hashes of the prototype
source and the reviewer packet manifest, plus runtime/test details. Test time
is recorded separately. WOUT loading, fit construction time, peak memory,
unloaded query throughput, native transport time and benchmark ratios remain
unmeasured. The current functional suite is too small to claim a performance
result.

## Feasibility snapshot

- **Original proposal:** FEASIBLE WITH SPECIFIED CHANGES for parametric Fourier
  displacement reconstruction; exact geometry is possible for the retained
  modes, but ray intersections remain general coupled surface queries.
  Boolean and implicit-sum readings are separate constructions with separate
  root costs; nonlinear maps require transformed-ray treatment.
- **Torus-assisted modification:** an analytic quartic can seed an actual
  boundary solve, but this prototype does not yet provide conservative
  residual-to-ray certificates or complete earliest-root exclusion. Its
  correctness status is therefore **UNRESOLVED** and it has no measured speed
  result.
- **Unsupported:** actual WISTELL coefficient ingestion, mode truncation
  policy, global/local atlas fitting, certified hit/miss queries, surface
  normals, Boolean ownership, OpenMC integration, and transport scoring.
