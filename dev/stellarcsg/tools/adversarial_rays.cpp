#include "stellarcsg/compiled_periodic_surface.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <string>
#include <vector>

namespace {

constexpr double pi = 3.141592653589793238462643383279502884;

struct Ray {
  stellarcsg::Vec3 origin;
  stellarcsg::Vec3 direction;
  bool coincident {false};
  std::string category;
};

stellarcsg::PeriodicSplineSurfaceData make_surface(bool helical)
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.content_id = helical ? "adversarial-helical-v1" : "adversarial-torus-v1";
  data.n_field_periods = helical ? 5 : 1;
  constexpr std::size_t n_axis = 24;
  data.axis_r_coefficients.resize(n_axis);
  data.axis_z_coefficients.resize(n_axis);
  for (std::size_t i = 0; i < n_axis; ++i) {
    const double psi = 2.0 * pi * static_cast<double>(i)
                       / static_cast<double>(n_axis);
    data.axis_r_coefficients[i] = 500.0 + (helical ? 8.0 * std::cos(psi) : 0.0);
    data.axis_z_coefficients[i] = helical ? 5.0 * std::sin(psi) : 0.0;
  }
  data.n_theta = 40;
  data.n_phi = 32;
  data.radius_coefficients.resize(data.n_theta * data.n_phi);
  for (std::size_t i = 0; i < data.n_theta; ++i) {
    const double theta = 2.0 * pi * static_cast<double>(i)
                         / static_cast<double>(data.n_theta);
    for (std::size_t j = 0; j < data.n_phi; ++j) {
      const double psi = 2.0 * pi * static_cast<double>(j)
                         / static_cast<double>(data.n_phi);
      double radius = 100.0;
      if (helical) {
        radius += 12.0 * std::cos(2.0 * theta - psi)
                  + 4.0 * std::cos(3.0 * theta + 2.0 * psi);
      }
      data.radius_coefficients[i * data.n_phi + j] = radius;
    }
  }
  data.characteristic_length = 620.0;
  return data;
}

stellarcsg::Vec3 unit_vector(std::mt19937_64& generator)
{
  std::uniform_real_distribution<double> uniform(-1.0, 1.0);
  while (true) {
    const stellarcsg::Vec3 value {uniform(generator), uniform(generator),
      uniform(generator)};
    const double magnitude = stellarcsg::norm(value);
    if (magnitude > 1.0e-12 && magnitude <= 1.0) return value / magnitude;
  }
}

std::vector<Ray> make_rays(std::size_t random_count)
{
  std::vector<Ray> rays;
  rays.reserve(random_count + 500);
  std::mt19937_64 generator(0x5A17C5A6ULL);
  std::uniform_real_distribution<double> xy(-640.0, 640.0);
  std::uniform_real_distribution<double> z(-150.0, 150.0);

  for (std::size_t i = 0; i < random_count; ++i) {
    rays.push_back({{xy(generator), xy(generator), z(generator)},
      unit_vector(generator), false, "random"});
  }

  // Exact radial crossings distributed over all seams and high-curvature
  // phases. They stress atan2 wrapping and field-period replication.
  for (int iphi = 0; iphi < 40; ++iphi) {
    const double phi = (2.0 * pi * static_cast<double>(iphi) / 40.0)
                       + (iphi % 2 == 0 ? 1.0e-13 : -1.0e-13);
    for (int itheta = 0; itheta < 20; ++itheta) {
      const double theta = 2.0 * pi * static_cast<double>(itheta) / 20.0;
      constexpr double rho = 150.0;
      const double R = 500.0 + rho * std::cos(theta);
      const stellarcsg::Vec3 direction {
        -std::cos(theta) * std::cos(phi),
        -std::cos(theta) * std::sin(phi), -std::sin(theta)};
      rays.push_back({{R * std::cos(phi), R * std::sin(phi),
                         rho * std::sin(theta)},
        direction, false, "radial-seam"});
    }
  }

  // Analytic tangencies to the circular torus. For the helical case these are
  // simply difficult near-grazing rays and are still compared to the reference.
  for (int i = 0; i < 64; ++i) {
    const double phi = 2.0 * pi * static_cast<double>(i) / 64.0;
    const stellarcsg::Vec3 point {600.0 * std::cos(phi),
      600.0 * std::sin(phi), 0.0};
    const stellarcsg::Vec3 tangent {-std::sin(phi), std::cos(phi), 0.0};
    rays.push_back({point - 37.25 * tangent, tangent, false, "tangent"});
    const auto normal = stellarcsg::Vec3 {std::cos(phi), std::sin(phi), 0.0};
    rays.push_back({point + 1.0e-8 * normal, tangent + 1.0e-10 * normal,
      false, "near-tangent"});
  }

  // Coincident starts exercise the crossing push and next-surface behavior.
  for (int i = 0; i < 32; ++i) {
    const double phi = 2.0 * pi * static_cast<double>(i) / 32.0;
    const stellarcsg::Vec3 point {600.0 * std::cos(phi),
      600.0 * std::sin(phi), 0.0};
    const stellarcsg::Vec3 normal {std::cos(phi), std::sin(phi), 0.0};
    rays.push_back({point, normal, true, "coincident-out"});
    rays.push_back({point, -normal, true, "coincident-in"});
  }
  return rays;
}

