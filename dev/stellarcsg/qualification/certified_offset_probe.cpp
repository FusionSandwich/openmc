// Exact-control offset qualification. No particle transport is launched.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"
#ifdef STELLARCSG_OFFSET_NATIVE
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/surface_swept_spline.h"
#endif

#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <set>
#include <stdexcept>
#include <unordered_map>

int main(int argc, char** argv)
{
  try {
    std::cout << "{\"kind\":\"arithmetic\",\"double_bits\":"
              << std::numeric_limits<double>::digits << ",\"long_double_bits\":"
              << std::numeric_limits<long double>::digits
              << ",\"long_double_max_exponent\":"
              << std::numeric_limits<long double>::max_exponent << "}\n";
    if (argc != 2)
      throw std::invalid_argument("Usage: certified_offset_probe ANALYTIC_H5");
    const auto data =
      stellarcsg::read_swept_spline_surface_hdf5(argv[1], "/coils/coil_002");
    const stellarcsg::CompiledSweptSplineSurface surface(data, true,
      stellarcsg::SweptTorusMode::faithful_spline,
      stellarcsg::SweptRepresentation::exact_control_offset);
    const auto start = std::chrono::steady_clock::now();
    const auto hit = surface.distance({550, 0, 0}, {-1, 0, 0}, false);
    const auto elapsed = std::chrono::duration<double, std::nano>(
      std::chrono::steady_clock::now() - start)
                           .count();
    std::cout << std::setprecision(17)
              << "{\"kind\":\"member2_seam\",\"representation\":\"exact_"
                 "control_offset\","
              << "\"found\":" << (hit.found ? "true" : "false")
              << ",\"unresolved\":"
              << (hit.terminal_unresolved ? "true" : "false")
              << ",\"distance_cm\":";
    if (std::isfinite(hit.distance))
      std::cout << hit.distance;
    else
      std::cout << "null";
    std::cout << ",\"elapsed_ns\":" << elapsed << ",\"excluded_slabs\":"
              << hit.root_diagnostics.certified_excluded_intervals
              << ",\"minimum_calls\":"
              << hit.root_diagnostics.function_evaluations
              << ",\"minimum_nodes\":"
              << hit.root_diagnostics.subdivided_intervals
              << ",\"projection_visits\":"
              << hit.root_diagnostics.derivative_evaluations << "}\n"
              << std::flush;
    if (hit.disposition() != stellarcsg::DistanceDisposition::hit)
      return 2;
    if (std::abs(hit.distance - 16.0) > 2e-8)
      throw std::runtime_error(
        "member2 seam distance disagrees with independent reference interval");
    const auto normal = surface.normal({550 - hit.distance, 0, 0});
    const auto before = surface.evaluate({550 - hit.distance + 1e-7, 0, 0});
    const auto after = surface.evaluate({550 - hit.distance - 1e-7, 0, 0});
    if (!(before > 0 && after < 0 && normal.x > 0.999999))
      throw std::runtime_error("point/normal transition disagrees");
    stellarcsg::RootSearchOptions exhausted;
    exhausted.initial_subdivisions = 0;
    if (surface.distance({550, 0, 0}, {-1, 0, 0}, false, exhausted)
          .disposition() != stellarcsg::DistanceDisposition::unresolved)
      throw std::runtime_error("exhaustion converted to a result");
    bool rejected = false;
    auto invalid = data;
    invalid.major_radius_coefficients[0] += 1;
    try {
      const stellarcsg::CompiledSweptSplineSurface bad(invalid, true,
        stellarcsg::SweptTorusMode::faithful_spline,
        stellarcsg::SweptRepresentation::exact_control_offset);
    } catch (const std::invalid_argument&) {
      rejected = true;
    }
    if (!rejected)
      throw std::runtime_error("variable radius admitted");
    rejected = false;
    try {
      (void)surface.distance({550, 0, 0}, {0, 0, 0}, false);
    } catch (const std::invalid_argument&) {
      rejected = true;
    }
    if (!rejected)
      throw std::runtime_error("zero direction admitted");
    const auto scaled = surface.distance({550, 0, 0}, {-1e-300, 0, 0}, false);
    if (scaled.disposition() != stellarcsg::DistanceDisposition::hit ||
        std::abs(scaled.distance - hit.distance) > 1e-10)
      throw std::runtime_error("near-zero direction normalization disagrees");
    std::cout << "{\"kind\":\"controls\",\"state\":\"PASS\",\"normal_x\":"
              << normal.x << ",\"before\":" << before << ",\"after\":" << after
              << "}\n";
#ifdef STELLARCSG_OFFSET_NATIVE
    openmc::settings::path_input = "";
    pugi::xml_document document;
    auto geometry = document.append_child("geometry");
    auto node = geometry.append_child("surface");
    node.append_attribute("id") = 1902;
    node.append_attribute("type") = "swept-spline";
    node.append_attribute("data_file") = argv[1];
    node.append_attribute("dataset") = "/coils/coil_002";
    node.append_attribute("representation") = "exact_control_offset";
    std::set<std::pair<int, int>> pairs;
    std::unordered_map<int, double> albedo;
    std::unordered_map<int, int> senses;
    openmc::read_surfaces(geometry, pairs, albedo, senses);
    auto* native = dynamic_cast<openmc::SurfaceSweptSpline*>(
      openmc::model::surfaces.front().get());
    if (!native || native->id_ != 1902)
      throw std::runtime_error("native registration failed");
    const auto distance = native->distance({550, 0, 0}, {-1, 0, 0}, false);
    const auto native_normal = native->normal({550 - distance, 0, 0});
    if (std::abs(distance - hit.distance) > 1e-10 || native_normal.x < 0.999999)
      throw std::runtime_error("native adapter disagrees");
    if (native->sense({550 - distance, 0, 0}, {-1, 0, 0}) ||
        !native->sense({550 - distance, 0, 0}, {1, 0, 0}))
      throw std::runtime_error("native coincident direction sense disagrees");
    std::cout
      << "{\"kind\":\"native_surface\",\"surface_id\":1902,\"distance_cm\":"
      << distance << ",\"state\":\"PASS\",\"particle_transport\":false}\n";
    openmc::free_memory_surfaces();
#endif
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
