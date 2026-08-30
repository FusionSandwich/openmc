#include "openmc/surface_periodic_spline.h"

#include "openmc/constants.h"
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "stellarcsg/coefficient_file.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <set>
#include <string>
#include <unordered_map>

namespace {

constexpr double pi = 3.141592653589793238462643383279502884;

struct ComparisonSummary {
  int point_samples {0};
  int ray_samples {0};
  int sense_mismatches {0};
  int ray_classification_mismatches {0};
  int ray_distance_mismatches {0};
  double maximum_distance_error {0.0};
  double maximum_normal_angle {0.0};
  double builtin_ns_per_ray {0.0};
  double custom_ns_per_ray {0.0};
};

stellarcsg::PeriodicSplineSurfaceData torus_data()
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.content_id = "step4-matched-ztorus-v1";
  data.n_field_periods = 1;
  data.axis_r_coefficients.assign(16, 500.0);
  data.axis_z_coefficients.assign(16, 0.0);
  data.n_theta = 32;
  data.n_phi = 24;
  data.radius_coefficients.assign(data.n_theta * data.n_phi, 100.0);
  data.characteristic_length = 620.0;
  return data;
}

openmc::Direction normalized(openmc::Direction value)
{
  const double magnitude = std::sqrt(value.x * value.x + value.y * value.y
                                     + value.z * value.z);
  return {value.x / magnitude, value.y / magnitude, value.z / magnitude};
}

double dot(openmc::Direction a, openmc::Direction b)
{
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

ComparisonSummary run_comparison(openmc::Surface& builtin,
  openmc::Surface& custom, int point_samples, int ray_samples)
{
  ComparisonSummary summary;
  summary.point_samples = point_samples;
  summary.ray_samples = ray_samples;

  std::mt19937_64 generator(0x5343545f5a544f52ULL);
  std::uniform_real_distribution<double> xy(-720.0, 720.0);
  std::uniform_real_distribution<double> z(-180.0, 180.0);
  std::normal_distribution<double> normal(0.0, 1.0);
  std::uniform_real_distribution<double> angle(0.0, 2.0 * pi);

  for (int i = 0; i < point_samples; ++i) {
    const openmc::Position point {xy(generator), xy(generator), z(generator)};
    const bool builtin_positive = builtin.evaluate(point) > 0.0;
    const bool custom_positive = custom.evaluate(point) > 0.0;
    if (builtin_positive != custom_positive) ++summary.sense_mismatches;
  }

  for (int i = 0; i < 4000; ++i) {
    const double theta = angle(generator);
    const double phi = angle(generator);
    const double R = 500.0 + 100.0 * std::cos(theta);
    const openmc::Position point {
      R * std::cos(phi), R * std::sin(phi), 100.0 * std::sin(theta)};
    auto n0 = normalized(builtin.normal(point));
    auto n1 = normalized(custom.normal(point));
    const double cosine = std::clamp(dot(n0, n1), -1.0, 1.0);
    summary.maximum_normal_angle =
      std::max(summary.maximum_normal_angle, std::acos(cosine));
  }

  struct Ray {
    openmc::Position origin;
    openmc::Direction direction;
  };
  std::vector<Ray> rays;
  rays.reserve(ray_samples);
  for (int i = 0; i < ray_samples; ++i) {
    openmc::Direction direction {normal(generator), normal(generator), normal(generator)};
    direction = normalized(direction);
    rays.push_back({{xy(generator), xy(generator), z(generator)}, direction});
  }

  volatile double sink = 0.0;
  auto start = std::chrono::steady_clock::now();
  for (const auto& ray : rays) sink += builtin.distance(ray.origin, ray.direction, false);
  auto stop = std::chrono::steady_clock::now();
  summary.builtin_ns_per_ray = std::chrono::duration<double, std::nano>(stop - start).count()
                               / static_cast<double>(ray_samples);
  start = std::chrono::steady_clock::now();
  for (const auto& ray : rays) sink += custom.distance(ray.origin, ray.direction, false);
  stop = std::chrono::steady_clock::now();
  summary.custom_ns_per_ray = std::chrono::duration<double, std::nano>(stop - start).count()
                              / static_cast<double>(ray_samples);
  if (sink == -1.0) std::cerr << sink;

  for (const auto& ray : rays) {
    const double d0 = builtin.distance(ray.origin, ray.direction, false);
    const double d1 = custom.distance(ray.origin, ray.direction, false);
    const bool hit0 = d0 < openmc::INFTY;
    const bool hit1 = d1 < openmc::INFTY;
    if (hit0 != hit1) {
      ++summary.ray_classification_mismatches;
      continue;
    }
    if (!hit0) continue;
    const double error = std::abs(d0 - d1);
    summary.maximum_distance_error = std::max(summary.maximum_distance_error, error);
    if (error > 3.0e-6) ++summary.ray_distance_mismatches;
  }
  return summary;
}

} // namespace