struct Summary {
  std::size_t total {0};
  std::size_t reference_hits {0};
  std::size_t fast_hits {0};
  std::size_t classification_mismatches {0};
  std::size_t distance_mismatches {0};
  std::size_t fallback_hits {0};
  std::size_t fallback_failures {0};
  double maximum_distance_error {0.0};
  double maximum_fast_residual {0.0};
  std::uint64_t fast_function_evaluations {0};
  std::uint64_t reference_function_evaluations {0};
  double fast_seconds {0.0};
  double reference_seconds {0.0};
};

Summary run_case(const stellarcsg::CompiledPeriodicSplineSurface& surface,
  const std::vector<Ray>& rays)
{
  Summary summary;
  summary.total = rays.size();

  stellarcsg::FastDistanceOptions fast_options;
  fast_options.fallback_to_reference = false;
  fast_options.minimum_scan_intervals = 12;
  fast_options.maximum_scan_intervals = 192;
  fast_options.maximum_scan_step_fraction = 0.35;
  fast_options.absolute_f_tolerance = 2.0e-9;
  fast_options.absolute_t_tolerance = 2.0e-10;

  stellarcsg::RootSearchOptions reference_options;
  reference_options.initial_subdivisions = 128;
  reference_options.max_refinement_levels = 6;
  reference_options.absolute_f_tolerance = 2.0e-9;
  reference_options.absolute_t_tolerance = 2.0e-10;
  reference_options.require_refinement_stability = true;

  std::vector<stellarcsg::DistanceResult> fast_results;
  fast_results.reserve(rays.size());
  auto start = std::chrono::steady_clock::now();
  for (const auto& ray : rays) {
    fast_results.push_back(surface.distance_fast(
      ray.origin, ray.direction, ray.coincident, fast_options));
  }
  auto stop = std::chrono::steady_clock::now();
  summary.fast_seconds = std::chrono::duration<double>(stop - start).count();

  std::vector<stellarcsg::DistanceResult> reference_results;
  reference_results.reserve(rays.size());
  start = std::chrono::steady_clock::now();
  for (const auto& ray : rays) {
    reference_results.push_back(surface.distance_reference(
      ray.origin, ray.direction, ray.coincident, reference_options));
  }
  stop = std::chrono::steady_clock::now();
  summary.reference_seconds = std::chrono::duration<double>(stop - start).count();

  for (std::size_t i = 0; i < rays.size(); ++i) {
    const auto& fast = fast_results[i];
    const auto& reference = reference_results[i];
    summary.reference_hits += reference.found ? 1U : 0U;
    summary.fast_hits += fast.found ? 1U : 0U;
    summary.fast_function_evaluations +=
      static_cast<std::uint64_t>(fast.root_diagnostics.function_evaluations);
    summary.reference_function_evaluations +=
      static_cast<std::uint64_t>(reference.root_diagnostics.function_evaluations);
    if (fast.found) summary.maximum_fast_residual = std::max(
      summary.maximum_fast_residual, fast.residual);

    if (fast.found != reference.found) {
      ++summary.classification_mismatches;
      stellarcsg::FastDistanceOptions fallback = fast_options;
      fallback.fallback_to_reference = true;
      fallback.fallback_options = reference_options;
      const auto recovered = surface.distance_fast(
        rays[i].origin, rays[i].direction, rays[i].coincident, fallback);
      if (recovered.found == reference.found
          && (!reference.found
              || std::abs(recovered.distance - reference.distance) <= 2.0e-6)) {
        ++summary.fallback_hits;
      } else {
        ++summary.fallback_failures;
      }
      continue;
    }
    if (!fast.found) continue;
    const double error = std::abs(fast.distance - reference.distance);
    summary.maximum_distance_error = std::max(summary.maximum_distance_error, error);
    if (error > 2.0e-6) ++summary.distance_mismatches;
  }
  return summary;
}

