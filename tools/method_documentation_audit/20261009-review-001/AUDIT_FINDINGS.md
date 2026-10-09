# Documentation audit findings

Reviewed October 9, 2026. This is a documentation/evidence reconciliation, not new scientific acceptance.

## 1. No existing ledger covers the whole retained history

The October 8 `METHODS_AND_FAILURES.md` preserves 23 geometry families and nine reference/integration families. The prototype `METHOD_LEDGER.md` covers its own FT attempts. The workload ladder's result table covers later optimizations, but its `ATTEMPTS.jsonl` ends after ladder-02 and omits AB, cross-validation, P00 gate and plasma runs.

**Resolution here:** retain all 32 original rows verbatim in `METHOD_RESULTS.json`; add separate early H, blanket B, P00 diagnostic R, ladder L, composition Q and Fourier FT entries. Link individual later gate/result receipts rather than infer their presence from `ATTEMPTS.jsonl`. These 81 entries mix families, variants and proposals; they are not 81 distinct experiments, and overlapping controls must not be summed into unique coverage.

## 2. Native-event status changed after the older packet cutoff

The older M23 row and packet evidence index describe October 1 arithmetic controls followed by a configure timeout, without accepted native rows. October 8 review and fresh integration receipts subsequently accepted the **restricted deterministic event slice**: 39 models, 208 rows, 154 supported, 54 expected rejections and 460 events.

**Current interpretation:** M23 records the later restricted acceptance and preserves the older timeout. It is limited to void, single-instance, unit-axis built-in planes. Earlier general facet/assembly failures, material cases, broader ownership/scoring semantics and installation ABI are not closed by that acceptance. R02/R03 preserve the counterexamples separately.

## 3. Later P00 timing passed a scoped gate; correctness remains open

The older corrected ring comparison failed at ratio 4.797639; later AABB campaigns reported 2.368/2.608 and compiler-confounded effects. The newer same-build sequence has three distinct outcomes:

| Attempt | Recorded outcome | Limitation |
| --- | --- | --- |
| gate-01, v2+v3 | Median pass, pooled 1.2006 | Worst pairings 1.27–1.28 fail a robust 1.25 bound |
| gate-02, v2–v6 | INVALID overall | One seed CV 6.8%; two seeds passing does not fix overall validity |
| gate-03, warmup replication | Reported PASS_ROBUST, pooled 1.104614615471397 | Represented P00 versus fixed 30x30 cm rings; independent physical/native-event acceptance open |

**Current interpretation:** it is inaccurate to say every P00 timing gate still fails. It is also inaccurate to say the physical winding-pack transport problem is solved. Exact stored-mesh topology/bounds do not certify continuous CAD. R01 records two overlapping component pairs; R02/R03 record unresolved/conflicting owners and native events. Bitwise tally equality cannot eliminate a defect shared by both versions.

## 4. Plasma comparisons use materially different workloads

The original point source is inside the custom plasma and outside its torus comparator. The ladder reports approximately 12.6 times as many collisions/source in the custom model. The v4 ceiling improvement (about 8.07 times) and ratio 195.935 to 23.833 belong to that original unequal-source experiment.

Uniform sources generated separately inside each plasma reduce the collision difference to 51.619 versus 60.589/source. Their reported ratios are 15.8100 for control, 2.100163 for v2–v7, and 2.119799 for v2–v8. They remain above 1.25 and are different solids/source banks. They do not erase the older 159.7233 failed proxy result. `ceiling_certified` is an implementation counter label; independent exclusion/root validation remains open.

## 5. Earlier exact and recovery routes were aggregated too coarsely

H01–H06 separate capsule/admissible seeds, floating pruning changes, exact resultant/gcd/Sturm, exact-query reuse, floating Bernstein prefiltering and exact-rational monotone isolation. H09 separately records Product05's executed two-dimensional outward interval cover: 90 ROOT_FREE / 70 UNRESOLVED, about 106397 ns/query, conditionally approved as an exclusion ingredient and rejected as the production hot path.

H10–H15 separate residual recomputation, queued-nearer recovery, broad crossing checks, crossing plus bounds, narrowed combined checks, and isolated acceptance. Several variants remain wrong or block too many queries. Blocked-query exception times were not measured, so survivor-only timing cannot be promoted as complete-bank speed. H16 preserves the clipped native diagnostic and its tally/track differences separately from solver correctness.

Different banks and thresholds must retain their labels. For example, the selected radial fit's 0.099667% search-grid error differs from its 0.119736% independent-grid error. The 384-query exact reference's 128 geometry blocks are distinct from floating solver failures and are not enforced by recovered production.

## 6. Blanket documentation has different milestones

Early blanket reports say no native family was implemented. Later composite reports contain a physical-normal multilayer compiler and native hybrid smokes. They also report **−37.1463 cm coil clearance**, an engineering failure. B01–B03 retain the implementation progress and failed clearance together. Boolean cutouts and zero lost particles do not fix the physical clash.

Exact circular/torus controls and restricted hybrid interoperability do not extend to all coil shapes. General ellipse/racetrack/capsule chains, nonuniform coil-constrained layers, scaling, multithreading/materialized closure and full-target verified DoubleDown/Embree comparisons remain not run in the reviewed records.

## 7. New proposal trials and combination reference are separate scopes

FT entries preserve all three prototype attempts, developmental failures, immutable reruns and independent reviews. The first two pasted proposals are byte-identical, so they are one input proposal rather than two experiments. FT-006 is a new synthetic all-spline comparator; FT-007 subsequently compares the actual frozen incumbent bicubic evaluator on a different synthetic target. Neither is a native transport speed result.

Q01 separately records the exact-Fraction hierarchy/ceiling/query-reuse reference and its restricted independent acceptance. Its finite adversarial tests validate composition under caller-certified boxes and complete callback root contracts; they do not supply those certificates for actual Fourier/spline/ruled surfaces. Q02 records the later exact represented quartic Sturm oracle, completed concurrently with this audit. It retains endpoint/even roots and conservative unresolved composition; isolation of the fitted polynomial's extra sheet still does not establish an actual surface hit. No timed native gain is established.

## 8. Coverage and unrecovered evidence

The initial inventory covers selected local StellarCSG documents, reports, benchmark records, campaign summaries and the archived review packet. It hashes 6227 selected files and indexes its 1240 Markdown copies as 306 content-distinct records. A late capture adds 14 observations and three distinct Markdown records/versions, giving 309 preserved distinct Markdown contents. Duplicate paths and divergent versions are preserved, including both proposal README versions. The final late capture is dated 2026-10-09 22:11:43 UTC; work completed after that cutoff requires a later review.

The catalog does not imply that every inventoried source/log is portable in this PR: unselected raw data remain at their original locations, with identities in the inventory. External D-drive/WSL build outputs, binaries, statepoints, linked DOCX/PDF/chat material and disappeared cloud artifacts were not exhaustively reacquired or re-executed. Reports referring to unrecovered artifacts remain reported/unrecovered rather than local implementation acceptance. Source snapshots retain their original internal links and historical claims; the new catalog carries corrections explicitly.

The unrelated SC48 gamma diagnostic was found among the documents and indexed, but excluded from StellarCSG method totals. No corrected activity or new nuclear claim is made.

## Recording convention for future attempts

For each new attempt, retain: stable method/variant ID; hypothesis; input and source hashes; geometry/units/frame; bank/workload and comparator; executed versus proposed status; complete result including negative controls and unresolved queries; timing denominator and initialization; accepted scope and reviewer; exact supersession link to earlier evidence. Append a new run or review; never overwrite an earlier result to make the latest status look cleaner.
