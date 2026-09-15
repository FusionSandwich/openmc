# Lightweight evolving plasma source

Implement a compact, configurable approximation of the neutron birth source
during startup, operation and shutdown. The user's aim is useful approximate
shape, profile, temperature, intensity, energy and angular evolution across
plasma configurations, not a full plasma solver. This task is independent of
the current StellarCSG root failures and broken ParaStell test assembly.

Read `../REMAINING_WORK_DISPATCH.md` and `../CLOUD_METHOD_HANDOFF.md` for
resource rules, source access and provenance. Work in your isolated environment
on a unique JS/ branch. Place a small experimental package, tests and examples
under `dev/stellarcsg/experiments/plasma_source/`; avoid modifying OpenMC core.
Do not alter the separate stellarator-neutronics-uq project or assume access
to its proposed private remote. Design an upstream interchange contract only.

## Bounded model

Start with tabulated equilibrium/profile snapshots and user-supplied phase
timing, interpolated conservatively within their declared domain. Provide a
simple manual analytic case and an adapter for compatible equilibrium
families. When no physical time trace exists, expose normalized phase and
label prescribed ramps as diagnostic assumptions, not machine predictions.
Do not infer boundary motion from a single equilibrium or continuation index.

Evaluate whether a small 0-D particle/energy-balance closure usefully improves
on prescribed traces given actual input data. Implement it only if equations,
loss/heating/fueling inputs, validity and validation can be justified. It is
optional, not permission to grow into MHD, gyrokinetics, full transport,
equilibrium solving, turbulence, thermal hydraulics or a quench calculation.
Do not invent universal startup/shutdown durations or uncertainty ranges.

Represent q(x,E,Omega,t) = Q_n(t) p(x,E,Omega | state(t)). Preserve rate and
normalized PDF separately; Q_n=0 is valid and must not produce a fake source
PDF or a prompt-neutron run. Use a cited, verified thermal D-T reactivity
implementation for n_D*n_T*<sigma v>(T_i), with explicit units, fuel fractions,
dilution and density definitions. Keep T_e and T_i distinct. External total
rate calibration is allowed only when recorded separately from profile-based
production. State excluded channels; D-T absence is not proof D-D is absent.

Shape/profile changes must affect volume/Jacobian and emissivity consistently.
Prefer compatible nested-surface families; define interpolation validity and
test folds, periodicity, coordinate s versus sqrt(s), and heldout snapshots.
Analytic deformation is an explicitly prescribed approximation, not a solved
equilibrium. Report absolute position and local-minor-size errors, rate and
profile errors separately. A steady equilibrium family is not a time model.

Retain position-energy correlation using local ion temperature and a verified
birth-spectrum approximation. Thermal angular baseline is isotropic in its
appropriate rest frame. Shape motion does not rotate/stretch neutron angles.
Only add flow/beam/nonthermal anisotropy with a justified physical model and
inputs; otherwise expose an explicit unsupported status. Distinguish direct
plasma radiation, prompt neutron/photon heating and delayed activation heat.
Temperature, stored plasma energy, neutron power and deposited coil heat are
different quantities. Export source quantities; do not claim to predict all
heat loads. Zero prompt source is not zero shutdown heat.

Freeze hardware/material/boundary/tally geometry in source-only studies.
Reject source-wall intersection; no silently discarded points followed by
renormalization. One-period export requires symmetry-compatible states and
explicit sector/full-device rates. Block nonperiodic perturbations in this
milestone instead of silently forcing them into a sector or running a machine.

## Deliverables and tests

Build a small documented Python API plus explicit JSON/table schema for
configuration, profiles, phase/time, units, provenance, validity and outputs.
Support a user-defined analytic configuration and at least one independent
heldout shape/profile family. Use public licensed inputs, not private desktop
assets. WISTELL-D is optional evidence, not the only supported configuration.
Make nominal startup/operation/shutdown examples runnable without OpenMC or a
full plasma code; mark their prescribed assumptions prominently.

Add a narrow vanilla OpenMC source export only after verifying the installed
version's supported interfaces. If that runtime is absent, supply/test the
portable source representation and report adapter execution as blocked. Do
not acquire nuclear data simply to demonstrate a source generator.

Test nonnegative source, volume/rate integration, zero-rate endpoints, pure
rate scaling, temporal convergence, spatial/energy/angular sampling moments,
unit conversions, periodicity, roundtrip schema and invalid geometry. Validate
interpolation on heldout snapshots; compare coarse/refined source resolutions.
For fixed normalized source and hardware, rate changes require exact linear
response rescaling, not another transport run. Report runtime, memory and
approximation errors; no arbitrary claim of universal accuracy.

Research primary physics/software sources before choosing numerical formulas
or physical bounds. Keep a concise evidence register separating measurements,
published simulations, assumptions and stress cases. Deliver code, tests,
commands, hashes, failed approaches, uncertainty limits and exact restart
instructions. Return an honest lightweight result even when physical timing
or free-boundary response remains input-limited. Seek independent numerical
review before describing the source model as validated.
