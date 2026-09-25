// Opt-in native OpenMC surface-registration smoke on an analytic HDF5 fixture.
// This is not particle transport or a WISTELL-D physics qualification.
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/surface_swept_spline.h"
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <cmath>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace {

double run_surface(const std::string& xml, int id)
{
  pugi::xml_document document;
  if (!document.load_string(xml.c_str())) {
    throw std::runtime_error("Invalid surface XML");
  }
  std::set<std::pair<int, int>> periodic_pairs;
  std::unordered_map<int, double> albedo_map;
  std::unordered_map<int, int> periodic_sense_map;
  openmc::read_surfaces(document.child("geometry"), periodic_pairs, albedo_map,
    periodic_sense_map);
  if (openmc::model::surfaces.size() != 1) {
    throw std::runtime_error("Expected exactly one registered surface");
  }
  auto* surface = dynamic_cast<openmc::SurfaceSweptSpline*>(
    openmc::model::surfaces.front().get());
  if (!surface || surface->id_ != id) {
    throw std::runtime_error("Native swept-spline dispatch failed");
  }
  try {
    const double distance = surface->distance(
      {550.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false);
    openmc::free_memory_surfaces();
    return distance;
  } catch (...) {
    openmc::free_memory_surfaces();
    throw;
  }
}

} // namespace

int main(int argc, char** argv)
{
  try {
    if (argc != 2) {
      throw std::invalid_argument("Usage: native_adapter_smoke ANALYTIC_H5");
    }
    openmc::settings::path_input = "";
    const std::string file = argv[1];
    const std::string one =
      "<geometry><surface id='902' type='swept-spline' data_file='" + file
      + "' dataset='/coils/coil_001' units='cm'/></geometry>";
    const std::string collection =
      "<geometry><surface id='903' type='swept-spline' data_file='" + file
      + "' dataset_prefix='/coils/coil_' dataset_start='1' "
        "dataset_count='3' units='cm'/></geometry>";
    double single_distance;
    double collection_distance;
    try { single_distance = run_surface(one, 902); }
    catch (const std::exception& error) {
      throw std::runtime_error(std::string("single: ") + error.what());
    }
    std::cout << "{\"kind\":\"native_stellarcsg_adapter_single\","
                 "\"distance_cm\":" << single_distance << ","
              << "\"native_transport\":false}\n" << std::flush;
    for (int member = 2; member <= 3; ++member) {
      const std::string dataset = "/coils/coil_00" + std::to_string(member);
      const auto data = stellarcsg::read_swept_spline_surface_hdf5(file, dataset);
      const stellarcsg::CompiledSweptSplineSurface surface {data};
      const auto result = surface.distance(
        {550.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false);
      const auto reference = surface.distance_reference(
        {550.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false);
      std::cout << "{\"kind\":\"native_stellarcsg_solver_probe\","
                   "\"member\":" << member << ",\"found\":"
                << (result.found ? "true" : "false")
                << ",\"terminal_unresolved\":"
                << (result.terminal_unresolved ? "true" : "false")
                << ",\"unresolved_intervals\":"
                << result.root_diagnostics.unresolved_intervals
                << ",\"lead_distance_cm\":";
      if (result.found && std::isfinite(result.distance))
        std::cout << result.distance;
      else std::cout << "null";
      std::cout << ",\"reference_found\":"
                << (reference.found ? "true" : "false")
                << ",\"reference_distance_cm\":";
      if (reference.found && std::isfinite(reference.distance))
        std::cout << reference.distance;
      else std::cout << "null";
      std::cout << "}\n" << std::flush;
    }
    for (int member = 2; member <= 3; ++member) {
      const std::string dataset = "/coils/coil_00" + std::to_string(member);
      const std::string xml =
        "<geometry><surface id='904' type='swept-spline' data_file='"
        + file + "' dataset='" + dataset + "' units='cm'/></geometry>";
      try {
        const double distance = run_surface(xml, 904);
        std::cout << "{\"kind\":\"native_stellarcsg_member_probe\","
                     "\"member\":" << member << ",\"distance_cm\":";
        if (std::isfinite(distance)) std::cout << distance;
        else std::cout << "null";
        std::cout << ",\"state\":\""
                  << (std::isfinite(distance) ? "HIT" : "NO_HIT")
                  << "\"}\n" << std::flush;
      } catch (const std::exception& error) {
        std::cout << "{\"kind\":\"native_stellarcsg_member_probe\","
                     "\"member\":" << member
                  << ",\"state\":\"ERROR\"}\n" << std::flush;
        std::cerr << "native member " << member << ": " << error.what()
                  << '\n';
      }
    }
    try { collection_distance = run_surface(collection, 903); }
    catch (const std::exception& error) {
      throw std::runtime_error(std::string("collection: ") + error.what());
    }
    std::cout << "{\"kind\":\"native_stellarcsg_adapter_smoke\","
                 "\"single_distance_cm\":" << single_distance << ','
              << "\"collection_distance_cm\":" << collection_distance << ','
              << "\"native_transport\":false}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native adapter smoke: " << error.what() << '\n';
    return 1;
  }
}
