# Independent geometry admission and completeness audit

**Dispatch:** StellarCSG / certification-audit / initial-20260915-001
**Decision:** NOT QUALIFIED. This audit supplies source findings and focused counterexamples; it does not certify a replacement solver.
**Scientific/code baseline:** `c08eea92ca3fb63eb8adbf44cfb4ea8612639e30`, branch `JS/stellarcsg-root-repair-20260915-07`.
**Archived exact-reference control, inspected separately:** `5ed327ade33b31ecdb5e3b4b4111c55f321991fd`.

## 1. Access, ownership, and execution truth

The pinned brief title is **Independent geometry admission and completeness audit**. Its exclusions are binding: no new production solver, production-kernel changes, or rerun of the ongoing failed transport case. This patch adds only this review, focused audit tests, a small retained-input fixture, a source manifest, and an offline runner under `dev/stellarcsg/experiments/certification_audit/`. No CMake integration, enabled experimental feature, publication, PR, protected reference change, remote job, SSH, or desktop access occurred.

The GitHub connector provided pinned source and report reads. Bash, Python 3.13.5, GCC 14.2.0 and Clang 17.0.0 executed locally in the ChatGPT container. Direct container source retrieval failed DNS; web access was unavailable. Two small headers were transferred from connector content and independently checked against their Git blob hashes. There was **no complete clone, full OpenMC build, full geometry-class execution, strict/stress-bank replay, or transport run**.

The local branch is `JS/certification-audit-20260915-local`. Its initial commit `04158c3a9f5173e7d30b0c893d2d830e2501637c` is a **synthetic two-header snapshot**, not the upstream commit or its history. Source provenance is established by the pinned connector reads and exact header blob hashes, not by equating these commits.

Before acquisition/builds, recorded audits covered RAM/cgroup limits, system/target/data free space, significant processes, tools, Python/Conda environments, caches, and a bounded checkout inventory. Initially the cgroup RAM limit was 4 GiB, available host RAM about 4.85 GiB, and all relevant volumes shared an overlay with about 29.8 GiB free. The CPU was an AMD EPYC 9V74 virtual machine, affinity 0–4; actual tests were restricted to CPU 0. HDF5 1.14.5 and GMP 6.3.0 were installed but were not needed. OpenMC and Conda were absent. Nuclear data was neither used nor acquired; no exhaustive remote/data inventory is claimed.

The acquisition plan capped source at 8 MiB, generated artifacts at 8 MiB, and builds at 16 MiB. Only 13,142 bytes of exact pinned header source were materialized. Other source was read through the connector. All local files are confined to the new audit directory; rollback is deletion of that directory. The runner reacquires nothing and repeats the resource audit before compiling. Unknown required observations block its builds.

## 2. Findings at the pinned source

Source abbreviations and exact blob identities are in `source_review.json`. `CS` means `dev/stellarcsg/src/compiled_swept_surface.cpp` at the baseline; `SB` means `src/swept_span_bounds.hpp` in that subtree.

| ID | Severity | Source location | Finding and required disposition |
|---|---|---|---|
| A1 | Blocking | CS 62–83; 254–414 | Constructor validation is not whole-span admission. Frame construction normalizes the center derivative and projected supplied normal; derivative/frame/curvature/separation obligations are not enforced here. Admit entire spans or return an explicit unsupported state. |
| A2 | Blocking | SB 99–179; CS 272–314, 416–513; `vector.hpp` 75–112 | Ideal polynomial bounds do not automatically enclose floating Horner, coordinate remapping, normalization, cross products, or trigonometric evaluation. A direct two-compiler counterexample below makes the evaluated frame escape a `certain` ideal bound. |
| A3 | Blocking | CS 1236–1254 | `if (!solved && proxy_count != 0)` drops retained zero-proxy spans and treats any successful seed as enough to avoid unresolved-span work. Neither condition proves an earlier prefix root-free. |
| A4 | Blocking | CS 1284–1347 | Eight-segment sign scanning cannot establish completeness. No sign change leaves no general unresolved status; final `best_t == infinity` can become ordinary no-hit. The existing `100 * absolute_f_tolerance` fallback gate is also not a root certificate. |
| A5 | Blocking | CS 816–825, 938–1049, 1061–1115; archived reference 525–690 | Origin association is different from a positive-distance cutoff. Small Newton/projected residuals and an estimated Newton correction do not provide existence, uniqueness, or a longitudinal enclosure. The exact reference's strict-positive convention must not be replaced silently by closed-domain contact semantics. |
| A6 | Important | CS 1168–1217; `vector.hpp` 75–112 | Proxy quadratics assume an exactly unit direction after rounded normalization and have cancellation-prone discriminants. Finite direction rescalings also overflow/underflow the naïve norm. Treat failed proxy generation as a lead failure, never root exclusion. |
| A7 | Important | CS 213–251 | Sample-based recognition of an “exact torus” is not polynomial identity. A numerical inter-knot mismatch is reproduced below. This optimization needs an explicit approximation/identity contract. |
| A8 | Important | `tests/test_swept_seed_regression.cpp` 1–52; CS 1334–1347 | The near-entry test has only an upper distance bound; it can pass an incorrectly early hit. The a08 test expects an unresolved exception, not the correct tangent result. Diagnostic labels such as `general_swept_certified` and counts alone do not constitute certificates. |

