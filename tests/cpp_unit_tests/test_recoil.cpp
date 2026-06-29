#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>

#include "openmc/constants.h"
#include "openmc/recoil.h"
#include "openmc/vector.h"

TEST_CASE("Elastic recoil energy bound")
{
  double E = 14.1e6;

  REQUIRE(openmc::recoil::max_elastic_recoil_energy(E, 1.0) ==
    Catch::Approx(E));
  REQUIRE(openmc::recoil::max_elastic_recoil_energy(E, 16.0) ==
    Catch::Approx(4.0 * 16.0 / (17.0 * 17.0) * E));
  REQUIRE(openmc::recoil::max_elastic_recoil_energy(E, 56.0) ==
    Catch::Approx(4.0 * 56.0 / (57.0 * 57.0) * E));
  REQUIRE(openmc::recoil::max_elastic_recoil_energy(E, 63.0) ==
    Catch::Approx(4.0 * 63.0 / (64.0 * 64.0) * E));

  REQUIRE(openmc::recoil::max_elastic_recoil_energy(0.0, 56.0) == 0.0);
  REQUIRE(openmc::recoil::max_elastic_recoil_energy(E, 0.0) == 0.0);
}

TEST_CASE("Recoil kinetic energy from momentum")
{
  openmc::Direction u {1.0, 0.0, 0.0};
  double E = 1.0e6;

  auto p = openmc::recoil::neutron_momentum(E, u);
  REQUIRE(openmc::recoil::kinetic_energy_from_momentum2(
            p.dot(p), openmc::MASS_NEUTRON_EV) == Catch::Approx(E));

  REQUIRE(openmc::recoil::kinetic_energy_from_momentum2(0.0,
            openmc::MASS_NEUTRON_EV) == 0.0);
  REQUIRE(openmc::recoil::kinetic_energy_from_momentum2(p.dot(p), 0.0) == 0.0);
}
