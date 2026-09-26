#include "openmc/surface_periodic_spline.h"

#include "openmc/settings.h"
#include "openmc/surface.h"
#include "stellarcsg/coefficient_file.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <set>
#include <string>
#include <unordered_map>

namespace {

int failures = 0;

void check(bool condition, const char* message)
{
  if (!condition) {
    ++failures;
    std::cerr << "FAIL: " << message << '\n';
  }
}

stellarcsg::PeriodicSplineSurfaceData torus_data()
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.content_id = "openmc-adapter-torus-v1";
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

int main()
{
  const std::string filename = "openmc_stellarcsg_adapter_test.h5";
  stellarcsg::write_periodic_spline_surface_hdf5(filename,
    "/surfaces/torus", torus_data(), true,
    stellarcsg::CoefficientFileMode::truncate);

  openmc::settings::path_input = "";
  pugi::xml_document document;
  const std::string xml =
    "<geometry><surface id='901' type='periodic-spline' "
    "data_file='" + filename + "' dataset='/surfaces/torus' "
    "content_id='openmc-adapter-torus-v1' solver='reference'/></geometry>";
  check(static_cast<bool>(document.load_string(xml.c_str())),
    "parse adapter test XML");

  std::set<std::pair<int, int>> periodic_pairs;
  std::unordered_map<int, double> albedo_map;
  std::unordered_map<int, int> periodic_sense_map;
  openmc::read_surfaces(document.child("geometry"), periodic_pairs,
    albedo_map, periodic_sense_map);
  check(openmc::model::surfaces.size() == 1,
    "OpenMC parser creates one periodic-spline surface");
  auto* surface = dynamic_cast<openmc::SurfacePeriodicSpline*>(
    openmc::model::surfaces.front().get());
  check(surface != nullptr, "parsed surface has experimental wrapper type");
  if (surface != nullptr) {
    check(std::abs(surface->evaluate({6.0, 0.0, 0.0})) < 1.0e-12,
      "surface evaluate matches exact torus point");
    check(std::abs(surface->distance({7.0, 0.0, 0.0},
      {-1.0, 0.0, 0.0}, false) - 1.0) < 3.0e-8,
      "surface distance matches exact radial torus crossing");
    const auto normal = surface->normal({6.0, 0.0, 0.0});
    check(std::abs(normal.x - 1.0) < 1.0e-12,
      "surface normal points outward");
    const auto box = surface->bounding_box(false);
    check(box.min.x <= -6.0 && box.max.x >= 6.0,
      "negative half-space has finite conservative bounds");
  }

  openmc::free_memory_surfaces();
  std::remove(filename.c_str());
  if (failures != 0) return EXIT_FAILURE;
  std::cout << "OpenMC periodic-spline adapter test passed\n";
  return EXIT_SUCCESS;
}