These findings apply to the inspected repair kernel, not to an uninspected future patch. The full-pinned-source control-flow gap supports “fast repairs remain incomplete.” Historical isolated-acceptance counts—2 strict wrong, 12 stress wrong plus 3 stress BLOCKED, and 2 admitted retained failures—are preserved as **reported checkpoint results**, not rerun measurements from this chat.

### A1: precise admission obligations

Separate three objects: the exact spline specified by stored binary64 controls, the exact polynomial using rounded compiled power coefficients, and the actual floating evaluation. The union of bounds for the first two objects does not bound every operation of the third.

Whole-span admission needs finite inputs and representable parameter transforms, positive radius bounds, and certified lower bounds for `||C'(u)||` and `||C'(u) × N_supplied(u)||`. Nonzero values at knots or a sample grid are insufficient. The local counterexamples `C(u)=((u-5/128)^2,0,0)` and `N_supplied(u)=(1,u-5/128,0)` with `C(u)=(u,0,0)` respectively hide derivative and frame singularities between all 65 grid points `i/64`. These are exact analytic span examples, not claims that a complete production object containing them was instantiated.

For the archived constant-circular-tube reference, additional sufficient conditions are local `r κ < 1` and separation excluding short doubly-critical chords. These are domain restrictions for that proof, not a universal physical-validity test. A varying elliptical sweep needs its own embedding/classification contract. A global closest-center classification method also requires a justified minimization/ownership argument: the fixed golden-section/Newton iterations in CS 571–633 do not provide one for arbitrary admitted cubic spans.

### A2: what the outward operations do establish

Under the stated supported binary64 environment, elementary operation followed by an outward adjacent representable value encloses the corresponding exact arithmetic operation. Propagating such intervals through the B-spline/power-to-Bernstein conversions encloses their exact coefficients. The Bernstein convex-hull property then gives ideal polynomial bounds. With valid supplied boxes and radii, the outward slab intersection and strictly positive center-distance lower bound support exclusion. Overflow/unsupported conditions returning unknown, and tangent intervals remaining retained, are appropriate.

That is a **conditional argument**, not an end-to-end certificate. It does not cover the actual frame's normalization error, subnormal loss in squared norms, rounding of span coordinates, Horner error, approximate trigonometric results, or rounding a ray into a different normalized direction. A rigorous evaluator needs an explicit error enclosure for each relevant operation and nonvanishing, numerically safe denominator bounds. Unknown evaluations must retain or block a query; increasing the geometric tolerance is not the repair.

**Measured local-span counterexample:** let `δ=2^-537`, `C(u)=(δu,δu/2,0)`, supplied normal `(0,0,1)`, and major radius 1. Minor radius can be 1/2 to avoid a constant-circular cross section. The exact tangent is regular and independent of the supplied normal. In the pinned vector helper, the exact squared speed `5*2^-1076` rounds to `2^-1074`; normalization produces `(1,1/2,0)`, whose squared norm is 1.25. Reproducing the pinned frame operations gives a normal with z component approximately `sqrt(1.25)`.

Both GCC and Clang measured `supported_binary64=true`, `bounds.certain=true`, evaluated z `1.1180339887498949`, and box upper z `1.0000000000000009`. Thus the actual evaluated point lies outside the ideal radius-expanded bound. The actual headers ran unchanged; the few frame statements are explicitly mirrored from CS, not an invocation of the entire production class. This is a local numerical-enclosure counterexample, not a physical WISTELL-D case or a whole-solver false-hit measurement.

### A3–A5: the nearest-root contract

Use physical distance `s=λ||d||` for the original stored ray `o+λd`; distinguish it from ray parameter λ. Ordinary archived-reference queries omit exact `s=0` and retain every strictly positive root. A contact-aware closed-domain API may report zero separately, but that is not the same convention. In the archived exact reference, coincidence instead asserts a uniquely associated origin root, with missing or ambiguous association explicitly unresolved.

The pinned strict record a06 is **positive**: its recorded distance is `8.3266726846886741e-17`, whose binary64 value is `3/2^55`. It is not an exact-zero contact that may simply be dropped or relabeled. The archived a08 reference returns distance 2. These are inspected historical records, not new root solves.

