# Independent Sol review of the matched transport proxy campaign

Review date: 2026-09-26. Scope: the completed 18-run fixed plan, repaired comparison validator, and exact coil geometry enclosure. This review made no builds, transport launches, oracle launches, dependency changes or production-source edits. Its only write is this report. The review follows `C:\HTS_transport\AGENT_DELEGATION.md` and preserves unsupported states.

The campaign supports narrow observations of sampled implementation agreement and measured proxy transport timing. It does **not** meet the native-throughput target, qualify the complete spectrum, or establish upstream readiness. Coil/native comparison concerns an explicitly bounded geometry approximation; the annulus remains a different-shape descriptive control.

## Decisive evidence checked independently

All 18 receipt identities agree with `campaign-plan.json`: three distinct seeds 1741/2741/3741, 20 batches, one thread, 1000 particles/batch for plasma and 10 for coil. All receipts report `OBSERVED_COMPLETE`, exit 0 and the same production binary, library, harness, source bank and Fe56 data. This comprises 120,000 plasma histories and 2,400 coil histories across the six variants. No pilot contributes to these totals or timings.

I independently rehashed all 72 XML inputs and 360 canonical zero-padded statepoints: no missing or mismatched artifact. Every receipt link in all four comparison JSON files matches the actual receipt. All 16 current build-04 input hashes still match its before/after receipt, and the current binary/library hashes match both build-04 and every production run:

- OpenMC executable: `47a1d0f4a15aba391a3f3ae5cb1dd0776f5041afe073e2e2d3fb58b04885a398`.
- Library: `7fa3dbf5bef055aa2227842800e54a2daa84537a1ba6730e97f4fb6cd25d317e`.
- Production harness: `b787ff1a06fa561baef10d698616fab9c8235c719be6ab54cc21110dfdcd0ae4`.
- Source bank: `5ae218fa17c8d57afd55792e8dd68d4a458a46a212e471de1e1ec0db881d1c39`.
- Fe56 data: `18abc04dc9fd602948bafcf487323a1148681c75ee74e27863e843211fd6f1f8`.

The observed mean of three paired throughput ratios was independently recalculated from the recorded transport timings. The ratio always denotes right-variant throughput divided by left-variant throughput, at equal histories; initialization/process wall time is a separate metric.

| Comparison | Mean right/left throughput | Sampled batch agreement | Bin states |
|---|---:|---|---|
| Plasma native → spline | 0.6208402303400099 | Pass | 28 equivalent, 4 insufficient coverage |
| Coil spline → ordered | 0.4022898100661501 | Pass | 24 equivalent, 8 insufficient coverage |
| Coil native → spline | 0.0012989383385587604 | Does not agree; approximation control | 24 equivalent, 8 insufficient coverage |
| Coil native → annulus | 1.2514248950096178 | Does not agree; shape control | 4 equivalent, 8 insufficient, 20 not equivalent or underpowered |

I compared 1,920 paired batch-bin values per implementation pair directly from receipts. Plasma maximum absolute difference is `2.3283064365386963e-10`; maximum difference divided by the planned numerical tolerance is `2.5142780494636248e-5`. Coil spline/ordered values are identical. These are sampled regression results, not proofs about all histories. The coil accelerator therefore improves this proxy's throughput by approximately 2.49 times against its disabled path, while remaining much slower than the native torus. Native coil transport takes only about 3 ms/run; these small timings and three pairs do not establish portable benchmark precision. The plasma specialization also falls below the observed 0.8 native-throughput target.

## Validator source acceptance and limits

The current validator closes the previously identified holes: canonical statepoint/hash sets; raw cumulative-score differences; seed/count/batch identities; actual final H5 scores, estimator, filters, nuclides, means and standard deviations; runtime/global tally matching; NRT recomputation; fixed Ed=40 eV; launch normalization identity; raw failure diagnostics; cross-seed materials/tallies and settings excluding only seed; an order-independent implementation-pair gate; three-pair/20-batch qualification; descriptive annulus classification. A renamed/unhashed statepoint, redistributed receipt spectrum, changed receipt timing or a reversed implementation pair can no longer obtain the earlier erroneous interpretation through those paths.

