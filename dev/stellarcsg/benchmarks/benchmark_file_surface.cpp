#include "stellarcsg/coefficient_file.hpp"
#include "stellarcsg/compiled_periodic_surface.hpp"
#include "stellarcsg/performance_counters.hpp"
#include "stellarcsg/uniform_periodic_cubic_spline.hpp"

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
#ifndef STELLARCSG_HAS_HDF5
  (void) argc;
  (void) argv;
  std::cerr << "HDF5 support is required\n";
  return EXIT_FAILURE;
#else
  if (argc != 3) {
    std::cerr << "usage: " << argv[0] << " FILE DATASET\n";
    return EXIT_FAILURE;
  }
  try {
    auto data = stellarcsg::read_periodic_spline_surface_hdf5(
      argv[1], argv[2]);
    const stellarcsg::UniformPeriodicCubicSpline axis_r {
      data.axis_r_coefficients.size(), data.n_field_periods,
      data.axis_r_coefficients};
    const stellarcsg::UniformPeriodicCubicSpline axis_z {
      data.axis_z_coefficients.size(), data.n_field_periods,
      data.axis_z_coefficients};
    const stellarcsg::Vec3 origin {axis_r.value(0.0), 0.0, axis_z.value(0.0)};
    const stellarcsg::CompiledPeriodicSplineSurface surface {std::move(data)};
    constexpr std::size_t count = 1000;
    constexpr double golden_angle = 2.3999632297286533222;
    std::size_t found = 0;
    std::size_t fallback = 0;
    long evaluations = 0;
    long subdivisions = 0;
    long exclusions = 0;
    volatile double sink = 0.0;
    stellarcsg::reset_performance_counters();
    const auto start = std::chrono::steady_clock::now();
    for (std::size_t i = 0; i < count; ++i) {
      const double z = 1.0 - 2.0 * (static_cast<double>(i) + 0.5)
                               / static_cast<double>(count);
      const double radial = std::sqrt(std::max(0.0, 1.0 - z * z));
      const double phi = golden_angle * static_cast<double>(i);
      const stellarcsg::Vec3 direction {
        radial * std::cos(phi), radial * std::sin(phi), z};
      const auto result = surface.distance(origin, direction, false);
      sink += result.found ? result.distance : 0.0;
      found += result.found ? 1U : 0U;
      fallback += result.root_diagnostics.reference_fallback_calls != 0 ? 1U : 0U;
      evaluations += result.root_diagnostics.function_evaluations;
      subdivisions += result.root_diagnostics.subdivided_intervals;
      exclusions += result.root_diagnostics.certified_excluded_intervals;
    }
    const auto stop = std::chrono::steady_clock::now();
    const auto counters = stellarcsg::performance_counters_snapshot();
    const double ns = std::chrono::duration<double, std::nano>(stop - start).count()
                      / static_cast<double>(count);
    std::cout << std::setprecision(12)
              << "{\n"
              << "  \"distance_ns_per_call\": " << ns << ",\n"
              << "  \"patch_count\": " << surface.patches().size() << ",\n"
              << "  \"bvh_node_count\": " << surface.patch_bvh().size() << ",\n"
              << "  \"found_fraction\": " << static_cast<double>(found) / count
              << ",\n"
              << "  \"fallback_fraction\": "
              << static_cast<double>(fallback) / count << ",\n"
              << "  \"candidate_bvh_nodes_per_call\": "
              << static_cast<double>(counters.candidate_bvh_nodes) / count
              << ",\n"
              << "  \"candidate_patches_per_call\": "
              << static_cast<double>(counters.candidate_patches_or_segments)
                   / count << ",\n"
              << "  \"newton_iterations_per_call\": "
              << static_cast<double>(counters.newton_iterations) / count
              << ",\n"
              << "  \"newton_failures_per_call\": "
              << static_cast<double>(counters.newton_failures) / count
              << ",\n"
              << "  \"proxy_seeds_per_call\": "
              << static_cast<double>(counters.proxy_seeds) / count << ",\n"
              << "  \"proxy_intersections_per_call\": "
              << static_cast<double>(counters.proxy_intersections) / count
              << ",\n"
              << "  \"tangent_cases_per_call\": "
              << static_cast<double>(counters.tangent_or_grazing_cases) / count
              << ",\n"
              << "  \"local_subdivision_nodes_per_call\": "
              << static_cast<double>(counters.local_subdivision_nodes) / count
              << ",\n"
              << "  \"local_subdivision_calls_per_call\": "
              << static_cast<double>(counters.local_subdivision_calls) / count
              << ",\n"
              << "  \"global_reference_calls\": "
              << counters.global_reference_calls << ",\n"
              << "  \"function_evaluations_per_call\": "
              << static_cast<double>(evaluations) / count << ",\n"
              << "  \"subdivisions_per_call\": "
              << static_cast<double>(subdivisions) / count << ",\n"
              << "  \"exclusions_per_call\": "
              << static_cast<double>(exclusions) / count << ",\n"
              << "  \"sink\": " << sink << "\n"
              << "}\n";
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
#endif
}
