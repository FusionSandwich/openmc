#include "stellarcsg/compiled_periodic_surface.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr double two_pi =
  2.0 * 3.141592653589793238462643383279502884;

class DeterministicGenerator {
public:
  explicit DeterministicGenerator(std::uint64_t seed) : state_ {seed} {}

  std::uint64_t integer()
  {
    state_ ^= state_ >> 12;
    state_ ^= state_ << 25;
    state_ ^= state_ >> 27;
    return state_ * 2685821657736338717ULL;
  }

  double symmetric()
  {
    constexpr double scale = 1.0 / 9007199254740992.0;
    return 2.0 * (static_cast<double>(integer() >> 11) * scale) - 1.0;
  }

private:
  std::uint64_t state_;
};

stellarcsg::PeriodicSplineSurfaceData torus_data()
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.content_id = "root-campaign-exact-torus";
  data.n_field_periods = 1;
  data.axis_r_coefficients.assign(8, 5.0);
  data.axis_z_coefficients.assign(8, 0.0);
  data.n_theta = 12;
  data.n_phi = 8;
  data.radius_coefficients.assign(data.n_theta * data.n_phi, 1.0);
  data.characteristic_length = 6.0;
  return data;
}

stellarcsg::Vec3 random_direction(DeterministicGenerator& generator)
{
  stellarcsg::Vec3 direction;
  do {
    direction = {generator.symmetric(), generator.symmetric(),
      generator.symmetric()};
  } while (stellarcsg::norm_squared(direction) < 1.0e-12);
  const double nonunit_scale = 0.125 + 7.875
    * (0.5 * (generator.symmetric() + 1.0));
  return nonunit_scale * direction;
}

double mismatch_tolerance(double expected)
{
  return 1.0e-9 * std::max({1.0, 6.0, std::abs(expected)});
}

struct FailureFixture {
  std::uint64_t index;
  const char* kind;
  stellarcsg::Vec3 origin;
  stellarcsg::Vec3 direction;
  bool fast_found;
  double fast_distance;
  bool oracle_found;
  double oracle_distance;
};

} // namespace

