# Independent bounded review /009

Read-only source, saved-receipt and local artifact review on 2026-09-27 UTC. Started 00:57:25; no build, numerical worker, container, acquisition, SSH or duplicate transport was launched. Only this review stream's reports were written. Repository HEAD was 54f8af0dbccb1ce2dcd066f27ea79667f2d6ee8f. This is source/evidence acceptance, not fresh numerical qualification.

## Decisions

- Embree: genuine historical linkage established; currently runnable backend **UNVERIFIED / MISSING DEPENDENCY PREFIX**.
- Coil hierarchy: **ACCEPT_SOURCE_DESIGN**, limited to conservative broad-phase exclusion on the already admitted constant-metric offset. Executable correctness and speed **NOT_RUN**; no production promotion.
- Cache: retain prior **ACCEPT_SOURCE / PASS_FINITE_AB**. Diagnostic speed improves but target performance/fidelity remains unresolved.
- Direct plasma evaluate/normal proposal: **REJECT_PROMOTION**, saved probe fails Boolean sense. Cache-only replacement **UNTESTED**.
- Full coil/plasma three-method >=20k, target-fidelity and verified-Embree qualification: **INCOMPLETE**.

## Embree inventory and exact missing capability

The current `build/astra-native/CMakeCache.txt` sets `OPENMC_USE_DAGMC:BOOL=OFF`. Its f301f7a76a1d4bc1910ea17b582dd31ce70f35cc35690ae5c390c1880ce714a6 library is not an Embree/DAGMC benchmark runtime.

The historical sibling checkout `openmc-stellarcsg-composite` retains `DOUBLE_DOWN_BUILD_AND_LINKAGE.json`, `DOUBLE_DOWN_COMPOSITE_RESULTS.{json,md}` and `COMPOSITE_BLANKET_INTEROP_BASELINE.json`. These record DAGMC 3.2.4, Double Down 1.1.0 with an Embree-4 context patch, Embree 4.3.0 and MOAB 5.5.1, resolved libdagmc/libdd/libembree4/libMOAB and the runtime banner `Using the DOUBLE-DOWN interface to Embree.` The 10k hybrid analytic torus smoke is genuine historical Embree evidence, below the new history minimum and not WISTELL-D qualification. The historical 48-coil and plasma timings used ordinary `nompi_nodoubledown` DAGMC and cannot be relabeled.

Current inspection confirms `openmc-stellarcsg-composite/build/composite-openmc-doubledown/bin/openmc` exists, 26,872 bytes, SHA256 8908cc37fcce95b3c3f24432bdeb3b4ebc0bafc81c4ac6bf0ae1114bd0b0a639. Readelf shows its libopenmc dependency and Docker `/workspace/...` RUNPATH. That build's libopenmc directly needs libdagmc.so and libMOAB.so.5. However, the named `build/torus-class-deps` directory is empty: Embree, Double Down and DAGMC prefixes are absent there. OpenMC-Dev-D's compact /opt and loader-cache inventory found no corresponding backend libraries in the inspected locations (no claim of exhaustive absence). Docker CLI exists, but its single image-list attempt failed because the DockerDesktopLinuxEngine pipe was missing. No daemon or container was started and no retry was made; cached image contents are UNKNOWN.

Exact blocker: no currently verified resolvable DAGMC/Double Down/Embree/MOAB dependency closure for the retained executable. Also, this older binary does not qualify current changed source. Next capability action is an explicitly authorized, fully inventoried examination/reuse of the pinned already-local Docker image or preserved dependency archive, if present; identify every resolved library/hash/backend before any transport. Do not acquire or rebuild until operator observations, target/bytes/rollback and authorization are recorded. There is no admitted executable Embree transport command in this review.

## Locally present WISTELL-D meshes

Paths below share `C:/HTS_transport/plots/stellarcsg_multiconfig_20260831/wistell_d/`. H5M hashes were recomputed locally and match saved manifests. Geometry/error quantities are manifest observations, not new independent mesh audits.

