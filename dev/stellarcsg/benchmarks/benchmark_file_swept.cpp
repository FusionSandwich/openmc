#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/performance_counters.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <algorithm>
#include <array>
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
  return EXIT_FAILURE;
#else
  if (argc != 3 && argc != 4) {
    std::cerr << "usage: " << argv[0] << " FILE DATASET [ORACLE_RAYS]\n";
    return EXIT_FAILURE;
  }
  try {
    auto data = stellarcsg::read_swept_spline_surface_hdf5(argv[1], argv[2]);
    const std::size_t last = data.sample_count - 1;
    const stellarcsg::Vec3 center {
      (data.centerline_coefficients[3 * last]
        + 4.0 * data.centerline_coefficients[0]
        + data.centerline_coefficients[3]) / 6.0,
      (data.centerline_coefficients[3 * last + 1]
        + 4.0 * data.centerline_coefficients[1]
        + data.centerline_coefficients[4]) / 6.0,
      (data.centerline_coefficients[3 * last + 2]
        + 4.0 * data.centerline_coefficients[2]
        + data.centerline_coefficients[5]) / 6.0};
    const stellarcsg::Vec3 center_derivative {
      0.5 * (data.centerline_coefficients[3]
             - data.centerline_coefficients[3 * last]),
      0.5 * (data.centerline_coefficients[4]
             - data.centerline_coefficients[3 * last + 1]),
      0.5 * (data.centerline_coefficients[5]
             - data.centerline_coefficients[3 * last + 2])};
    const stellarcsg::Vec3 tangent = stellarcsg::normalized(center_derivative);
    stellarcsg::Vec3 source_normal {
      (data.normal_coefficients[3 * last]
        + 4.0 * data.normal_coefficients[0]
        + data.normal_coefficients[3]) / 6.0,
      (data.normal_coefficients[3 * last + 1]
        + 4.0 * data.normal_coefficients[1]
        + data.normal_coefficients[4]) / 6.0,
      (data.normal_coefficients[3 * last + 2]
        + 4.0 * data.normal_coefficients[2]
        + data.normal_coefficients[5]) / 6.0};
    source_normal = stellarcsg::normalized(
      source_normal - stellarcsg::dot(source_normal, tangent) * tangent);
    const stellarcsg::Vec3 origin = center + 2.5 * source_normal;
    const stellarcsg::CompiledSweptSplineSurface surface {std::move(data)};
    constexpr std::size_t count = 1000;
    const std::size_t oracle_count = argc == 4
      ? static_cast<std::size_t>(std::stoull(argv[3])) : 1000;
    if (oracle_count == 0) {
      throw std::invalid_argument("ORACLE_RAYS must be positive");
    }
    constexpr double golden_angle = 2.3999632297286533222;
    std::size_t found = 0;
    std::size_t mismatches = 0;
    volatile double sink = 0.0;
    std::array<stellarcsg::Vec3, count> classification_points {};
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
      classification_points[i] = result.found
        ? origin + result.distance * direction : origin;
      sink += result.found ? result.distance : 0.0;
      found += result.found ? 1U : 0U;
    }
    const auto stop = std::chrono::steady_clock::now();
    const auto counters = stellarcsg::performance_counters_snapshot();
    const auto evaluate_start = std::chrono::steady_clock::now();
    for (const auto& point : classification_points) sink += surface.evaluate(point);
    const auto evaluate_stop = std::chrono::steady_clock::now();
    for (std::size_t i = 0; i < oracle_count; ++i) {
      const double z = 1.0 - 2.0 * (static_cast<double>(i) + 0.5)
                               / static_cast<double>(oracle_count);
      const double radial = std::sqrt(std::max(0.0, 1.0 - z * z));
      const double phi = golden_angle * static_cast<double>(i);
      const stellarcsg::Vec3 direction {
        radial * std::cos(phi), radial * std::sin(phi), z};
      const auto fast = surface.distance(origin, direction, false);
      const auto oracle = surface.distance_reference(origin, direction, false);
      if (fast.found != oracle.found
          || (fast.found && std::abs(fast.distance - oracle.distance) > 1.0e-6)) {
        ++mismatches;
        std::cerr << std::setprecision(17)
                  << "mismatch " << i << " fast=" << fast.found << ':'
                  << fast.distance << " oracle=" << oracle.found << ':'
                  << oracle.distance << " fast_residual=" << fast.residual
                  << " oracle_residual=" << oracle.residual
                  << " fast_f=" << surface.evaluate(
                       origin + fast.distance * direction)
                  << " oracle_f=" << surface.evaluate(
                       origin + oracle.distance * direction)
                  << " direction=" << direction.x << ','
                  << direction.y << ',' << direction.z << '\n';
      }
    }
    const double ns = std::chrono::duration<double, std::nano>(stop - start).count()
                      / static_cast<double>(count);
    const double evaluate_ns = std::chrono::duration<double, std::nano>(
      evaluate_stop - evaluate_start).count() / static_cast<double>(count);
    std::cout << std::setprecision(12)
              << "{\n"
              << "  \"distance_ns_per_call\": " << ns << ",\n"
              << "  \"classification_ns_per_call\": " << evaluate_ns << ",\n"
              << "  \"span_count\": " << surface.spans().size() << ",\n"
              << "  \"bvh_node_count\": " << surface.span_bvh().size() << ",\n"
              << "  \"found_fraction\": " << static_cast<double>(found) / count
              << ",\n"
              << "  \"candidate_nodes_per_call\": "
              << static_cast<double>(counters.candidate_bvh_nodes) / count
              << ",\n"
              << "  \"candidate_spans_per_call\": "
              << static_cast<double>(counters.candidate_patches_or_segments) / count
              << ",\n"
              << "  \"newton_iterations_per_call\": "
              << static_cast<double>(counters.newton_iterations) / count
              << ",\n"
              << "  \"newton_failures_per_call\": "
              << static_cast<double>(counters.newton_failures) / count
              << ",\n"
              << "  \"local_subdivision_calls_per_call\": "
              << static_cast<double>(counters.local_subdivision_calls) / count
              << ",\n"
              << "  \"production_global_reference_calls\": 0,\n"
              << "  \"oracle_rays\": " << oracle_count << ",\n"
              << "  \"oracle_mismatches\": " << mismatches << ",\n"
              << "  \"sink\": " << sink << "\n"
              << "}\n";
    return mismatches == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return EXIT_FAILURE;
  }
#endif
}