A blanket push can delete a distinct next boundary: `F(s)=s(s-2^-21)` has an origin root and a next root `2^-21`; discarding all `s <= 2^-20` loses that next root. This analytic example does not prescribe OpenMC's entire crossing API; it proves that a distance push is not a certificate of unique origin association.

The required invariant is a ledger of every admitted candidate region. Finding a root resolves that root, **not** the entire span or its earlier prefix. A zero proxy count resolves nothing unless a separate conservative predicate excluded the domain. Before returning a nearest-root enclosure `[L,U]`, every region capable of an earlier root must be excluded or resolved into the certified candidate set. Exhausted budgets, retained intervals, degeneracies, and unresolved ties remain explicit. An ordinary no-hit requires exclusion of the complete eligible domain, not absence of successful leads.

Even roots and close pairs defeat sign-only scanning: `(s-3/16)^2` has an exact root, and `(s-3/16)^2-2^-60` has two simple roots, yet all nine samples `i/8` are strictly positive. Multiplying the first polynomial by `(s-3/4)` makes a later crossing visible while leaving an earlier tangent undiscovered. A separate factored cubic puts two earlier simple roots in one scan cell before a later crossing. These are counterexamples to an inference from samples, not substitutes for a geometry solver.

Even a true sign bracket proves existence only for the continuous function whose signs are established. Here `evaluate()` includes approximate closest-center work, and its floating point signs have no supplied enclosure connecting them to the authoritative surface. Nor does a bracket alone establish uniqueness or absence of an earlier root. `(s-3/16)^2+2^-80` additionally gives an arbitrarily small positive residual with no root anywhere.

## 3. Retained BLOCKED reason: reproduced, not weakened

The retained file contains shape-2 ray dispositions with indices 0–127 blocked at `geometry_certificate`; the checkpoint reports 128 such states. These are not evidence of 128 separately invalid physical geometries. The exact string is preserved:

```
STELLARCSG_UNRESOLVED_CIRCULAR_TUBE: embedded circular-tube separation certificate failed
```

The fixture contains the 16 shape-2 binary64 control triples and radius 1/4 from retained-reference line 259. The Python audit reproduces **only** the archived exact source's separation predicate using rational arithmetic. The first failing pair in its traversal is `(0,15)`: squared box separation is 0, versus the required `4r² = 1/4`. The independent tangent-cone dot lower bound is

```
-24233699620915614707944923662466375 /
 1298074214633706907132624082305024
= approximately -18.668963105282796
```

The two copies of the cone are independent intervals: this is not a negative squared tangent norm. Their component dependency loss makes the sufficient acute-tangent condition fail. The separation certificate therefore cannot exclude the problematic close-chord configurations. Actual self-intersection is **UNRESOLVED**, not established. The full reference admission sequence, curvature stage, and ray solver were not rerun. No block reason was replaced by PASS or by physical invalidity.

## 4. Bernstein and Bezier allegations

**Bernstein 32/160 stress errors:** UNVERIFIED. No exact source/patch and raw results for that newer experiment were supplied or located in the inspected pinned source subtree. The baseline does not contain its `experiments` directory. The archived GMP/Bernstein reference is a different implementation and must not be substituted for the newer lane. Positive/negative coefficient enclosures can exclude roots over a complete domain; zero-containing coefficients, identically zero polynomials, even roots, or budget exhaustion cannot be declared no-hit from a sampled fallback. The analytic examples demonstrate this mechanism, but do not reproduce or endorse the reported count 32.

**New Bezier accepted-t claim:** UNVERIFIED AS AN IMPLEMENTATION FINDING. Its exact experiment artifact was not inspected. The mathematical concern is established independently, and the pinned general swept acceptance has an analogous residual-only path at CS 1061–1115. A plane, representable by degree elevation as a bicubic patch, suffices:

```
S(u,v) = (2^-40 (u-1/4), v, u),       ray = (0,0,s).
```

The exact hit is `u=s=1/4`. At candidate `u=3/4,v=0`, projected residual is `2^-41 = 4.547473508864641e-13` while longitudinal error is **1/2**. The patch is regular; the transverse map is ill-conditioned. Small transverse residual or a sampled conversion-error estimate therefore does not certify s. Require a validated root-containing parameter box, an outward longitudinal image bound, appropriate existence/uniqueness or multiplicity handling, and completion of earlier candidate regions. This audit does not implement that solver or approve an unseen implementation.

## 5. Additional focused observations and test interpretation

An endpoint-sphere proxy counterexample uses origin `(2^30,2^30,0)`, radius 1, and the stored direction obtained by `normalized(-1,-1,0)`. The exact stored ray passes through the sphere center, so its exact quadratic has positive discriminant. Both compilers produced **-2048** from the pinned endpoint-proxy arithmetic. Other proxy seeds could rescue a full query; no complete zero-proxy solver miss is claimed. It establishes that this proxy calculation cannot itself justify exclusion.

