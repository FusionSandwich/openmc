# StellarCSG documentation review — October 9, 2026

## Read these first

- [All methods and recorded results](METHOD_RESULTS.md): **81 entries**, including unsuccessful repairs, later optimizations, restricted successes and proposals that were not run.
- [Documentation gaps and status corrections](AUDIT_FINDINGS.md).
- [Full document index](DOCUMENTATION_INDEX.md): **309 distinct Markdown records**: 306 from the initial 1240 checkout copies, plus three late records/versions.
- [Structured method catalog](METHOD_RESULTS.json) and [document catalog with copy paths and hashes](document_catalog_with_coverage.json).
- [Independent Sol review](INDEPENDENT_COVERAGE_REVIEW.json): **ACCEPT_SCOPED_DOCUMENTATION_COVERAGE**, with no blocking findings remaining. This accepts documentation accuracy and bounded coverage, not new scientific or performance claims.

## Main findings

The documentation is extensive but fragmented across historical checkouts, archived review packets and later campaign folders. The October 8 broad ledger contains 32 method/reference entries, but omits or aggregates several earlier exact-reference and recovery variants, blanket/composite cases, and subsequent experiments. This review adds those records without changing the earlier ledger.

The restricted native axis-plane repair later received independent acceptance. The later represented-P00 timing campaign reports a robust pass, with a pooled P00/ring ratio of **1.1046**. Both results have narrow scopes; physical winding-pack fidelity, ownership and broader native events remain open. Work-matched plasma diagnostics still report ratios around **2.10–2.12**, above the 1.25 target. Fourier/toroidal prototypes remain synthetic approximation or query research, with general queries unresolved.

## Preservation and limits

This directory is an additive review artifact. The original attempt folders, raw results, ledgers and source checkouts remain intact. All 309 distinct Markdown contents are copied byte-for-byte under `source_snapshots/`; decisive additional JSON/JSONL records are frozen under `source_data/` with their original paths and hashes in [the manifest](source_data_manifest.json). The initial selected inventory lists **6227 files** in [source_inventory_final.json](source_inventory_final.json). A [late capture](late_source_manifest.json) records 14 further file observations, including a changed proposal README and the newly completed quartic composition reference. Its final capture time is **2026-10-09 22:11:43 UTC**. The earlier inventories and README version are retained separately.

Frozen documents retain their original text, including historical instructions and relative links. Those internal links belong to the original source location shown in the document catalog; they are not rewritten to make the frozen copy appear newer. The review's own evidence links resolve to captured files in this directory.

This review used retained local documentation and small result receipts. It did not rerun scientific methods, compile native code, inspect active jobs, change schedules or access remote compute. It does not claim to recover disappeared cloud artifacts or independently validate every raw statepoint, log line or scientific proof. See [audit findings](AUDIT_FINDINGS.md) for unresolved documentation gaps, [preservation check](PRESERVATION_CHECK.json) for file identities and [Git byte-preservation check](GIT_PRESERVATION.json) for captured-byte storage. Scoped Git attributes disable newline conversion for this archive.

## Continuing the record

Keep this dated review directory as a snapshot. Future review captures should use a new numbered directory. Record new attempts with their input/source identities, execution status, failed controls, result denominator, scope, uncertainty and independent review; keep each prior run intact. A newer pass can supersede a specific earlier gate only with an explicit scope and provenance link, while the earlier result remains available.
