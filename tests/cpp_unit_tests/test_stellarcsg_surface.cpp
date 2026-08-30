#include <catch2/catch_test_macros.hpp>

#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/surface_periodic_spline.h"
#include "stellarcsg/coefficient_file.hpp"

#include <cmath>
#include <cstdio>
#include <set>
#include <string>
#include <unordered_map>

namespace {

stellarcsg::PeriodicSplineSurfaceData torus_data()
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.content_id = "openmc-native-test";
  data.n_field_periods = 1;
  data.axis_r_coefficients.assign(8, 5.0);
  data.axis_z_coefficients.assign(8, 0.0);
  data.n_theta = 12;
  data.n_phi = 8;
  data.radius_coefficients.assign(data.n_theta * data.n_phi, 1.0);
  data.characteristic_length = 6.0;
  return data;
}

} // namespace

TEST_CASE("native periodic spline surface", "[stellarcsg]")
{
  const std::string filename = "openmc_stellarcsg_native_test.h5";
  const auto data = torus_data();
  stellarcsg::write_periodic_spline_surface_hdf5(filename,
    "/surfaces/torus", data, true,
    stellarcsg::CoefficientFileMode::truncate);

  openmc::settings::path_input = "";
  pugi::xml_document document;
  const std::string xml =
    "<geometry><surface id='901' type='periodic-spline' data_file='" +
    filename + "' dataset='/surfaces/torus' content_id='" + data.content_id +
    "' solver='reference' units='cm'/></geometry>";
  REQUIRE(document.load_string(xml.c_str()));

  std::set<std::pair<int, int>> periodic_pairs;
  std::unordered_map<int, double> albedo_map;
  std::unordered_map<int, int> periodic_sense_map;
  openmc::read_surfaces(document.child("geometry"), periodic_pairs, albedo_map,
    periodic_sense_map);
  REQUIRE(openmc::model::surfaces.size() == 1);
  auto* surface = dynamic_cast<openmc::SurfacePeriodicSpline*>(
    openmc::model::surfaces.front().get());
  REQUIRE(surface != nullptr);
  CHECK(std::abs(surface->evaluate({6.0, 0.0, 0.0})) < 1.0e-12);
  CHECK(std::abs(surface->distance(
          {7.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false) -
        1.0) < 3.0e-8);
  const auto normal = surface->normal({6.0, 0.0, 0.0});
  CHECK(std::abs(normal.x - 1.0) < 1.0e-12);
  const auto box = surface->bounding_box(false);
  CHECK(box.min.x <= -6.0);
  CHECK(box.max.x >= 6.0);

  openmc::free_memory_surfaces();
  std::remove(filename.c_str());
}
