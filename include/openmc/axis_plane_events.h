#ifndef OPENMC_AXIS_PLANE_EVENTS_H
#define OPENMC_AXIS_PLANE_EVENTS_H

#include "openmc/particle_data.h"

namespace openmc {
class Region;
class Particle;

// Experimental, deliberately narrow native event path. Throws std::runtime_error
// on unsupported input; never falls back to tolerance-based navigation.
bool axis_plane_find_cell(GeometryState& p);
BoundaryInfo axis_plane_boundary(GeometryState& p);
std::pair<double, int32_t> axis_plane_region_distance(
  const Region& region, Position r, Direction u);
void axis_plane_advance_endpoint(Particle& p, double distance);
void axis_plane_commit(Particle& p);
void axis_plane_validate_particle(Particle& p);
} // namespace openmc
#endif
