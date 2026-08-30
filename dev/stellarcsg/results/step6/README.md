# Step 6 remote qualification

The CAD-free magnet prototype represents a closed coil as the union of
equal-radius capsules around a closed polyline. A segment AABB BVH
accelerates exact analytic ray/capsule intersections. The companion
hexahedral mesh is indexed by coil arc length and two local
cross-section coordinates.

- `pytest.log`: full StellarCSG Python suite.
- `swept-coil-qualification.json`: BVH/brute-force equivalence,
  candidate reduction, timing, frame closure, and mesh checks.
- `coil-local-mesh.h5` and `coil-local-mesh.vtk`: replayable local
  tally mesh generated without CAD.

Current limit: this step qualifies a circular cross-section prototype;
a production rectangular or multilayer winding pack is not yet claimed.
