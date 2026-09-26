# Bounded one-period plasma source handoff

`stellarcsg.plasma_source.load_bounded_plasma_source(path,
expected_wall_sha256=...)` consumes a portable,
same-directory JSON handoff. It returns a normalized class-B diagnostic source
definition only after the export, native sampling and fixed-wall clearance
evidence all agree on the source mesh. The physical neutron rate remains `null`.
The caller must pass the SHA-256 of the wall in the transport model being built;
the loader rejects a bundle for a different fixed wall. The returned source
definition carries that wall hash for a downstream model-assembly check.

The `stellarcsg.plasma-source-handoff/v1` JSON has state
`ADMITTED_BOUNDED_DIAGNOSTIC`, `field_period_degrees: 90`,
`coordinate_units: "cm"`, `physical_rate_n_s: null`, `case_id`, and a `files`
object. Each of `source_result`, `sampling_result`, `clearance_result`, `mesh`,
`mesh_data`, `case`, and `wall` is `{ "name": "basename", "sha256": "64 lowercase
hex digits" }`. Files must be colocated regular files with matching hashes;
the wall entry is the actual fixed-wall H5M used in clearance.

The export and sampling records use the current UQ source schemas. The selected
case must be a class-B analyst stress test with normalized per-element source
strengths and one- or two-line conditional birth spectra. The loader verifies
the tetrahedral geometry arrays and consistency of the profile integrals with
the probabilities. It requires the native OpenMC sample checks to have passed
for the same files and number of elements. `make_openmc_source()` then creates
an OpenMC MOAB `UnstructuredMesh` and a unit-strength `MeshSource`. The same
returned source definition should be used in both eventual CSG and DAGMC
models; no transport is performed by the loader.

The proposed independent clearance record is
`stellarator_uq.bound-source-clearance/v1`, with status
`QUALIFIED_BOUNDED_SOURCE`. It binds `source_mesh_sha256` and
`wall_h5m_sha256`, declares `whole_cells_inside_cavity`,
`periodic_sector_contained`, and `source_wall_intersection_excluded` as true,
and supplies finite `certified_gap_lower_bound_cm`, nonnegative
`continuous_wall_error_bound_cm`, and positive `required_clearance_cm`.
Admission requires `certified_gap_lower_bound_cm -
continuous_wall_error_bound_cm >= required_clearance_cm`. The UQ task must
establish these statements for the complete source tetrahedra and the actual
fixed wall; sampled source sites alone cannot establish containment. The
consumer validates bindings and stated conditions, but does not itself prove
the clearance calculation or authenticate who wrote the evidence.

The UQ project's current corrected ASC P00 geometry target is the fixed H5M
SHA-256 `549c42bf66b290f8f56b6f4d7523940c3b32b9d256d993ea42605f4dddb33e39`
and ASC case SHA-256 `742ef72f1e1c07f958ecc3e47796709d1b51a53407cb89b0448f7a595d722c59`.
Its class-B `s=0.80` source is staged but has not been meshed or cleared. The
prepared ASC P00 facet-clearance script intentionally emits a **diagnostic**
status and leaves continuous-wall and source-wall containment qualification
false, even if its stored-facet test passes. That output does not satisfy the
`QUALIFIED_BOUNDED_SOURCE` handoff contract. Earlier `s=0.90` evidence rejected
the source at the previous fixed wall; the earlier `s=0.80` attempt stopped
before export. No actual WISTELL-D source has been loaded or transported here.
The synthetic
contract tests deliberately fabricate evidence and a non-MOAB H5M placeholder;
their positive constructor check only verifies the Python interface. Source
discretization convergence, physical-rate modeling, one-period geometry,
native neutron/photon transport and matched performance remain separate gates.
