#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>

#include "openmc/damage.h"

TEST_CASE("Lindhard partition rejects nonphysical inputs")
{
  REQUIRE(openmc::lindhard_partition(0.0, 26, 56, 26, 56) == 0.0);
  REQUIRE(openmc::lindhard_partition(-1.0, 26, 56, 26, 56) == 0.0);
  REQUIRE(openmc::lindhard_partition(1.0e5, 0, 56, 26, 56) == 0.0);
  REQUIRE(openmc::lindhard_partition(1.0e5, 26, 0, 26, 56) == 0.0);
  REQUIRE(openmc::lindhard_partition(1.0e5, 26, 56, 0, 56) == 0.0);
  REQUIRE(openmc::lindhard_partition(1.0e5, 26, 56, 26, 0) == 0.0);
}

TEST_CASE("Lindhard partition gives bounded damage energy")
{
  for (double energy : {1.0e3, 1.0e5, 1.0e6}) {
    double damage = openmc::lindhard_partition(energy, 26, 56, 26, 56);

    REQUIRE(damage > 0.0);
    REQUIRE(damage < energy);
  }
}

TEST_CASE("Lindhard partition reference values")
{
  REQUIRE(openmc::lindhard_partition(1.0e3, 26, 56, 26, 56) ==
    Catch::Approx(814.77640736389355));
  REQUIRE(openmc::lindhard_partition(1.0e5, 26, 56, 26, 56) ==
    Catch::Approx(61865.089085593674));
  REQUIRE(openmc::lindhard_partition(1.0e6, 26, 56, 26, 56) ==
    Catch::Approx(351586.31153058767));
  REQUIRE(openmc::lindhard_partition(1.0e6, 2, 4, 26, 56) ==
    Catch::Approx(5503.7665662392474));
  REQUIRE(openmc::lindhard_partition(1.0e6, 26, 56, 2, 4) ==
    Catch::Approx(335906.63287178514));
}
