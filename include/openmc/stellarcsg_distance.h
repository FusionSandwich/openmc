#ifndef OPENMC_STELLARCSG_DISTANCE_H
#define OPENMC_STELLARCSG_DISTANCE_H

#include <cmath>
#include <stdexcept>
#include <string>

#include "openmc/constants.h"
#include "stellarcsg/periodic_radial_surface.hpp"

namespace openmc {

// Keep terminal unresolved separate from historical diagnostic counts: a
// fallback may resolve an interval after incrementing those counters.
inline double checked_stellarcsg_distance(
  const stellarcsg::DistanceResult& result, int surface_id)
{
  if (result.disposition() == stellarcsg::DistanceDisposition::unresolved) {
    throw std::runtime_error("StellarCSG surface " + std::to_string(surface_id) +
                             " has an unresolved nearest-boundary query");
  }
  if (!result.found) return INFTY;
  if (!std::isfinite(result.distance) || result.distance < 0.0) {
    throw std::runtime_error("StellarCSG surface " + std::to_string(surface_id) +
                            " returned a non-finite or negative hit distance");
  }
  return result.distance;
}

} // namespace openmc

#endif