int main(int argc, char** argv)
{
  const int point_samples = argc > 1 ? std::max(1000, std::atoi(argv[1])) : 20000;
  const int ray_samples = argc > 2 ? std::max(1000, std::atoi(argv[2])) : 10000;
  const std::string filename = "step4_periodic_spline_vs_ztorus.h5";
  stellarcsg::write_periodic_spline_surface_hdf5(filename,
    "/surfaces/torus", torus_data(), true,
    stellarcsg::CoefficientFileMode::truncate);

  openmc::settings::path_input = "";
  pugi::xml_document document;
  const std::string xml =
    "<geometry>"
    "<surface id='4101' type='z-torus' coeffs='0 0 0 500 100 100'/>"
    "<surface id='4102' type='periodic-spline' data_file='" + filename
    + "' dataset='/surfaces/torus' content_id='step4-matched-ztorus-v1' "
      "solver='fast'/>"
      "</geometry>";
  if (!document.load_string(xml.c_str())) return EXIT_FAILURE;

  std::set<std::pair<int, int>> periodic_pairs;
  std::unordered_map<int, double> albedo_map;
  std::unordered_map<int, int> periodic_sense_map;
  openmc::read_surfaces(document.child("geometry"), periodic_pairs,
    albedo_map, periodic_sense_map);
  if (openmc::model::surfaces.size() != 2) return EXIT_FAILURE;

  auto& builtin = *openmc::model::surfaces[0];
  auto& custom = *openmc::model::surfaces[1];
  const auto result = run_comparison(builtin, custom, point_samples, ray_samples);
  const bool passed = result.sense_mismatches == 0
                      && result.ray_classification_mismatches == 0
                      && result.ray_distance_mismatches == 0
                      && result.maximum_normal_angle <= 3.0e-7;

  std::cout << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"comparison\": \"OpenMC ZTorus versus native periodic-spline\",\n"
            << "  \"point_samples\": " << result.point_samples << ",\n"
            << "  \"ray_samples\": " << result.ray_samples << ",\n"
            << "  \"sense_mismatches\": " << result.sense_mismatches << ",\n"
            << "  \"ray_classification_mismatches\": "
            << result.ray_classification_mismatches << ",\n"
            << "  \"ray_distance_mismatches\": "
            << result.ray_distance_mismatches << ",\n"
            << "  \"maximum_distance_error_cm\": "
            << result.maximum_distance_error << ",\n"
            << "  \"maximum_normal_angle_rad\": "
            << result.maximum_normal_angle << ",\n"
            << "  \"builtin_ns_per_ray\": " << result.builtin_ns_per_ray << ",\n"
            << "  \"custom_ns_per_ray\": " << result.custom_ns_per_ray << ",\n"
            << "  \"custom_to_builtin_time_ratio\": "
            << result.custom_ns_per_ray / result.builtin_ns_per_ray << ",\n"
            << "  \"passed\": " << (passed ? "true" : "false") << "\n"
            << "}\n";

  openmc::free_memory_surfaces();
  std::remove(filename.c_str());
  return passed ? EXIT_SUCCESS : EXIT_FAILURE;
}
