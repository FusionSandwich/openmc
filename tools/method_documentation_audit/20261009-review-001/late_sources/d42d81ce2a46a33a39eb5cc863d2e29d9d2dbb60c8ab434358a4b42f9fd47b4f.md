The Fourier-to-torus proposal needs a reconstruction definition and complete boundary-search contract before its speed can be assessed. This draft preserves the original proposal in a seven-page Word review packet, defines torus-assisted tracking, and reviews the newer torus-patch, weighted-torus, hybrid, direct-Fourier and local-quartic trials in PR #7.

The exact candidate scheduler combines conservative hierarchy traversal, front-to-back ordering, collision ceilings and bounded candidate reuse. Earlier or equal unresolved domains block first-hit acceptance. The new rational quartic oracle enumerates distinct roots of a represented polynomial, including repeated contacts and closed endpoints; coefficient uncertainty, physical fidelity and boundary ownership remain separate obligations. Irrational root brackets remain unresolved for the scheduler's scalar-hit interface.

The review corrects the earlier conversational claim about constant-weight polynomial torus sums: they remain quartic. The retained trials expose a restricted global shape family, missed Fourier crossings, singular-grid candidate loss and an extrapolated local quartic sheet. Exact isolation reproduces the latter polynomial root while its target field remains about +0.784 m, so it is still not accepted as a physical hit.

Validation:

- Original DOCX: all seven pages rendered and visually inspected; fourteen evidence snapshots bound by SHA256.
- Scheduler: 20 controls, 120 independent trimmed-plane queries and 12 ablation arms; prior independent Sol acceptance with 2,400 additional multi-root resolutions.
- New isolated replay: 59 controls (29 frozen prototype, 20 scheduler, 10 quartic-oracle), including a 160-polynomial factored bank; all three retained negative cases reproduced.
- Frozen evidence: 93 committed input files from `9399a879926cb09658709ff030d0317e9e96b7e5`, SHA256 verified; retained run source/output hashes checked and later source formatting compared by parsed AST.
- Independent Sol oracle/replay acceptance recorded under `dev/stellarcsg/experiments/quartic_combinations_20261009/independent_review.json`.

Scope: standalone Python experiments and review documents. No native backend, real-VMEC fidelity, physical coil qualification, transport or native speed acceptance. The previous synthetic hierarchy reduced box tests from 129 to 15; query reuse eliminated repeat box tests. These are work counts. The newer retained ~3.3x Python Fourier candidate timing is not native throughput evidence or achievement of the 80% torus-throughput goal.

This PR remains stacked on `JS/axis-integration-20261008` (PR #6). The separate prototype chat owns PR #7 and its active documentation work. That checkout and Claude's checkout, campaign inputs and processes were not modified. No software was acquired, no native builds or remote jobs launched, and no merge requested.
