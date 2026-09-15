# First review of independent method reports

Status: preliminary review of returned chat reports, not local reproduction
or patch-level certification. Six prior sessions returned results; all six
received a targeted evidence follow-up and the mandatory same-environment
ZTorus rule. Their private chat links and original responses are retained
outside this public repository. No candidate is promoted.

## Findings

1. Bernstein's sampled `distance_reference` fallback is not the exact oracle.
   Its reported strict zero errors coexist with 32/160 wrong stress results,
   all stress queries using fallback. The proposed fail-closed patch was not
   applied before the environment disconnected. Neither strict success nor
   a future BLOCKED patch establishes current correctness.
2. Torus-arc distances are provisional: 160/160 queries are BLOCKED. Reported
   C0 joins, not G1 biarcs, introduce a seam-normal issue; corresponding sampled
   error is not two-sided shape certification. No usable distance throughput
   can be claimed for this blocked solver.
3. Swept-fiber depth-1 cost is candidate generation only, not full distance.
   Its apparent 0.984x old cost omits correction and certification and leaves
   all strict queries unresolved. It is not a faster replacement solver.
4. Bezier's accepted point t is not yet a certified longitudinal upper bound
   for excluding earlier roots. Binary64 enclosure composition, classification
   and topology also remain open. Synthetic same-parameter samples do not
   establish WISTELL-D fidelity or whole-surface correctness.
5. Original-fast origin-contact semantics require an explicit distinction
   between a mathematical root at zero and OpenMC on-surface suppression.
   The reported a08/a15 improvements need the actual diff and root-ordering
   evidence. The interrupted, uncommitted experiment cannot be promoted.
6. Period-import's hash reconstruction must distinguish original bytes from
   line-ending canonicalization. Exact quarter-turn image consistency and
   source-fit deviation are different measurements. Sampled 47.58 cm coil
   clearance is not a global clearance proof or physical winding-pack result.

## Reported scoreboard

Values below belong to DIFFERENT destination environments. Absolute timings
are recorded for provenance, not ranked across machines. Same-environment
ratios to the old control are retained where supplied; all ZTorus ratios are
null because the returned reports did not measure that control. Performance
comparison is therefore incomplete under the new mandatory rule.

| Method | Reported distance bank mean ns | Same-host old ratio | ZTorus ratio | Main gap | Disposition |
|---|---:|---:|---|---|---|
| Original-fast repair | latest candidate not finalized | null | null | offline uncommitted repair; source diff needed | experimental |
| Bernstein | 305376.11 | about 253 | null | strict fallback dominates; 32/160 stress wrong | reject current prototype |
| Torus-arcs | 7631.53 provisional | about 6.35 | null | 160/160 BLOCKED; join/root admission incomplete | experimental, not eligible |
| Bezier plasma | null | null | null | synthetic fidelity only; no comparative timing | experimental |
| Swept-fiber depth 1 | 1269.056 candidate-only | 0.984 candidate-only | null | 160/160 unresolved; full solve absent | reject as production solver |
| Period import | null | null | null | kernel gate and physical assembly unresolved | compiler evidence only |

Original-fast control report independently reproduced old/seed/acceptance
strict wrong counts 4/3/2, with bank means 1103.47/1820.73/2591.81 ns in its
own environment. Acceptance was 2.35x old there, not a robust <=2x result.
No conversion of these values using a desktop ZTorus measurement is allowed.

Bernstein reported 12/160 strict fallbacks, about 90% of strict distance time
in fallback. These are not to be relabeled exact-fallback metrics until the
algorithm is identified; reported fallback used the sampled reference.

Period import reports Python 42 passed/1 skipped; C++ 3/4 passed, a08 still
failing. Its heldout ParaStell result remains rejected at 2.39627%, above 2%.
WISTELL physical winding-pack clearance and transport remain unmeasured.

## Next evidence gate

Collect actual patches and raw hash-bound receipts, then review source and
tests before rerunning only the smallest useful experiment. Existing source
commits reported by the sessions are unpublished and have not been fetched
or verified locally. The original-fast and Bernstein environments went offline
before final patches were saved. Missing artifacts stay missing, not inferred.
No build, dependency acquisition, mesh run or remote job was launched by this
review. All previous negative results remain retained.

## Follow-up corrections received

- Original-fast and Bernstein confirm their workspaces were pruned: uncommitted
  solver diffs and raw receipts are unavailable, with no surviving exported
  copy. Their reported observations are no longer reproducible from exported
  artifacts. Do not treat their candidate code as recovered or hash-bound.
- Bernstein confirms all 12 strict fallbacks were sampled, zero exact. Sampled
  fallback consumed 89.88% of strict and 93.77% of stress time. Its follow-up
  P95 differs from its original summary (3185534 versus 3180534 ns); raw receipts
  are missing, so this discrepancy remains unresolved.
- Period import confirms deliberate geometric canonicalization: three members
  per orbit are replaced by exact images of one representative. The input file
  is preserved, but the compiled geometry changes by a sampled 0.0002030684 cm.
  This is a controlled representation change requiring fidelity assessment,
  not merely more accurate evaluation of unchanged source geometry.
- The coil checkout SHA is LF-normalized
  324812c391ee5ef6427a0983f823f3909dadb73d6b71d078576193d1ad478a6f;
  explicit CRLF reconstruction yields the locked source hash. Both must be
  retained in receipts; they are not identical byte streams.
- Torus-arcs and period-import report surviving exported patches, but this
  coordinator has not yet retrieved or verified their contents. Patch-level
  review remains a separate next step. All returned ZTorus ratios remain null.