int main(int argc, char* argv[])
{
  try {
    const std::uint64_t ray_count = argc > 1
      ? static_cast<std::uint64_t>(std::stoull(argv[1]))
      : 100000ULL;
    const std::uint64_t seed = argc > 2
      ? static_cast<std::uint64_t>(std::stoull(argv[2]))
      : 0x5a17c5a5d00d1234ULL;
    const bool force_general = argc > 3 && std::string {argv[3]} == "general";
    auto surface_data = torus_data();
    surface_data.force_general_solver = force_general;
    const stellarcsg::CompiledPeriodicSplineSurface surface {
      std::move(surface_data)};
    stellarcsg::RootSearchOptions oracle_options;
    oracle_options.initial_subdivisions = 32;
    oracle_options.max_refinement_levels = 4;
    oracle_options.absolute_t_tolerance = 2.0e-12;
    oracle_options.relative_t_tolerance = 2.0e-12;
    oracle_options.absolute_f_tolerance = 2.0e-11;
    oracle_options.derivative_tolerance = 2.0e-11;
    auto adjudication_options = oracle_options;
    adjudication_options.initial_subdivisions = 128;
    adjudication_options.max_refinement_levels = 8;
    adjudication_options.absolute_t_tolerance = 2.0e-13;
    adjudication_options.relative_t_tolerance = 2.0e-13;
    adjudication_options.absolute_f_tolerance = 2.0e-12;
    adjudication_options.derivative_tolerance = 2.0e-12;

    DeterministicGenerator generator {seed};
    std::uint64_t oracle_found = 0;
    std::uint64_t fast_found = 0;
    std::uint64_t missed_roots = 0;
    std::uint64_t false_roots = 0;
    std::uint64_t wrong_nearest = 0;
    std::uint64_t exact_path_count = 0;
    std::uint64_t oracle_adjudications = 0;
    double maximum_distance_error = 0.0;
    double maximum_fast_residual = 0.0;
    std::vector<FailureFixture> failure_fixtures;
    const auto start = std::chrono::steady_clock::now();

    for (std::uint64_t index = 0; index < ray_count; ++index) {
      const stellarcsg::Vec3 origin {
        8.0 * generator.symmetric(),
        8.0 * generator.symmetric(),
        2.0 * generator.symmetric()};
      const auto direction = random_direction(generator);
      const auto fast = surface.distance(origin, direction, false);
      const auto quick_oracle = surface.distance_reference(
        origin, direction, false, oracle_options);
      auto oracle = quick_oracle;
      const bool quick_disagreement = fast.found != quick_oracle.found
        || (fast.found && quick_oracle.found
          && std::abs(fast.distance - quick_oracle.distance)
            > mismatch_tolerance(quick_oracle.distance));
      if (quick_disagreement) {
        ++oracle_adjudications;
        oracle = surface.distance_reference(
          origin, direction, false, adjudication_options);
      }
      fast_found += fast.found ? 1ULL : 0ULL;
      oracle_found += oracle.found ? 1ULL : 0ULL;
      exact_path_count += fast.root_diagnostics.solver_path
          == stellarcsg::SolverPath::exact_circular_torus
        ? 1ULL : 0ULL;
      if (oracle.found && !fast.found) {
        ++missed_roots;
        failure_fixtures.push_back({index, "missed_root", origin, direction,
          fast.found, fast.distance, oracle.found, oracle.distance});
      } else if (!oracle.found && fast.found) {
        ++false_roots;
        failure_fixtures.push_back({index, "false_root", origin, direction,
          fast.found, fast.distance, oracle.found, oracle.distance});
      } else if (oracle.found && fast.found) {
        const double error = std::abs(fast.distance - oracle.distance);
        maximum_distance_error = std::max(maximum_distance_error, error);
        maximum_fast_residual = std::max(
          maximum_fast_residual, fast.residual);
        if (error > mismatch_tolerance(oracle.distance)) {
          ++wrong_nearest;
          failure_fixtures.push_back({index, "wrong_nearest_root", origin,
            direction, fast.found, fast.distance, oracle.found,
            oracle.distance});
        }
      }
    }

    // Exact adversarial cases exercise measure-zero tangencies, coincident
    // starts, four crossings, seams, and non-unit directions separately from
    // the randomized oracle population.
    std::uint64_t adversarial_failures = 0;
    constexpr std::uint64_t adversarial_count = 4096;
    for (std::uint64_t index = 0; index < adversarial_count; ++index) {
      const double phi = two_pi * static_cast<double>(index)
                         / static_cast<double>(adversarial_count);
      const stellarcsg::Vec3 point {
        6.0 * std::cos(phi), 6.0 * std::sin(phi), 0.0};
      const stellarcsg::Vec3 tangent {
        -3.0 * std::sin(phi), 3.0 * std::cos(phi), 0.0};
      const auto tangent_result = surface.distance(
        point - (1.23456789 / 3.0) * tangent, tangent, false);
      if (!tangent_result.found
          || std::abs(tangent_result.distance - 1.23456789) > 2.0e-8) {
        ++adversarial_failures;
      }
    }
    const auto four_root = surface.distance(
      {-7.0, 0.0, 0.0}, {9.0, 0.0, 0.0}, false);
    const auto coincident_out = surface.distance(
      {6.0, 0.0, 0.0}, {4.0, 0.0, 0.0}, true);
    const auto coincident_in = surface.distance(
      {6.0, 0.0, 0.0}, {-4.0, 0.0, 0.0}, true);
    if (!four_root.found || std::abs(four_root.distance - 1.0) > 2.0e-9)
      ++adversarial_failures;
    if (coincident_out.found) ++adversarial_failures;
    if (!coincident_in.found
        || std::abs(coincident_in.distance - 2.0) > 2.0e-9)
      ++adversarial_failures;

    const auto stop = std::chrono::steady_clock::now();
    const double elapsed_seconds =
      std::chrono::duration<double>(stop - start).count();
    std::cout << std::setprecision(17)
              << "{\n"
              << "  \"schema_version\": 1,\n"
              << "  \"case\": \""
              << (force_general ? "exact_torus_forced_general_patch"
                                : "exact_circular_torus") << "\",\n"
              << "  \"seed\": " << seed << ",\n"
              << "  \"randomized_rays\": " << ray_count << ",\n"
              << "  \"adversarial_rays\": " << adversarial_count + 3 << ",\n"
              << "  \"oracle_found\": " << oracle_found << ",\n"
              << "  \"fast_found\": " << fast_found << ",\n"
              << "  \"exact_path_count\": " << exact_path_count << ",\n"
              << "  \"high_resolution_oracle_adjudications\": "
              << oracle_adjudications << ",\n"
              << "  \"missed_roots\": " << missed_roots << ",\n"
              << "  \"false_roots\": " << false_roots << ",\n"
              << "  \"wrong_nearest_roots\": " << wrong_nearest << ",\n"
              << "  \"adversarial_failures\": " << adversarial_failures << ",\n"
              << "  \"maximum_distance_error_cm\": "
              << maximum_distance_error << ",\n"
              << "  \"maximum_fast_residual_cm\": "
              << maximum_fast_residual << ",\n"
              << "  \"elapsed_seconds\": " << elapsed_seconds << ",\n"
              << "  \"failure_fixtures\": [";
    for (std::size_t i = 0; i < failure_fixtures.size(); ++i) {
      const auto& failure = failure_fixtures[i];
      if (i != 0) std::cout << ',';
      std::cout << "\n    {\"index\":" << failure.index
                << ",\"kind\":\"" << failure.kind << "\""
                << ",\"origin\":[" << failure.origin.x << ','
                << failure.origin.y << ',' << failure.origin.z << ']'
                << ",\"direction\":[" << failure.direction.x << ','
                << failure.direction.y << ',' << failure.direction.z << ']'
                << ",\"fast_found\":"
                << (failure.fast_found ? "true" : "false")
                << ",\"fast_distance_cm\":";
      if (failure.fast_found) std::cout << failure.fast_distance;
      else std::cout << "null";
      std::cout << ",\"oracle_found\":"
                << (failure.oracle_found ? "true" : "false")
                << ",\"oracle_distance_cm\":";
      if (failure.oracle_found) std::cout << failure.oracle_distance;
      else std::cout << "null";
      std::cout << '}';
    }
    if (!failure_fixtures.empty()) std::cout << '\n' << "  ";
    std::cout << "]\n"
              << "}\n";
    return missed_roots == 0 && false_roots == 0 && wrong_nearest == 0
        && adversarial_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return EXIT_FAILURE;
  }
}