The nine comparison controls and sixteen subtests in `comparison-tests-03.txt` passed. They test compare/validate logic, including cross-seed materials and reversed pair scope. The later `python-final-tests.txt` reports fourteen tests and sixteen subtests passing, with only duplicate-surface-ID warnings from test fixtures.

I inspected `audit_proxy_artifacts.py` and `artifact-audit.json`: all eleven actual-loader mutations are rejected for their intended reasons. These cover changed runtime, redistributed energy bins preserving integral/ownership closure, changed receipt plus launch seed, missing statepoint entry, missing MT444, wrong displacement energy, changed NRT, changed uncertainty, nonzero exit, timeout, and raw unresolved diagnostics. The mutations operate on temporary receipt/launch files and symlinks; the unresolved-log control unlinks the temporary symlink before writing, preserving the original run. The checker, audit script and baseline native receipt hashes all match the receipt. This supplies the previously pending decisive loader failure-path evidence without new transport.

The three pilot track hashes also match. The audited 41 plasma, 10 accelerated-coil and 10 ordered-coil recorded states have consistent allowed cell/material labels and finite nonnegative energies. Accept this as 61 recorded states' label consistency. The audit does not classify their positions against an independent geometry or identify every collision, and therefore cannot establish full geometric collision ownership.

The summed tally differences are already per-source batch quantities; no second division by particle count is appropriate. Flux bins are tracklength cm/source, becoming volume-averaged flux only after volume division. The declared Fe atom count conversion and `0.8*damage_energy/(2*40*atoms)` are dimensionally consistent with the explicit NRT test convention. Cell/material closure is useful, but one Fe cell makes it insufficient by itself to establish every collision's geometric ownership.

The finite 256-direction source bank is sampled randomly per history. Statistical statements are conditional on that fixed empirical source bank. Bonferroni Student-t intervals are the planned finite-batch approximation, not an exact finite-sample guarantee for sparse collision data. Insufficient bins remain unqualified: all four JSON comparisons correctly set full-spectrum equivalence false. Exact sampled agreement of zero bins does not certify their physical response. Annulus throughput cannot count as meeting the round-tube implementation target.

## Exact coil geometry and volume

`proxy_coil_geometry.py` uses original binary64 controls as exact Fractions, the exact periodic cardinal B-spline-to-Bezier conversion, exact Bernstein products and dyadic subdivision. The span derivative enclosures establish positive angular derivative and signed curvature; each span's chord homotopy stays in an origin-free half-plane, and the exact seam polygon has winding one. Thus the closed C2 curve makes one strictly increasing angular turn, is simple, and positive curvature makes it strictly convex.

The curvature upper bound `0.010008044824561227 cm^-1` implies every radius of curvature exceeds about 99.9 cm. Parameterized by outward normal angle, a signed planar offset d has tangent derivative `(rho+d)T`; for `|d|<=5`, it remains strictly convex. Different offsets have nested support functions and cannot intersect. At fixed z, each circular normal-disk fiber projects to these disjoint planar offsets. Consequently the three-dimensional radius-5 normal tube is embedded, with reach exceeding 5 cm. Integrating its Jacobian `1-kappa*a` over the symmetric disk cancels the odd term and yields volume `pi*25*L`.

I accept this reach argument for the hash-bound prepared fixture, not arbitrary swept curves. `coil-geometry-bounds-02.json` bounds radial deviation by approximately `2.425014803e-5 cm`, length by `[628.3184423425413, 628.3184566045675] cm`, and volume by `[49348.01506445773, 49348.01618459467] cm^3`. The updated volume conversion multiplies the pi enclosure and length endpoint as Fractions before directed binary64 conversion, avoiding intermediate floating multiplication gaps.

Actual-volume NRT proxy postprocessing may use this volume interval, propagating its inverse into atom-count/DPA bounds. The persisted transport receipts still use the common native reference volume and remain reference-normalized damage indices; this review does not relabel them silently. Even actual-volume normalization would qualify the declared Fe56/NRT proxy per source, not device DPA/s or DPA/year.

## Reviewed artifact identities

