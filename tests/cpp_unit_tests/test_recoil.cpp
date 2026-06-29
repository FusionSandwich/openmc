#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>

#include <cmath>

#include "openmc/constants.h"
#include "openmc/position.h"
#include "openmc/recoil.h"
#include "openmc/settings.h"

namespace {

openmc::Direction direction_from_mu(double mu)
{
  return {std::sqrt(1.0 - mu * mu), 0.0, mu};
}

void lab_elastic_outgoing(double E_in, double target_awr, double mu_cm,
  double& E_out, openmc::Direction& u_out)
{
  openmc::Direction u_cm = direction_from_mu(mu_cm);
  openmc::Direction v_cm {0.0, 0.0, std::sqrt(E_in) / (target_awr + 1.0)};
  openmc::Direction v_neutron =
    v_cm + (target_awr / (target_awr + 1.0)) * std::sqrt(E_in) * u_cm;

  E_out = v_neutron.dot(v_neutron);
  u_out = E_out > 0.0 ? v_neutron / std::sqrt(E_out) : openmc::Direction {};
}

} // namespace

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

TEST_CASE("Elastic recoil energy from momentum balance is bounded")
{
  double E_in = 14.1e6;
  openmc::Direction u_in {0.0, 0.0, 1.0};

  for (double target_awr : {1.0, 16.0, 56.0, 63.0}) {
    double max_recoil =
      openmc::recoil::max_elastic_recoil_energy(E_in, target_awr);

    for (double mu_cm : {-1.0, -0.25, 0.5, 1.0}) {
      double E_out;
      openmc::Direction u_out;
      lab_elastic_outgoing(E_in, target_awr, mu_cm, E_out, u_out);

      double E_recoil = openmc::recoil::elastic_recoil_energy(
        E_in, u_in, E_out, u_out, target_awr);

      REQUIRE(E_recoil >= 0.0);
      REQUIRE(E_recoil <= max_recoil * (1.0 + 1e-12));
      REQUIRE(E_recoil == Catch::Approx(E_in - E_out).margin(1e-8));
    }
  }
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

TEST_CASE("Recoil production is disabled by default")
{
  REQUIRE_FALSE(openmc::settings::recoil_production);
}
