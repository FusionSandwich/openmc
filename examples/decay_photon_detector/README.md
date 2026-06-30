Decay Photon Detector Example
=============================

This example builds a small fixed-source photon transport model for a generic
activation-counting setup:

- an activated point-like sample region with a Co-60 decay photon spectrum
- a simple active germanium detector volume
- detector photon flux and pulse-height tallies
- JSON metadata describing the timing, source normalization, geometry, and
  tally energy bins

The example is a transport/source-term scaffold only. It does not model
detector electronics, dead time, peak fitting, calibration, or spectral
broadening.

Export the model inputs and metadata:

```
python build_model.py --output-dir run
```

Run the exported model:

```
python build_model.py --output-dir run --run
```

When ``--run`` is used, the example also writes CSV tables for detector photon
flux, pulse height, and heating from the final statepoint. The detector
response manifest ``detector_response_manifest.json`` records the source,
timing, detector, tally, units, energy-bin, and export-file metadata.

Validate detector response outputs:

```
python ../../tools/validation/detector_response/check_detector_response.py run
```

The included depletion chain fragment is limited to the Co-60 photon source used
by this example. Set ``OPENMC_CROSS_SECTIONS`` to a photon-capable data library
before running transport.
