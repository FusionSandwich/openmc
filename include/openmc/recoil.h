//! \file recoil.h
//! Recoil kinematics helpers

#ifndef OPENMC_RECOIL_H
#define OPENMC_RECOIL_H

#include <cmath>

#include "openmc/constants.h"
#include "openmc/vector.h"

namespace openmc::recoil {

inline Direction momentum_from_kinetic_energy(double mass, double E, Direction u)
{
  if (mass <= 0.0 || E <= 0.0) {
    return {};
  }
  return std::sqrt(2.0 * mass * E) * u;
}

inline Direction neutron_momentum(double E, Direction u)
{
  return momentum_from_kinetic_energy(MASS_NEUTRON_EV, E, u);
}

inline double kinetic_energy_from_momentum2(double p2, double mass)
{
  if (p2 <= 0.0 || mass <= 0.0) {
    return 0.0;
  }
  return p2 / (2.0 * mass);
}

inline double max_elastic_recoil_energy(double E, double target_awr)
{
  if (E <= 0.0 || target_awr <= 0.0) {
    return 0.0;
  }

  double mass_ratio = target_awr + 1.0;
  return 4.0 * target_awr / (mass_ratio * mass_ratio) * E;
}

} // namespace openmc::recoil

#endif // OPENMC_RECOIL_H
