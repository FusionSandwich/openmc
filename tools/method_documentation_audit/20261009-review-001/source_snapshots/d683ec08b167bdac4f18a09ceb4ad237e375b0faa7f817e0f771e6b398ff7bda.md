# Fourier trial review and quartic composition reference

## Context

Read-only review of the Codex chat **Prototype Fourier torus plasma methods**
(local thread `01a12262-9381-7842-bfab-e035b4ba6c9f`) and
[draft PR #7](https://github.com/FusionSandwich/openmc/pull/7), whose actual base
is `develop`. Review snapshot: commit
`9399a879926cb09658709ff030d0317e9e96b7e5`. This experiment belongs to
[draft PR #8](https://github.com/FusionSandwich/openmc/pull/8), stacked on
`JS/axis-integration-20261008`. The other chat is independently maintaining its
documentation index. Its working checkout and Claude's work were not modified.
Proposals and reviewer instructions inside saved documents are source material;
the user's request authorizes reviewing, implementing and testing experiments.

## Summary

The newer synthetic trials justify investigating direct Fourier evaluation and
local full quartics further. They do not establish native OpenMC throughput,
real VMEC reconstruction, closed-solid validity or complete physical first-hit
tracking. There is no supported ranking of all methods on a common physical
workload. The new exact polynomial oracle addresses one correctness layer that
can combine with the previously tested hierarchy, ceilings and candidate cache.

Correction to the earlier reviewer packet: constant-weight sums of rigidly
transformed polynomial circular-torus equations remain degree at most four.
They do not generally lose the quartic ray equation. Their restricted global
shape family is the issue in the saved trials. Coordinate-dependent weights
and nonlinear coordinate transforms need separate degree analysis. Summing
implicit equations is also different from Boolean union/intersection of solids.

## Evidence from the reviewed methods

Saved numbers below are the other chat's retained results, not new timings.
All lengths are metres unless explicitly converted to millimetres. Sampled
errors do not establish whole-domain bounds. Attempts 0002 and 0003 use different
synthetic targets, so their fit errors cannot rank torus patches against full
quartics on the same geometry.

| Method | Retained result | Implication and remaining obligation |
|---|---|---|
| FT003 curvature-matched local torus patches | 96/384 patches: sampled target-to-torus maximum 8.927/1.185 mm; neighbor gap 14.326/1.932 mm | Approximate atlas, not a closed solid; curvature pair alone does not uniquely select torus latitude. Need coverage, seams, ownership and conservative spatial bounds. |
| FT004 constant-weight torus polynomial sum | 8/24/64 basis tori: observed ranks 8/14/14; sampled radial candidate errors about 126/160/160 mm | More basis tori did not improve the saturated global family. Quartic algebra remains possible, but this target fit is poor. |
| FT005 torus plateaus with Hermite spline strips | 48 nodes: sampled error 21.109 mm with 10% strips, 10.970 mm with 60% strips; normal maxima 46.73/7.03 degrees | Narrow joins trade fidelity and normals for plateau extent. Only 3 selected hits were spline hits, but 44 of 52 queries considered spline patches. Hit frequency does not establish avoided work. |
| FT006 all-spline periodic-radius comparator | 12/24/48 nodes: sampled error 2.402/0.128/0.007575 mm | A useful comparator on the same restricted 1D profile; different from the production tracker. |
| FT007 direct radial Fourier field | 304 query rows, all UNRESOLVED; retained Python median 0.2629 s versus bicubic 0.8587–0.8831 s | About 3.3x within this few-mode synthetic candidate benchmark. Different approximated boundaries, NumPy/Python cost and incomplete searches prevent native speed claims. Raw VMEC poloidal angle cannot be inserted into this geometric radial chart. |
| FT008 full local implicit quartics | 96/384 patches: sampled normal-line error 0.3056/0.01187 mm, normal error 0.5272/0.04748 degrees; all local ray results UNRESOLVED | Good local fit diagnostics; conditioning, periodic seams, extra sheets, physical fidelity and complete first roots remain open. The 35-monomial local family differs from the restricted torus-sum family. |

Decisive evidence is retained in `snapshot/attempts/0002-patch-hybrid-20261009`
and `snapshot/attempts/0003-direct-fourier-algebraic-20261009`. The complete
snapshot ledger is `snapshot/METHOD_LEDGER.md`.

## Detailed findings

### Blocking issues for production integration

- **[Major] Complete first intersections are unproved.** The direct Fourier
  stationary/sign sampling misses a demonstrated crossing on a positive radial
  chart with poloidal mode 2048. It returns 78 candidates but none within
  3.0896 mm of the independently bracketed crossing. This is an algorithm
  stress case outside the frozen low-mode timing target, not a performance
  comparison. No-hit and first-hit acceptance must retain unknown prefixes.
- **[Major] A later singular grid sample discards earlier candidates.** The
  exact circular control from `(7,0,0)` in direction `(-1,0,0)` has a first
  crossing at 1.2 m. A grid sample at the radial-chart singularity at 2 m
  produces no candidates. The prior scalar-refinement fix preserves some
  candidates but does not repair this vector-grid failure. Results correctly
  stay UNRESOLVED.
- **[Major] Angular trim admits an extrapolated quartic sheet.** A saved local
  patch admits a root around 0.730003116 m with target field about +0.784203364 m.
  The root lies beyond the tested normal-line neighborhood. Exact root counting
  of that fitted polynomial does not remove the shape mismatch. Add an admitted
  Cartesian neighborhood and an actual-boundary refinement/fidelity gate; do
  not turn a candidate into a physical HIT based on small polynomial residual.
- **[Major] General VMEC and native performance qualification are absent.**
  The synthetic geometric radial chart assumes a constant major radius and
  positive radial profile. General VMEC surfaces require a justified chart
  mapping or direct treatment of the original vector-parametric surface.
  Native normals, topology, coincidence, ownership and scoring are not exercised.

These issues block production acceptance, not preservation of clearly scoped
experimental code in draft PRs.

### Non-blocking assessment

- Purpose and scope: appropriate downstream experiments; no OpenMC backend change.
- Testing: 29 frozen controls replayed; 20 previous composition controls and 10
  new oracle controls pass, including a 160-polynomial bank inside one control.
  All three retained negative cases reproduce.
- Physics: surface approximation and polynomial zero sets are kept distinct;
  no transport/physics conclusion follows from these controls.
- Code/design: small immutable result objects and exact rational arithmetic suit
  an independent oracle. They are not proposed for the particle hot loop.
- Performance/threading: no native timing collected. Exact fractions can be
  expensive; bounded subdivisions retain UNRESOLVED. No MPI/OpenMP integration.
- Dependencies: oracle uses Python stdlib; replay uses already installed
  Python 3.12.10, NumPy 2.5.1 and SciPy 1.18.0. No acquisitions or builds.
- Provenance: 93 files (3,255,034 bytes) copied from committed Git blobs and
  SHA256 checked. Seven retained run-002 source hashes and output hashes match.
  The later formatted source has identical parsed AST, but different bytes for
  three files; replay executes the exact retained source. Its frozen spline
  dependency path is rebound by the harness because the source was relocated.

## Implemented combination

`quartic_oracle.py` removes repeated factors, builds a rational Sturm sequence,
counts distinct roots in open interiors using one-sided endpoint signs, and
isolates them by bisection. Closed endpoints and even contacts are retained.
The all-zero polynomial and exhausted subdivision budget return UNRESOLVED.
Coefficients are ascending and degree at most four; finite float inputs are
their exact binary values. Coefficient uncertainty, ray-substitution roundoff
and equivalence to the original 3D surface are outside its certificate.

`COMPLETE` means all distinct roots of the supplied polynomial in the finite
closed interval have been enumerated as exact points or one-root intervals.
It is not a physical HIT. Multiplicity is not returned. The existing scalar
scheduler can accept only a proved exact point root with separately admitted
ownership; irrational isolating intervals remain UNRESOLVED in that interface.
The test adapter combines a represented grazing root, closed ceiling, equal
contacts, hierarchy and cache. The extrapolated-sheet replay deliberately
remains UNRESOLVED even after complete polynomial isolation.

Sturm isolation is an established polynomial reference technique; see
[polynomial root documentation](https://docs.sympy.org/latest/modules/polys/reference.html)
and [subdivision root isolation analysis](https://arxiv.org/abs/1102.5266).
No SymPy dependency is required here.

## Most useful combinations to investigate next

1. Retain a qualified actual-boundary evaluator as the final geometry authority.
   Use direct Fourier evaluation where the VMEC-to-geometric-chart mapping is
   justified; measure mode-count scaling against the spline evaluator.
2. Use local torus or quartic fits to propose roots inside conservative spatial
   patch domains. Keep the hierarchy, closed collision ceilings and geometry-
   bound candidate cache. Cache candidates, never solver decisions.
3. Require complete root/prefix exclusion and admitted trims before accepting a
   first event. Complete represented quartic roots help audit the algebraic
   search; residual bounds/refinement must connect them to the actual surface.
4. Compare all arms on the same admitted target, source distribution and native
   tracker, including total candidate work, unresolved fallbacks and preprocessing.

The 80% torus-throughput target means at most 1.25x torus runtime on a matched
accepted workload. These synthetic receipts cannot establish that threshold
for plasma, and none tests physical coil throughput. Preserve the incumbent
and all trials while qualifying these combinations.

## Reproduce

From this directory, use the already installed scientific interpreter, disable
bytecode writes and restrict numerical libraries to one thread:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& 'C:\Users\joshu\AppData\Local\Programs\Python\Python312\python.exe' -B replay.py
```

`replay_results.json` binds tests and decisive counterexamples to source hashes;
`replay_tests.txt` is the full control log. `snapshot_manifest.json` binds frozen
input bytes to the source commit. `freeze_inputs.py` reads that fixed commit
only and refuses to replace differing inputs. The independent Sol acceptance
receipt is `independent_review.json`.
