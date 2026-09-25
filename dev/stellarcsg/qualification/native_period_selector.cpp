// Register the manifest-selected swept members through native OpenMC.
// This checks import and statepoint selector serialization, not transport.
#include "openmc/settings.h"
#include "openmc/hdf5_interface.h"
#include "openmc/surface.h"
#include "openmc/surface_swept_spline.h"

#include <hdf5.h>

#include <cmath>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

int main(int argc, char** argv)
{
  try {
    if (argc != 4)
      throw std::invalid_argument("usage: native_period_selector H5 INDICES OUTPUT_H5");
    const std::string file = argv[1];
    const std::string indices = argv[2];
    const std::string output = argv[3];
    openmc::settings::path_input = "";
    pugi::xml_document document;
    const std::string xml =
      "<geometry><surface id='9801' type='swept-spline' data_file='"
      + file + "' dataset_prefix='/coils/coil_' dataset_indices='"
      + indices + "' units='cm'/></geometry>";
    if (!document.load_string(xml.c_str()))
      throw std::runtime_error("Invalid indexed selector XML");
    std::set<std::pair<int, int>> periodic_pairs;
    std::unordered_map<int, double> albedo_map;
    std::unordered_map<int, int> periodic_sense_map;
    openmc::read_surfaces(document.child("geometry"), periodic_pairs,
      albedo_map, periodic_sense_map);
    if (openmc::model::surfaces.size() != 1)
      throw std::runtime_error("Expected one registered collection surface");
    auto* surface = dynamic_cast<openmc::SurfaceSweptSpline*>(
      openmc::model::surfaces.front().get());
    if (!surface || surface->id_ != 9801)
      throw std::runtime_error("Native indexed swept-spline dispatch failed");
    const auto box = surface->bounding_box(false);
    if (!std::isfinite(box.min.x) || !std::isfinite(box.min.y)
        || !std::isfinite(box.min.z) || !std::isfinite(box.max.x)
        || !std::isfinite(box.max.y) || !std::isfinite(box.max.z))
      throw std::runtime_error("Indexed collection has nonfinite bounds");
    const hid_t file_id = H5Fcreate(output.c_str(), H5F_ACC_EXCL,
      H5P_DEFAULT, H5P_DEFAULT);
    if (file_id < 0) throw std::runtime_error("Unable to create output HDF5");
    const hid_t group = H5Gcreate2(file_id, "surface 9801", H5P_DEFAULT,
      H5P_DEFAULT, H5P_DEFAULT);
    if (group < 0) {
      H5Fclose(file_id);
      throw std::runtime_error("Unable to create output surface group");
    }
    openmc::write_string(group, "boundary_type", "transmission", false);
    surface->to_hdf5_inner(group);
    H5Gclose(group);
    H5Fclose(file_id);
    openmc::free_memory_surfaces();
    std::cout << "{\"native_registered\":true,\"transport_run\":false,"
              << "\"bounds_cm\":[[" << box.min.x << ',' << box.min.y
              << ',' << box.min.z << "],[" << box.max.x << ',' << box.max.y
              << ',' << box.max.z << "]]}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native period selector: " << error.what() << '\n';
    return 1;
  }
}
