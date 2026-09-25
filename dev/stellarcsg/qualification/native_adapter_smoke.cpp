// Opt-in native OpenMC surface-registration smoke on an analytic HDF5 fixture.
// This is not particle transport or a WISTELL-D physics qualification.
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/surface_swept_spline.h"

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
  const double distance = surface->distance(
    {550.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false);
  if (!std::isfinite(distance) || distance <= 0.0 || distance > 25.0) {
    throw std::runtime_error("Native swept-spline distance outside smoke bound");
  }
  openmc::free_memory_surfaces();
  return distance;
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
