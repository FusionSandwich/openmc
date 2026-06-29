Reaction Event Output Validation
================================

This directory contains small utilities for checking optional
``reaction_events.h5`` diagnostic files produced by ``reaction_event_output``.
The checker validates the HDF5 structure, metadata, numeric fields, provenance
codes, and product-to-event references. It does not validate recoil physics or
compare against external transport codes.

For schema 1.2, event balance diagnostics use ``NaN`` as the sentinel for
diagnostics that are not physically computable from the recorded event data.
Finite values are required for ``elastic_exact`` events; unsupported and
product-bearing incomplete events must use the sentinel rather than a fake zero.

Example:

```
python tools/validation/reaction_event_output/check_reaction_events.py \
    path/to/reaction_events.h5
```

Useful options:

```
--require-products       Require the optional products dataset to be present.
--require-provenance 3   Require at least one event with provenance code 3.
--summary-json           Print the summary as JSON.
```
