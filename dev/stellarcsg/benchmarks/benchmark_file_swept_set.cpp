#include "stellarcsg/compiled_swept_surface_set.hpp"
#include "stellarcsg/performance_counters.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string dataset_name(
  const std::string& prefix, std::size_t index)
{
  std::ostringstream name;
  name << prefix << std::setfill('0') << std::setw(3) << index;
  return name.str();
}

stellarcsg::Vec3 benchmark_origin(
  const stellarcsg::SweptSplineSurfaceData& data)
{
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
  const auto tangent = stellarcsg::normalized(center_derivative);
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
  return center + 2.5 * source_normal;
}

stellarcsg::Vec3 fibonacci_direction(
  std::size_t index, std::size_t count)
{
  constexpr double golden_angle = 2.3999632297286533222;
  const double z = 1.0 - 2.0 * (static_cast<double>(index) + 0.5)
                           / static_cast<double>(count);
  const double radial = std::sqrt(std::max(0.0, 1.0 - z * z));
  const double phi = golden_angle * static_cast<double>(index);
  return {radial * std::cos(phi), radial * std::sin(phi), z};
}

} // namespace

int main(int argc, char** argv)
{
#ifndef STELLARCSG_HAS_HDF5
  (void) argc;
  (void) argv;
  return EXIT_FAILURE;
#else
  if (argc != 6) {
    std::cerr << "usage: " << argv[0]
              << " FILE DATASET_PREFIX START COUNT RAYS\n";
    return EXIT_FAILURE;
  }
  try {
    const std::string filename = argv[1];
    const std::string prefix = argv[2];
    const std::size_t first = std::stoull(argv[3]);
    const std::size_t coil_count = std::stoull(argv[4]);
    const std::size_t ray_count = std::stoull(argv[5]);
    if (coil_count == 0 || ray_count == 0) {
      throw std::invalid_argument("COUNT and RAYS must be positive");
    }

    auto first_data = stellarcsg::read_swept_spline_surface_hdf5(
      filename, dataset_name(prefix, first));
    const auto origin = benchmark_origin(first_data);
    std::vector<stellarcsg::SweptSplineSurfaceData> set_data;
    std::vector<std::unique_ptr<stellarcsg::CompiledSweptSplineSurface>>
      brute_surfaces;
    set_data.reserve(coil_count);
    brute_surfaces.reserve(coil_count);
    for (std::size_t i = 0; i < coil_count; ++i) {
      const auto dataset = dataset_name(prefix, first + i);
      set_data.push_back(
        stellarcsg::read_swept_spline_surface_hdf5(filename, dataset));
      brute_surfaces.push_back(
        std::make_unique<stellarcsg::CompiledSweptSplineSurface>(
          stellarcsg::read_swept_spline_surface_hdf5(filename, dataset)));
    }
    stellarcsg::CompiledSweptSplineSurfaceSet surface_set {
      std::move(set_data)};

    std::size_t found = 0;
    volatile double sink = 0.0;
    stellarcsg::reset_performance_counters();
    const auto start = std::chrono::steady_clock::now();
    for (std::size_t i = 0; i < ray_count; ++i) {
      const auto direction = fibonacci_direction(i, ray_count);
      const auto result = surface_set.distance(origin, direction, false);
      sink += result.root.found ? result.root.distance : 0.0;
      found += result.root.found ? 1U : 0U;
    }
    const auto stop = std::chrono::steady_clock::now();
    const auto counters = stellarcsg::performance_counters_snapshot();

    constexpr std::size_t correctness_rays = 1000;
    std::size_t mismatches = 0;
    for (std::size_t i = 0; i < correctness_rays; ++i) {
      const auto direction = fibonacci_direction(i, correctness_rays);
      const auto fast = surface_set.distance(origin, direction, false);
      double brute_distance = std::numeric_limits<double>::infinity();
      bool brute_found = false;
      for (const auto& coil : brute_surfaces) {
        const auto candidate = coil->distance(origin, direction, false);
        if (candidate.found && candidate.distance < brute_distance) {
          brute_distance = candidate.distance;
          brute_found = true;
        }
      }
      if (fast.root.found != brute_found
          || (brute_found
              && std::abs(fast.root.distance - brute_distance) > 1.0e-8)) {
        ++mismatches;
      }
    }

    const double elapsed_ns = std::chrono::duration<double, std::nano>(
      stop - start).count();
    std::cout << std::setprecision(12)
              << "{\n"
              << "  \"coil_count\": " << coil_count << ",\n"
              << "  \"ray_count\": " << ray_count << ",\n"
              << "  \"distance_ns_per_call\": "
              << elapsed_ns / static_cast<double>(ray_count) << ",\n"
              << "  \"distance_calls_per_second\": "
              << 1.0e9 * static_cast<double>(ray_count) / elapsed_ns << ",\n"
              << "  \"found_fraction\": "
              << static_cast<double>(found) / static_cast<double>(ray_count)
              << ",\n"
              << "  \"top_level_bvh_node_count\": "
              << surface_set.coil_bvh().size() << ",\n"
              << "  \"candidate_coils_per_call\": "
              << static_cast<double>(counters.distance_calls) / ray_count
              << ",\n"
              << "  \"combined_bvh_nodes_per_call\": "
              << static_cast<double>(counters.candidate_bvh_nodes) / ray_count
              << ",\n"
              << "  \"candidate_spans_per_call\": "
              << static_cast<double>(counters.candidate_patches_or_segments)
                   / ray_count
              << ",\n"
              << "  \"newton_iterations_per_call\": "
              << static_cast<double>(counters.newton_iterations) / ray_count
              << ",\n"
              << "  \"local_subdivision_calls_per_call\": "
              << static_cast<double>(counters.local_subdivision_calls) / ray_count
              << ",\n"
              << "  \"production_global_reference_calls\": "
              << counters.global_reference_calls << ",\n"
              << "  \"brute_fast_comparison_rays\": "
              << correctness_rays << ",\n"
              << "  \"brute_fast_mismatches\": " << mismatches << ",\n"
              << "  \"sink\": " << sink << "\n"
              << "}\n";
    return mismatches == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return EXIT_FAILURE;
  }
#endif
}
