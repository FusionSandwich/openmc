#ifndef OPENMC_REACTION_EVENT_H
#define OPENMC_REACTION_EVENT_H

#include "openmc/position.h"

namespace openmc {

class Particle;
class Nuclide;
class Reaction;

//! Reserve space in the reaction-event bank according to user settings.
void reaction_event_reserve_bank();

//! Write reaction-event data to disk at the end of a run.
void reaction_event_flush_bank();

//! Record exact elastic recoil diagnostics when reaction-event output is enabled.
//!
//! \param p Particle after elastic scattering
//! \param nuc Target nuclide
//! \param E_in Incident neutron energy in [eV]
//! \param u_in Incident neutron direction
//! \param E_recoil Recoil energy in [eV]
//! \param u_recoil Recoil direction
void reaction_event_record_elastic(Particle& p, const Nuclide& nuc,
  double E_in, Direction u_in, double E_recoil, Direction u_recoil);

//! Record a sampled neutron product when reaction-product output is enabled.
//!
//! \param p Particle after scattering
//! \param nuc Target nuclide
//! \param rx Sampled reaction
//! \param E_in Incident neutron energy in [eV]
//! \param u_in Incident neutron direction
//! \param n_products Number of sampled neutron product rows to record
//! \param E_recoil Residual recoil energy in [eV], if available
//! \param u_recoil Residual recoil direction, if available
//! \param has_residual Whether residual recoil information is available
void reaction_event_record_neutron_product(Particle& p, const Nuclide& nuc,
  const Reaction& rx, double E_in, Direction u_in, int n_products,
  double E_recoil, Direction u_recoil, bool has_residual);

} // namespace openmc

#endif // OPENMC_REACTION_EVENT_H