- Comparator: `52f26cd9d115d66d6dd149ba935cc76eed33d7aa0994af5ae3f0c6940a698f89`.
- Geometry prover: `756c64b5364c90af50b41002b9fc4d6a39291f2468e1a7e81ac2b5a6d77d4b0d`.
- Geometry bounds-02: `a7bc1546f109d3ac243b1ae34cd0e465df7d0b5b3aa1415f31a1aa4c94b9aa2e`.
- Plasma comparison: `df49ac120254f22f5b12b85f0df0d26fd004585e6a6c9b29280155fcef8d7379`.
- Coil spline/ordered comparison: `34c3a2a96ec228672d6f730d4eabc441d79bdab054fc39d389370a1acb84a6cb`.
- Coil native/spline comparison: `97d6d326c119c4e5b5940139d5bc46dcac97b04aa3b348761b8c2fb59ecf9be1`.
- Coil native/annulus comparison: `97111aa109919ca0ed946b31cfb4098687a593c486e8d5d0689412b31dffdb3d`.

Fresh `qualified-on.json` and `qualified-off.json` report independent 160-query distance qualification at exactly `1/100000000000 cm`, 69 hits/91 no-hits, with 158 ordinary exact certificates and two support-contact certificates. I rehashed each candidate, canonical bank, prefix receipt/query output, verifier, support prover, aggregator and fresh support output against the aggregate links: no mismatch, and aggregate before/after hashes agree. The exact reference mechanisms and unchanged verifier/aggregator were independently reviewed previously; no oracle execution was duplicated here. This accepts the fresh bounded bank-distance milestone. It does not supply universal transport, full normal or physical-material qualification; nine bank telemetry states remain blocked in the raw observation receipt.

`analysis-summary.json` preserves the expected distinction: all 24 covered coil native/spline bins are equivalent within the planned finite-batch criterion, while eight are sparse. The sampled integrated damage-energy difference is approximately `-1.08286750135e-7` relative to native. The actual-volume NRT interval is explicitly normalization-only for a fixed sample mean and excludes Monte Carlo uncertainty; it must not be interpreted as the full uncertainty interval for physical DPA. The successor `analysis-summary-02.json` implements the requested exact Fraction multiplication/division and directed conversion, explicitly conditional on the rounded stored mean index. Its source-summary and geometry hashes match those reviewed above. I independently checked both reported endpoints by exact BigInt cross-products of the binary64 fractions: the lower endpoint is no greater than `stored_index*reference_volume/volume_upper`, and the upper endpoint is no smaller than `stored_index*reference_volume/volume_lower`. Accept this normalization-only interval `[3.204065664307497e-25, 3.2040657370356978e-25]` per source for the declared Fe56/NRT proxy.

The preserved correct-target `native-probe-02.jsonl` reports PASS for member-2 distance/normal controls and native CSG entry/exit ownership, with entry `15.999999999998977 cm`, exit after coincident entry `27.999999999999407 cm`, and signed surfaces -1/+1. It explicitly records `particle_transport:false`. Its new observed distances must not be linked to an older receipt asserting different exact binary64 returned values. The production proxy campaign supplies the separate actual particle-history observations.

Additional observed artifact SHA256 identities:

- Artifact audit: `f694308cc804430a97461e41cc1a6b9f32e27ac8ea371792adc2931cc42ebbda`.
- Audit script: `3f50af91b693e8c698c698f37c133b437b00cbe4192e4166cb94dbc5f62d0ba3`.
- Analysis summary: `ab7e59109a2ff423228a87d1a5f326b2a27439a345759029263dad1fdc34661a`.
- Directed-normalization summary-02: `90a889d0b9bb25fab009fee4a641244f21f81722477bc15096df715b5daceee7`.
- Final Python tests: `e007fada5e11ef6920a3dca6d31ad407354acbabd49798abeb76bdc7059cb00e`.
- Qualified accelerator on: `5e85b509272dd79516ee5049767024bdb28b92189625209a3909d6e0a43b49dc`.
- Qualified accelerator off: `938d2786295517cc13d6fe2ed711959ea233b615e14735776df919dfef11efee`.

Accepted: fixed-campaign completion/provenance checks, sampled implementation agreement, narrowly reported timing observations, corrected claim separation, actual-loader negative controls, recorded-state label consistency, fresh bounded bank-distance certificates, and the prepared coil's embedded-tube volume formula. Rejected as unsupported: 80% native-throughput success, universal spectra/DPA equivalence, arbitrary shaped-surface transport qualification, full geometric collision-ownership qualification, and upstream readiness. No additional production run is requested by this review.