| Artifact | Bytes / SHA256 | Manifest provenance and error | Admitted use |
|---|---|---|---|
| `dagmc/plasma_fine.h5m` | 5,534,904 / 861997912a5d8a64d7f527817e8d4b6f0ed1e6a1cdac27110c7ea3b4441cdbd8 | VMEC wout SHA 9231969001203a8133255ee0a275bf552b114cc12524dda0608ab2f12047f7ac; 4 periods; 128 theta x 512 phi; 131,072 triangles. CSG fit max/RMS 0.0327919/0.00241870 cm. Sampled mesh implicit residual max/RMS 0.875842/0.109515 cm. | Provenance-bound candidate plasma reference; exact correspondence to current qualified payload still needs verification. |
| `magnets/coils_1cm_fine.h5m` | 99,130,464 / 9a753d4328f23367ec1cb22298504ed0f7737337faced65fd4afa6ec885043e3 | MAKEGRID source SHA 7748369407d28a70f35b5c4a7c0ab860495a08fd0030002112ea933fe570159b; 48 volumes/surfaces; 2,359,296 triangles; 512 axial x 48 angular samples. Sampled chordal max/RMS 0.102616/0.0270404 cm. | Standardized circular 1 cm tube fixture only; full physical winding-pack mesh NOT_ESTABLISHED. |

The coil compile receipt explicitly says the source does not establish winding-pack thickness. Its paired payload SHA is 9bb178c308e7f3ec659e1651a7d57e0ecbff734d3320000df1c2bf79fcf3262b. Reported source-centerline reconstruction/approximate Hausdorff metrics also need reconciliation; node residuals alone do not establish global geometric fidelity. The meshes were sampled at a stated resolution; a requested certified global meshing tolerance is **UNKNOWN**. Sampled residuals/chordal deviations must not be labeled rigorous Hausdorff bounds. DAGMC runtime `faceting tolerance: 0` is not the generation tolerance.

A representative-coil naming ambiguity remains: compile receipt names representative nonplanar ID31, fine-mesh manifest names ID27, and separately present `representative_coil_001_1cm_fine.h5m` hashes to 182cd0446adcc92c9f4347a55aa286fc011e6a6b1f9b472f08b5ad4cac8fa5a0. Do not choose any of these as a matched single-coil target without binding source IDs. Historical debug overlap complaints remain relevant; normal completion alone does not clear them.

## Hierarchy source review

Reviewed exact patch 0354e84cca67ecb243a0ceb23692c8d4358323f34f4c42762c040b2b507a688f, candidate 91b702e429669438163bc81e8ba57244ef6c239602a187b6b66150c5a324d476, against accepted-cache base 5f71bb5054f74c0e83815bcaf9a75f8509ff0ad59026ea4c551af245b20e6008.

Every node contains the union of the original transformed control hulls, with outward endpoint expansion. Partition centroids affect ordering only. Constructor admission guarantees 4..4096 spans, finite bounded inputs/radii and IEEE long-double round-to-nearest arithmetic; centroid arithmetic stays within that admitted range. Balanced splitting has nonempty children; stored indices avoid references invalidated by vector growth. Fixed 64-entry traversal stack exceeds balanced depth and still throws on exhaustion. The 4096-entry mask is indexed only by admitted span indices.

Pruning uses only `length2(p-node.hull).lo > upper`. Equality/uncertainty retain nodes. A containing box gives a conservative distance lower bound, including interval query points. Minimum computes the mask using its initial valid curve-point witness upper enclosure; any later smaller upper bound cannot invalidate an exclusion. Surviving spans retain original order and the original per-span check. Projection performs local convexity/stationarity proofs before masking remote domains; excluding a whole span against its existing valid nearest upper enclosure covers all omitted tails. Root ordering, prefix proofs, coincidence, normalization, exceptions and unresolved semantics are unchanged.

This supports the source design. It does not certify compiled behavior, fresh finite banks, normal resolution or speed. Tree construction/storage, the O(n) mask scan and small-model overhead remain unmeasured. Before promotion, compile under the existing complete-inventory/exclusive-lease gates and perform the concrete BVH_SOURCE_PROPOSAL_005.md enclosure/coverage, touching/uncertain-box, maximum-index, thin-root, bank on/off and failure tests. Keep unresolved outcomes visible. Do not restore the historical generic solver's wrong-first-root cases a03/a06/a08/a15.

## Cache and plasma evidence

