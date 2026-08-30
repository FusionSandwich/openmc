# Periodic spline coefficient HDF5 schema v1.0

A geometry file contains one or more independent surfaces under:

```text
/surfaces/<surface-name>
```

## File attributes

| Attribute | Value |
|---|---|
| `schema_name` | `stellarcsg-periodic-spline` |
| `schema_version` | integer array `[1, 0]` |

## Surface group

### Attributes

| Attribute | Type | Meaning |
|---|---|---|
| `surface_type` | UTF-8 string | `periodic-radial-bicubic` |
| `units` | UTF-8 string | must be `cm` |
| `content_id` | UTF-8 string | canonical `sha256:<hex>` or explicit test identity |
| `canonical_metadata_json` | UTF-8 string | exact canonical JSON bytes covered by `content_id` |
| `n_field_periods` | integer | positive field-period count |
| `characteristic_length` | float64 | scale used for numerical tolerances |
| `coordinate_singularity_tolerance` | float64 | exclusion scale around singular coordinates |
| `source_metadata_json` | UTF-8 JSON | provenance; not interpreted by C++ kernel |

### Datasets

| Dataset | Shape | Type | Meaning |
|---|---:|---|---|
| `schema_version` | `(2,)` | int32 | group schema version |
| `axis_r_coefficients` | `(n_axis,)` | float64 | periodic cardinal cubic coefficients for \(R_a(\phi)\) |
| `axis_z_coefficients` | `(n_axis,)` | float64 | periodic cardinal cubic coefficients for \(Z_a(\phi)\) |
| `radius_coefficients` | `(n_theta,n_phi)` | float64 | periodic bicubic coefficients for \(\rho_s(\theta,\phi)\) |

The axis splines and the second radial coordinate use reduced toroidal phase
`n_field_periods * phi`.

## Content identity

The Python compiler computes SHA-256 over `canonical_metadata_json` followed by
the axis-R, axis-Z, and radius coefficient arrays as contiguous little-endian
float64 bytes. Both Python and C++ readers recompute this digest and reject a
changed payload. The C++ reader also verifies an expected identity supplied in
OpenMC XML.

## OpenMC XML reference

```xml
<surface id="101" type="periodic-spline"
         data_file="compiled_geometry.h5"
         dataset="/surfaces/plasma"
         content_id="sha256:..."
         solver="reference" />
```

Large coefficient arrays are not embedded in `model.xml`.

## Tally mesh companion schema

The current mesh writer produces:

```text
/vertices_cm                    float64 [n_vertices,3]
/connectivity                   int64   [n_elements,8]
/element_metadata/shell_index  int32   [n_elements]
/element_metadata/radial_index int32   [n_elements]
/element_metadata/theta_index  int32   [n_elements]
/element_metadata/phi_index    int32   [n_elements]
/element_metadata/approximate_volume_cm3 float64 [n_elements]
```

The HDF5 mesh is a research interchange/metadata file. For an OpenMC
`UnstructuredMesh`, a later exporter will write MOAB H5M or Exodus using the
same vertices/connectivity and preserve this metadata in a sidecar file.