Actual vector-helper execution rejects the finite nonzero direction scales `2^-600` and `2^600` because its naïve norm underflows or overflows. Exact signed-permutation/dyadic-translation fixtures with moderate direction scales 1/4, 1, 4 verify that physical distance stays 1 while λ changes to 4, 1, 1/4. Adding `2^54` to binary64 points initially one unit apart collapses their stored separation: arbitrary rounded rigid transformations are not exact preservation of the input geometry. Transform receipts must distinguish mathematical invariance from newly rounded data.

The circular 64-control fixture passes equal-radius knot sampling but differs at an inter-knot midpoint by about `1.2105612139379218e-6` coordinate units. Analytically a nonconstant real polynomial curve segment cannot lie exactly on a circle: the highest-degree coefficient of its squared radius is a positive sum of squares. Thus a polynomial spline circle fixture is not made an exact torus by finite sampling.

The existing bounds test has assertions deliberately active in Release. Its cancellation, slab, underflow/overflow, and tangent-retention examples are useful, but do not test complete evaluated frames or nearest-root completeness. This audit runs six focused helper checks, not that entire CTest target. The near-entry test's predicate accepts a fabricated positive distance `1e-12` for expected `.002`; the proposed two-sided error check rejects it. This is a test-predicate witness, not fabricated kernel output. Keep the old negative a08 evidence: its expected exception is a safety regression, not a successful tangent solver test.

## 6. Results, performance, and restart

The final restart receipt records **16 Python analytic/predicate witnesses and controls**, plus both GCC and Clang C++ probes. Each compiler probe checks the frame escape, two extreme-scale rejections, six ideal-bounds examples, and the negative proxy discriminant. All final subprocesses exited 0 without compiler diagnostics. Exit 0 means the specified witnesses reproduced; it does **not** mean the geometry kernel passed qualification. Initial 15-case results and source versions are retained separately from the added test-predicate witness.

No geometry-kernel or transport performance was measured. Native OpenMC ZTorus and recovered-old were not run. All distance/classification/normal costs, transport throughput, candidate/ZTorus ratios, old-fast ratios, variability, allocations, and fallback timing are **null / NOT_MEASURED**. The comparison is **INCOMPLETE**, not waived. Repeated correctness probes are not a performance campaign. No historical absolute ns/query was compared across machines.

The offline restart command, from the root of the supplied snapshot or an appropriate pinned checkout after applying the patch, is:

```bash
python dev/stellarcsg/experiments/certification_audit/run_audit.py \
  --output /tmp/stellarcsg-certification-audit-NEW
```

Use a new output path; the runner refuses overwrites. It checks the two expected header hashes, captures a fresh environment audit, restricts affinity to one available CPU, sets numerical-library threads to 1, and limits each compiler/test child to 512 MiB address space, 25 CPU seconds, bounded wall time, and 16 MiB individual file size. It performs no acquisition or transport. Existing g++ and clang++ are required for a complete two-compiler run. Full commands, versions, stdout/stderr, source hashes, binary hashes, and return codes are in `results.json`. Unsupported/missing observations or a future changed fixture are explicit blockers/failures, not silent success.

The measured final commands used C++17, `-O2 -fno-fast-math -ffp-contract=off -Wall -Wextra -pedantic`, CPU 0, and `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=NUMEXPR_NUM_THREADS=1`. Binary SHA256 values were:

```
GCC   e7234a38420e348303e3f04be4e4b80c4865860c2f112d7fd17a3a2381137737
Clang f02f5d1718d1c1af2e0c14fea4c83ffc0c93bbac268dd08944eb7c60f639042d
```

For an already available full checkout, verify the baseline and isolate the patch before editing:

```bash
test "$(git rev-parse HEAD)" = c08eea92ca3fb63eb8adbf44cfb4ea8612639e30
git switch -c JS/certification-audit-review-20260915
git apply --check /path/to/stellarcsg-certification-audit-20260915.patch
git apply /path/to/stellarcsg-certification-audit-20260915.patch
python dev/stellarcsg/experiments/certification_audit/run_audit.py \
  --output /tmp/stellarcsg-certification-audit-NEW
```

These are restart instructions, not a claim that a full checkout was available here. No additional clone or dependency acquisition is authorized by this review.

The next solver-owner gates are explicit whole-span admission, actual-evaluation enclosures, origin-associated-root semantics, even/near-multiple-root handling, and the complete earlier-prefix ledger. Independent review of those future changes remains pending. Whole-machine, periodic assembly, transport, and mesh promotion are still gated.

Finally, the supplied provenance correction remains intact: raw WISTELL input identity does not turn the current 1 cm circular/no-blanket diagnostic into the physical winding pack, accepted 40 cm-offset assembly, or continuous 30 cm winding-surface model. This audit makes no physical-clearance, winding-pack fidelity, or mesh-superiority claim.