The completed cache A/B used two repetitions of 1,000-history workers, identical original/cache solids and production tallies. Tally-on median transport was 12.262501 -> 6.648469 s; preparation-through-child-exit 18.662684 -> 13.389543 s (27–28% elapsed reduction across on/off). All 128 final local sum/sum-square values matched; 69 hits/91 misses and nine blocked no-hit-origin normals were preserved. These finite results do not qualify arbitrary tangency, full target shape or the new minimum history count. Native torus transport ~0.006410 s is a short diagnostic denominator. Cold geometry preparation is UNKNOWN; the production library remains original despite integrated cache source.

The plasma isolated probe compiled but exited 1 with `PROBE_FAIL: sense changed`. Eleven printed distance records agree; failure occurs during evaluate/normal/directional-sense checking before packet timing. `Surface::sense` uses evaluate's coincidence threshold then strict `u.dot(normal)>0`; apparently tiny gradient/tie-break differences are a plausible source mechanism, not a reproduced p/u counterexample. Exact failing coordinates were not recorded. Reject direct evaluate/normal promotion. Diagnostic source adds that logging; the separate cache-only alternative preserves evaluate/normal/distance checking but has no passing receipt yet.

One read-only snapshot of the existing owner's new transport-009-01 receipts found both builtin/custom completed 20,000 histories, exit0, tally-on, shared material/settings/tally XML hashes. Current periodic payload SHA 52695c3c6a7329faccdd009f1179c50c91e24c8902447356d3b2cd77c7f9ca36 and library f301... are recorded in its manifest. Custom transport 34.819716296 s versus builtin 0.218000213 s gives 159.7233, far above 1.25. Native invocation wall is 44.185278351 versus 8.643225121 s. This is a single pilot, **COMPLETED_NOT_ACCURACY_ACCEPTED**, without DAGMC/Embree; custom cold coefficient preparation, separate geometry-load timer and crossing counts remain UNKNOWN. No raw per-bin/statepoint audit was performed here and target-mesh correspondence is not yet established. Receipt completion does not promote physical or tally accuracy.

## Public consolidation review

Reviewed snapshots: CONSOLIDATED_DEVELOPMENT_20260926.md SHA 6bb1507c9b83943f134dad3f3886a356f3ed60b635add098e97e0b88187baba5; BENCHMARK_CONTRACT_BUILD_TRANSPORT_20260926.md SHA 8c84fc0293df4b4614521ff0963916d58876efcfd155bb91f288de84eed1ad1d; BUILD_TRANSPORT_RESULTS_20260926.md SHA d43839cef0fade8c5910d0af9530febd8cdc0c6ede8870e1adbfca29553e12ae.

The scientific/time interpretation is sound: separate transport and cold geometry, <=1.25 transport ratio, simpler built-in cost controls, same-target Embree requirement, no universal tally claims and no complete three-method claim. Historical exact circular timings were checked against raw measured repetitions (1.3670 custom /1.4343 builtin). No source acceptance reversal was found.

Before calling this a refreshed latest-results consolidation, append the now-completed generic plasma pilot above and replace the blanket assertion that both new assignments lack completed timing receipts with their precise current dispositions. Update historical-only Embree availability wording to reflect the present executable plus missing dependency closure. Label sampled mesh error separately from certified tolerance and retain the physical coil-pack gap. These are publication freshness/capability corrections, not a claim that the full matrix completed. Public documents and other owners' files were not edited here.

## Architecture recommendation and next step

Coils: immutable conservative span/shared-coil hierarchies on the strict admitted solid are the best supported immediate performance direction. Full rectangular/varying-frame packs still require explicit face/frame/trim/event ownership, potentially ruled rational faces. Offset certificates cannot establish a different pack's fidelity. Plasma: retain periodic local-patch/BVH structure and exact analytic admission, while preserving checked distance and investigating Boolean boundary semantics before adapter promotion. Compile geometry bounds once, exclude only proved domains and retain complete/fail-closed fallback.

The next finite coil action is the inventoried source-proposal compile and enclosure/coverage/bank acceptance block already specified in BVH_SOURCE_PROPOSAL_005.md, not an automatic full campaign. The next plasma action is independent acceptance of the existing 20k receipts and logged sense diagnostic/cache-only test, without rerunning those completed workers. The Embree action is blocked by the exact runtime capability above. Only after target binding, executable and accuracy acceptance should owners fill the matched >=20k three-method matrix with cold/reuse costs, completed work, runtime backend evidence and uncertainty.
