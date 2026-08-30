#include "stellarcsg/coefficient_file.hpp"
#include "stellarcsg/compiled_periodic_surface.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool condition, const std::string& message)
{
  if (!condition) {
    ++failures;
    std::cerr << "FAIL: " << message << '\n';
  }
}

void check_near(double actual, double expected, double tolerance,
  const std::string& message)
{
  if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance) {
    ++failures;
    std::cerr << "FAIL: " << message << " actual=" << actual
              << " expected=" << expected << " tolerance=" << tolerance
              << '\n';
  }
}

stellarcsg::PeriodicSplineSurfaceData make_torus_data()
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.content_id = "compiled-torus-v1";
  data.n_field_periods = 1;
  data.axis_r_coefficients.assign(8, 5.0);
  data.axis_z_coefficients.assign(8, 0.0);
  data.n_theta = 12;
  data.n_phi = 8;
  data.radius_coefficients.assign(data.n_theta * data.n_phi, 1.0);
  data.characteristic_length = 6.0;
  return data;
}

void test_compiled_torus()
{
  const stellarcsg::CompiledPeriodicSplineSurface surface {make_torus_data()};
  check_near(surface.evaluate({6.0, 0.0, 0.0}), 0.0, 1.0e-12,
    "compiled torus surface value");
  check(surface.evaluate({5.0, 0.0, 0.0}) < 0.0,
    "reference axis is inside the radial half-space");
  check(surface.evaluate({7.0, 0.0, 0.0}) > 0.0,
    "point outside torus is positive");

  const auto normal = surface.normal({6.0, 0.0, 0.0});
  check_near(normal.x, 1.0, 1.0e-12, "compiled torus outward normal x");
  check_near(normal.y, 0.0, 1.0e-12, "compiled torus outward normal y");
  check_near(normal.z, 0.0, 1.0e-12, "compiled torus outward normal z");

  stellarcsg::RootSearchOptions options;
  options.initial_subdivisions = 96;
  options.max_refinement_levels = 6;
  const auto crossing = surface.distance_reference(
    {7.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false, options);
  check(crossing.found, "compiled torus radial crossing is found");
  if (crossing.found) {
    check_near(crossing.distance, 1.0, 3.0e-8,
      "compiled torus radial crossing distance");
  }

  stellarcsg::FastDistanceOptions fast_options;
  fast_options.fallback_to_reference = false;
  const auto fast_crossing = surface.distance_fast(
    {7.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false, fast_options);
  check(fast_crossing.found, "compiled torus fast radial crossing is found");
  if (fast_crossing.found) {
    check_near(fast_crossing.distance, 1.0, 3.0e-8,
      "compiled torus fast radial crossing distance");
    check(!fast_crossing.used_fallback,
      "compiled torus fast radial crossing avoids fallback");
  }

  const auto box = surface.bounding_box();
  check(box.lower.x <= -6.0 && box.upper.x >= 6.0,
    "compiled torus conservative xy bounds");
  check(box.lower.z <= -1.0 && box.upper.z >= 1.0,
    "compiled torus conservative z bounds");
}

void test_moving_axis_and_helical_radius()
{
  auto data = make_torus_data();
  data.content_id = "compiled-helical-v1";
  data.n_field_periods = 5;
  const std::size_t n_axis = 16;
  data.axis_r_coefficients.resize(n_axis);
  data.axis_z_coefficients.resize(n_axis);
  for (std::size_t i = 0; i < n_axis; ++i) {
    const double phase = 2.0 * 3.141592653589793238462643383279502884
                         * static_cast<double>(i) / static_cast<double>(n_axis);
    data.axis_r_coefficients[i] = 5.0 + 0.08 * std::cos(phase);
    data.axis_z_coefficients[i] = 0.05 * std::sin(phase);
  }
  data.n_theta = 24;
  data.n_phi = 20;
  data.radius_coefficients.resize(data.n_theta * data.n_phi);
  for (std::size_t i = 0; i < data.n_theta; ++i) {
    const double theta = 2.0 * 3.141592653589793238462643383279502884
                         * static_cast<double>(i) / static_cast<double>(data.n_theta);
    for (std::size_t j = 0; j < data.n_phi; ++j) {
      const double psi = 2.0 * 3.141592653589793238462643383279502884
                         * static_cast<double>(j) / static_cast<double>(data.n_phi);
      data.radius_coefficients[i * data.n_phi + j] =
        1.0 + 0.10 * std::cos(2.0 * theta - psi);
    }
  }

  const stellarcsg::CompiledPeriodicSplineSurface surface {std::move(data)};
  for (int k = 0; k < 20; ++k) {
    const double phi = 2.0 * 3.141592653589793238462643383279502884
                       * static_cast<double>(k) / 20.0;
    const stellarcsg::Vec3 outside {6.5 * std::cos(phi),
      6.5 * std::sin(phi), 0.0};
    check(surface.evaluate(outside) > 0.0,
      "moving-axis test point remains outside");
  }
}

#ifdef STELLARCSG_HAS_HDF5
void test_hdf5_round_trip()
{
  const std::string filename = "stellarcsg_compiled_surface_test.h5";
  const auto source = make_torus_data();
  stellarcsg::write_periodic_spline_surface_hdf5(filename,
    "/surfaces/torus", source, true,
    stellarcsg::CoefficientFileMode::truncate);
  const auto loaded = stellarcsg::read_periodic_spline_surface_hdf5(
    filename, "/surfaces/torus", source.content_id);
  check(loaded.content_id == source.content_id, "HDF5 content ID round trip");
  check(loaded.n_field_periods == source.n_field_periods,
    "HDF5 field-period round trip");
  check(loaded.axis_r_coefficients == source.axis_r_coefficients,
    "HDF5 axis R round trip");
  check(loaded.radius_coefficients == source.radius_coefficients,
    "HDF5 radius coefficient round trip");

  bool mismatch_rejected = false;
  try {
    (void) stellarcsg::read_periodic_spline_surface_hdf5(
      filename, "/surfaces/torus", "wrong-content-id");
  } catch (const std::runtime_error&) {
    mismatch_rejected = true;
  }
  check(mismatch_rejected, "HDF5 content-ID mismatch is rejected");
  std::remove(filename.c_str());
}
#endif

} // namespace

int main()
{
  try {
    test_compiled_torus();
    test_moving_axis_and_helical_radius();
#ifdef STELLARCSG_HAS_HDF5
    test_hdf5_round_trip();
#endif
  } catch (const std::exception& error) {
    ++failures;
    std::cerr << "UNCAUGHT EXCEPTION: " << error.what() << '\n';
  }

  if (failures != 0) {
    std::cerr << failures << " compiled-surface test assertion(s) failed\n";
    return EXIT_FAILURE;
  }
  std::cout << "All StellarCSG compiled-surface tests passed\n";
  return EXIT_SUCCESS;
}
