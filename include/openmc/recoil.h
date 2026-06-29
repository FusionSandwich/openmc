//! \file recoil.h
//! Recoil kinematics helpers

#ifndef OPENMC_RECOIL_H
#define OPENMC_RECOIL_H

#include <cmath>

#include "openmc/constants.h"
#include "openmc/position.h"

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

inline Direction elastic_recoil_momentum(
  double E_in, Direction u_in, double E_out, Direction u_out)
{
  return neutron_momentum(E_in, u_in) - neutron_momentum(E_out, u_out);
}

inline double elastic_recoil_energy(
  double E_in, Direction u_in, double E_out, Direction u_out, double target_awr)
{
  Direction p_recoil = elastic_recoil_momentum(E_in, u_in, E_out, u_out);
  return kinetic_energy_from_momentum2(
    p_recoil.dot(p_recoil), target_awr * MASS_NEUTRON_EV);
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
