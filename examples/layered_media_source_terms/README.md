Layered Media Source-Term Example
=================================

This example builds a small fixed-source neutron transport model for generic
layer-resolved source-term studies. It includes:

- a simple one-dimensional slab geometry
- layer-resolved neutron flux, reaction-rate, damage-energy, and secondary
  production tallies
- optional reaction-event output for selected neutron reactions
- JSON and CSV metadata describing the layer stack and tally setup

The example is intentionally generic. The layers can represent shielding,
samples, coatings, detector housings, or material-response regions. It does not
model HTS degradation, BCA/MD cascades, detector electronics, or peak fitting.

Export the model inputs and metadata:

```
python build_model.py --output-dir run
```

Run the model and write CSV tables from the final statepoint:

```
python build_model.py --output-dir run --run
```

Set ``OPENMC_CROSS_SECTIONS`` before running transport.