void print_summary(const char* name, const Summary& value, bool final)
{
  const double average_fast = value.total > 0
    ? static_cast<double>(value.fast_function_evaluations)
      / static_cast<double>(value.total)
    : 0.0;
  const double average_reference = value.total > 0
    ? static_cast<double>(value.reference_function_evaluations)
      / static_cast<double>(value.total)
    : 0.0;
  std::cout << "    \"" << name << "\": {\n"
            << "      \"total_rays\": " << value.total << ",\n"
            << "      \"reference_hits\": " << value.reference_hits << ",\n"
            << "      \"fast_hits\": " << value.fast_hits << ",\n"
            << "      \"classification_mismatches\": "
            << value.classification_mismatches << ",\n"
            << "      \"distance_mismatches\": "
            << value.distance_mismatches << ",\n"
            << "      \"fallback_recoveries\": " << value.fallback_hits << ",\n"
            << "      \"fallback_failures\": " << value.fallback_failures << ",\n"
            << "      \"maximum_distance_error_cm\": "
            << value.maximum_distance_error << ",\n"
            << "      \"maximum_fast_residual_cm\": "
            << value.maximum_fast_residual << ",\n"
            << "      \"average_fast_function_evaluations\": "
            << average_fast << ",\n"
            << "      \"average_reference_function_evaluations\": "
            << average_reference << ",\n"
            << "      \"fast_seconds\": " << value.fast_seconds << ",\n"
            << "      \"reference_seconds\": " << value.reference_seconds << ",\n"
            << "      \"speed_ratio_reference_over_fast\": "
            << (value.fast_seconds > 0.0
                  ? value.reference_seconds / value.fast_seconds : 0.0)
            << "\n    }" << (final ? "\n" : ",\n");
}

} // namespace

int main(int argc, char** argv)
{
  std::size_t random_count = 2000;
  if (argc > 1) random_count = static_cast<std::size_t>(std::stoull(argv[1]));
  const auto rays = make_rays(random_count);
  const stellarcsg::CompiledPeriodicSplineSurface torus {make_surface(false)};
  const stellarcsg::CompiledPeriodicSplineSurface helical {make_surface(true)};

  const auto torus_summary = run_case(torus, rays);
  const auto helical_summary = run_case(helical, rays);
  const bool passed = torus_summary.classification_mismatches == 0
                      && helical_summary.classification_mismatches == 0
                      && torus_summary.distance_mismatches == 0
                      && helical_summary.distance_mismatches == 0
                      && torus_summary.fallback_failures == 0
                      && helical_summary.fallback_failures == 0;

  std::cout << std::setprecision(17)
            << "{\n  \"schema_version\": 1,\n"
            << "  \"random_ray_count\": " << random_count << ",\n"
            << "  \"all_fallback_results_match_reference\": "
            << (passed ? "true" : "false") << ",\n"
            << "  \"cases\": {\n";
  print_summary("circular_torus", torus_summary, false);
  print_summary("helical_surface", helical_summary, true);
  std::cout << "  }\n}\n";
  return passed ? EXIT_SUCCESS : EXIT_FAILURE;
}
