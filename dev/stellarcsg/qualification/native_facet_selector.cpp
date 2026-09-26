// Exercise native OpenMC facet import, side queries and serialization.
// This does not launch particle transport.
#include "openmc/hdf5_interface.h"
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/surface_facet_set.h"

#include <hdf5.h>

#include <cmath>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>

int main(int argc, char** argv)
{
  try {
    if (argc != 5)
      throw std::invalid_argument(
        "usage: native_facet_selector PAYLOAD CONTENT_ID FIXTURE OUTPUT_H5");
    openmc::settings::path_input = "";
    pugi::xml_document document;
    auto geometry = document.append_child("geometry");
    auto node = geometry.append_child("surface");
    node.append_attribute("id") = 9901;
    node.append_attribute("type") = "facet-set";
    node.append_attribute("data_file") = argv[1];
    node.append_attribute("dataset") = "/facets/one_period";
    node.append_attribute("content_id") = argv[2];
    node.append_attribute("units") = "cm";
    std::set<std::pair<int, int>> periodic_pairs;
    std::unordered_map<int, double> albedo_map;
    std::unordered_map<int, int> periodic_sense_map;
    openmc::read_surfaces(geometry, periodic_pairs,
      albedo_map, periodic_sense_map);
    if (openmc::model::surfaces.size() != 1)
      throw std::runtime_error("Expected one facet-set surface");
    auto* surface = dynamic_cast<openmc::SurfaceFacetSet*>(
      openmc::model::surfaces.front().get());
    if (!surface || surface->id_ != 9901)
      throw std::runtime_error("Native facet-set dispatch failed");
    const auto box = surface->bounding_box(false);
    if (!std::isfinite(box.min.x) || !std::isfinite(box.min.y)
        || !std::isfinite(box.min.z) || !std::isfinite(box.max.x)
        || !std::isfinite(box.max.y) || !std::isfinite(box.max.z))
      throw std::runtime_error("Facet set has nonfinite bounds");

    std::ifstream fixture {argv[3]};
    std::size_t triangles = 0;
    fixture >> triangles;
    if (!fixture || triangles != 3348)
      throw std::runtime_error("Unexpected P00 fixture triangle count");
    for (std::size_t i = 0; i < triangles; ++i) {
      double coordinate;
      int component;
      fixture >> component;
      for (int j = 0; j < 9; ++j) fixture >> coordinate;
      if (!fixture) throw std::runtime_error("Malformed P00 triangle fixture");
    }
    std::size_t probes = 0;
    fixture >> probes;
    if (!fixture || probes != 108)
      throw std::runtime_error("Unexpected P00 fixture probe count");
    std::size_t inside_count = 0;
    std::size_t outside_count = 0;
    for (std::size_t i = 0; i < probes; ++i) {
      int component, expected_inside;
      openmc::Position point;
      fixture >> component >> expected_inside >> point.x >> point.y >> point.z;
      if (!fixture) throw std::runtime_error("Malformed P00 probe fixture");
      const bool inside = surface->evaluate(point) < 0.0;
      if (inside != (expected_inside == 1))
        throw std::runtime_error("Native facet probe side mismatch");
      inside_count += inside;
      outside_count += !inside;
    }
    if (inside_count != 54 || outside_count != 54)
      throw std::runtime_error("Native facet probe counts differ");

    const hid_t file = H5Fcreate(argv[4], H5F_ACC_EXCL,
      H5P_DEFAULT, H5P_DEFAULT);
    if (file < 0) throw std::runtime_error("Unable to create HDF5 summary");
    const hid_t group = H5Gcreate2(file, "surface 9901", H5P_DEFAULT,
      H5P_DEFAULT, H5P_DEFAULT);
    if (group < 0) {
      H5Fclose(file);
      throw std::runtime_error("Unable to create HDF5 surface group");
    }
    openmc::write_string(group, "boundary_type", "transmission", false);
    surface->to_hdf5_inner(group);
    H5Gclose(group);
    H5Fclose(file);
    openmc::free_memory_surfaces();
    std::cout << "{\"native_registered\":true,\"inside_probes\":"
              << inside_count << ",\"outside_probes\":" << outside_count
              << ",\"transport_run\":false}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native facet selector: " << error.what() << '\n';
    return 1;
  }
}
