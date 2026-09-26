# Exact-control offset baseline: verified results and limits

Baseline implementation: `3f8703db2`, based on pinned
`63359cb83d36b419a7e9ba60c45f867073703c21`. The original checkpoint checkout and
branch were preserved. The new `exact_control_offset` representation is explicit
in C++, Python, XML, HDF5 and query receipts. Legacy geometry remains the default.

## Achieved

- Native OpenMC member-2 shaped seam: distance **16.000000000001382 cm**,
  outward normal and both directional sense checks pass. An independent exact
  rational support/witness proof bounds its distance error by
  **1.4577968462011388e-12 cm**. This is an actual `SurfaceSweptSpline` call,
  not only a standalone kernel result.
- Unchanged frozen bank: **69 hits, 91 no-hits, zero unresolved and zero wrong
  scalar results** for this explicit representation. All 160 queries are
  independently certified at **1e-11 cm**: 158 exact rational Bernstein/ball
  proofs and two exact support contact proofs. Every earlier eligible ray
  interval is excluded, including the interior-origin cases; no-hit results
  exclude the whole ray. The frozen CSV SHA-256 remains
  `fc9da0be5eb66e3d56649a8d709db16f9b096c7767a565c57d5488bd19430723`.
- The two contact roots are treated as even contacts, not misses or residual
  guesses. a06 is exactly `3/2^55` cm from its origin; a08 is exactly
  `2+3/2^55` cm. The former stays positive despite being smaller than the query
  tolerance. A generic exact support predicate admits them; it contains no
  bank-ID dispatch.
- Adversarial controls pass: exact minimum enclosure, curved seam crossing,
  zero-contact policy, coincident inward/outward handling, tangent fallback,
  direction scaling, exhaustion, invalid options, zero/competing normal rejection,
  unsupported arithmetic and degenerate geometry rejection, support axis/sign
  permutations and tiny positive contacts, and exact dyadic carry/cancellation.
  Legacy C++ tests pass. Eight comparator controls and three representation
  round-trip/rejection tests pass.

## Decisive evidence

| Evidence | What it establishes |
|---|---|
| `build-receipt-11.json`, build11/native-build02 logs | Successful bounded local Release builds, unchanged compiled input hashes and produced executable/library hashes |
| `native-probe-02.jsonl` | Native surface registration, seam distance, normal and directional sense |
| `frozen-offset-03/receipt.json` and `candidate.jsonl` | All 160 actual results, unchanged execution inputs, exported normalized directions and cost counters |
| `independent-bank-qualified-01.json` | Bound aggregate of 158 exact prefix/ball certificates and two independently regenerated support proofs at 1e-11 cm |
| `independent-bank-tight-01/` | Per-query exact prefix and bracket evidence for 158 queries |
| `exact-ring-contact-reference.json`, `independent-bank-support-final-01.json` | Exact geometric contact proofs and rounding bounds |
| `INDEPENDENT_REVIEW.md` | Separate Sol challenge/review of the implementation, proof obligations and receipts |
| `offset-tests-06.txt`, `offset-tests-07.txt`, Python test logs | Actual positive and failure-path controls; test07 adds DBL_MAX and invalid-weight cases after build11 |
| `BANK_COST_OBSERVATION.md`, `PERFORMANCE_PLAN.md` | Measured costs and the unmet performance acceptance condition |

The build11 receipt predates the extra test-only arithmetic controls; those were
rebuilt in `build-tests-12.txt`. Any later performance experiment or expanded
native probe must have separate build/run receipts; these results cannot be
silently transferred to changed binaries. The independent oracle verifies the
new mathematical surface, so agreement with the legacy oracle is descriptive
compatibility evidence only.

## Remaining limits

This is a constant-metric offset solid: constant circular tubes around regular
curves, or constant ellipses on admitted xy-planar curves. It is not a rectangular
WISTELL-D winding-pack model. The eight real coil031 bank rays are no-hits for
the diagnostic circular-offset payload. Their presence is not positive-hit
qualification of the physical pack. Collections are not admitted in the new
native mode. Variable radius/frame solids, arbitrary degenerate contacts,
ambiguous normals, and unsupported arithmetic fail closed.

The baseline bank has nine blocked auxiliary point/normal telemetry rows
(`a00`, `w0` through `w7`); these do not invalidate their independently proved
scalar no-hits, but they prevent an unrestricted point/normal usability claim.
Native parameter-seam success is not a physical periodic-boundary validation.
No neutron/photon particle histories, periodic transport, or material physics
qualification have run. The 80% native-throughput target is unmeasured and unmet
as an acceptance claim. The baseline is slow and allocates during queries.

The pre-existing swapped source-hash false-PASS path remains reproduced by the
checkpoint recheck and is not repaired here. The comparator now rejects NaN,
infinity, duplicate keys, contradictory status/count fields, invalid or changed
frozen metadata and cross-representation comparisons. Retained original artifact
hashes match except the intentionally changed production source.

No dependency was acquired, no environment was modified, no SSH or remote job
was used, and no schedule was changed. Local resource observations and failed
attempts are preserved alongside successful runs. Reproduction requires the
hash-matched local analytic and coil031 HDF5 inputs named in the receipts; the
large source geometry is not duplicated in this patch.
