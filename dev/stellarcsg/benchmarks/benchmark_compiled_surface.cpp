#include "stellarcsg/compiled_periodic_surface.hpp"

#include <chrono>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <iostream>
#include <vector>

namespace {

stellarcsg::PeriodicSplineSurfaceData make_surface()
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.content_id = "benchmark-helical-v1";
  data.n_field_periods = 5;
  data.axis_r_coefficients.assign(16, 500.0);
  data.axis_z_coefficients.assign(16, 0.0);
  data.n_theta = 48;
  data.n_phi = 48;
  data.radius_coefficients.resize(data.n_theta * data.n_phi);
  constexpr double two_pi = 2.0 * 3.141592653589793238462643383279502884;
  for (std::size_t i = 0; i < data.n_theta; ++i) {
    const double theta = two_pi * static_cast<double>(i)
                         / static_cast<double>(data.n_theta);
    for (std::size_t j = 0; j < data.n_phi; ++j) {
      const double psi = two_pi * static_cast<double>(j)
                         / static_cast<double>(data.n_phi);
      data.radius_coefficients[i * data.n_phi + j] =
        100.0 + 8.0 * std::cos(2.0 * theta - psi)
        + 3.0 * std::cos(3.0 * theta + 2.0 * psi);
    }
  }
  data.characteristic_length = 610.0;
  return data;
}

template<class Callable>
double nanoseconds_per_call(std::size_t count, Callable&& callable,
  volatile double& sink)
{
  const auto start = std::chrono::steady_clock::now();
  double sum = 0.0;
  for (std::size_t i = 0; i < count; ++i) sum += callable(i);
  const auto stop = std::chrono::steady_clock::now();
  sink += sum;
  const auto elapsed = std::chrono::duration<double, std::nano>(stop - start);
  return elapsed.count() / static_cast<double>(count);
}

} // namespace

int main()
{
  const stellarcsg::CompiledPeriodicSplineSurface surface {make_surface()};
  constexpr std::size_t count = 500000;
  constexpr double two_pi = 2.0 * 3.141592653589793238462643383279502884;
  volatile double sink = 0.0;

  const double evaluate_ns = nanoseconds_per_call(count,
    [&](std::size_t i) {
      const double phase = two_pi * static_cast<double>(i % 10000) / 10000.0;
      return surface.evaluate(
        {610.0 * std::cos(phase), 610.0 * std::sin(phase), 5.0});
    }, sink);

  const double normal_ns = nanoseconds_per_call(count / 10,
    [&](std::size_t i) {
      const double phase = two_pi * static_cast<double>(i % 10000) / 10000.0;
      const auto n = surface.normal(
        {600.0 * std::cos(phase), 600.0 * std::sin(phase), 0.0});
      return n.x + n.y + n.z;
    }, sink);

  constexpr std::size_t distance_count = 20000;
  std::size_t fallback_count = 0;
  long fast_function_evaluations = 0;
  long fast_subdivided_intervals = 0;
  int first_solver_path = -1;
  int first_fallback_reason = -1;
  long first_unresolved_intervals = -1;
  const auto distance_start = std::chrono::steady_clock::now();
  for (std::size_t i = 0; i < distance_count; ++i) {
    const double phi = two_pi * static_cast<double>(i % 10000) / 10000.0;
    const double theta = two_pi * static_cast<double>((37 * i) % 10000) / 10000.0;
    const double R = 500.0 + 145.0 * std::cos(theta);
    const stellarcsg::Vec3 origin {
      R * std::cos(phi), R * std::sin(phi), 145.0 * std::sin(theta)};
    const stellarcsg::Vec3 direction {
      -std::cos(theta) * std::cos(phi),
      -std::cos(theta) * std::sin(phi), -std::sin(theta)};
    const auto result = surface.distance(origin, direction, false);
    if (i == 0) {
      first_solver_path = static_cast<int>(result.root_diagnostics.solver_path);
      first_fallback_reason = static_cast<int>(
        result.root_diagnostics.fallback_reason);
      first_unresolved_intervals = result.root_diagnostics.unresolved_intervals;
    }
    sink += result.found ? result.distance : 0.0;
    fallback_count += result.root_diagnostics.reference_fallback_calls != 0
      ? 1U : 0U;
    fast_function_evaluations += result.root_diagnostics.function_evaluations;
    fast_subdivided_intervals += result.root_diagnostics.subdivided_intervals;
  }
  const auto distance_stop = std::chrono::steady_clock::now();
  const double distance_ns = std::chrono::duration<double, std::nano>(
    distance_stop - distance_start).count() / static_cast<double>(distance_count);

  constexpr std::size_t reference_count = 100;
  const auto reference_start = std::chrono::steady_clock::now();
  for (std::size_t i = 0; i < reference_count; ++i) {
    const double phi = two_pi * static_cast<double>(i) / reference_count;
    const double theta = two_pi * static_cast<double>((37 * i) % reference_count)
                         / reference_count;
    const double R = 500.0 + 145.0 * std::cos(theta);
    const stellarcsg::Vec3 origin {
      R * std::cos(phi), R * std::sin(phi), 145.0 * std::sin(theta)};
    const stellarcsg::Vec3 direction {
      -std::cos(theta) * std::cos(phi),
      -std::cos(theta) * std::sin(phi), -std::sin(theta)};
    const auto result = surface.distance_reference(origin, direction, false);
    sink += result.found ? result.distance : 0.0;
  }
  const auto reference_stop = std::chrono::steady_clock::now();
  const double reference_ns = std::chrono::duration<double, std::nano>(
    reference_stop - reference_start).count()
    / static_cast<double>(reference_count);

  std::cout << std::setprecision(12)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"evaluate_ns_per_call\": " << evaluate_ns << ",\n"
            << "  \"normal_ns_per_call\": " << normal_ns << ",\n"
            << "  \"distance_fast_ns_per_call\": " << distance_ns << ",\n"
            << "  \"distance_reference_ns_per_call\": " << reference_ns << ",\n"
            << "  \"distance_speedup_vs_reference\": "
            << reference_ns / distance_ns << ",\n"
            << "  \"distance_fallback_fraction\": "
            << static_cast<double>(fallback_count) / distance_count << ",\n"
            << "  \"fast_function_evaluations_per_call\": "
            << static_cast<double>(fast_function_evaluations) / distance_count
            << ",\n"
            << "  \"fast_subdivided_intervals_per_call\": "
            << static_cast<double>(fast_subdivided_intervals) / distance_count
            << ",\n"
            << "  \"first_solver_path\": " << first_solver_path << ",\n"
            << "  \"first_fallback_reason\": " << first_fallback_reason
            << ",\n"
            << "  \"first_unresolved_intervals\": "
            << first_unresolved_intervals << ",\n"
            << "  \"sink\": " << sink << "\n"
            << "}\n";
  return 0;
}
