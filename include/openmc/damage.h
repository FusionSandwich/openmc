//! \file damage.h
//! Damage energy models

#ifndef OPENMC_DAMAGE_H
#define OPENMC_DAMAGE_H

namespace openmc {

//! Damage model used for secondary-particle production tallies
enum class DamageModel { NONE, NRT, RECOIL_ENERGY };

//! Calculate damage energy using the Lindhard/Robinson partition function.
//!
//! \param[in] E Recoil kinetic energy in [eV]
//! \param[in] Z_R Recoil atomic number
//! \param[in] A_R Recoil mass number
//! \param[in] Z_L Lattice atomic number
//! \param[in] A_L Lattice mass number
//! \return Damage energy in [eV]
double lindhard_partition(double E, int Z_R, int A_R, int Z_L, int A_L);

} // namespace openmc

#endif // OPENMC_DAMAGE_H
