#ifndef OPENMC_STELLARCSG_DISTANCE_H
#define OPENMC_STELLARCSG_DISTANCE_H

#include <cmath>
#include <stdexcept>
#include <string>

#include "openmc/constants.h"
#include "stellarcsg/periodic_radial_surface.hpp"

namespace openmc {

// Adapter validation only: do not change geometric origin contacts or the
// kernel's coincident policy. Historical unresolved-interval counters are not
// a terminal disposition; a typed unresolved/no-hit contract is still needed.
inline double checked_stellarcsg_distance(
  const stellarcsg::DistanceResult& result, int surface_id)
{
  if (!result.found) return INFTY;
  if (!std::isfinite(result.distance) || result.distance < 0.0) {
    throw std::runtime_error("StellarCSG surface " + std::to_string(surface_id) +
                            " returned a non-finite or negative hit distance");
  }
  return result.distance;
}

} // namespace openmc

#endif
