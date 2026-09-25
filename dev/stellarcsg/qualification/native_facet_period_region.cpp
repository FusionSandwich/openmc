// Initialize the accepted-mesh 90-degree region through native OpenMC.
// No particle histories or material transport are run.
#include "openmc/boundary_condition.h"
#include "openmc/cell.h"
#include "openmc/geometry_aux.h"
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/surface_facet_set.h"

#include <cmath>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
  try {
    if (argc != 2)
      throw std::invalid_argument("usage: native_facet_period_region INPUT_DIR");
    openmc::settings::path_input = std::string(argv[1]) + "/";
    openmc::read_geometry_xml();
    if (openmc::model::surfaces.size() != 6 || openmc::model::cells.size() != 2)
      throw std::runtime_error("Unexpected facet period surface or cell count");
    if (openmc::model::surface_map.size() != 6
        || openmc::model::cell_map.size() != 2)
      throw std::runtime_error("Unexpected facet period ID map count");
    for (const int id : {901, 902, 903, 904, 905, 906})
      if (!openmc::model::surface_map.count(id))
        throw std::runtime_error("Missing facet period surface ID");
    for (const int id : {1001, 1002})
      if (!openmc::model::cell_map.count(id))
        throw std::runtime_error("Missing facet period cell ID");
    auto* facet = dynamic_cast<openmc::SurfaceFacetSet*>(
      openmc::model::surfaces[openmc::model::surface_map.at(903)].get());
    if (!facet)
      throw std::runtime_error("Facet period surface dispatch failed");
    const auto* xbc = dynamic_cast<openmc::RotationalPeriodicBC*>(
      openmc::model::surfaces[openmc::model::surface_map.at(901)]->bc_.get());
    const auto* ybc = dynamic_cast<openmc::RotationalPeriodicBC*>(
      openmc::model::surfaces[openmc::model::surface_map.at(902)]->bc_.get());
    if (!xbc || !ybc)
      throw std::runtime_error("Facet period planes are not rotationally paired");
    const auto box = facet->bounding_box(false);
    if (!std::isfinite(box.min.x) || !std::isfinite(box.min.y)
        || !std::isfinite(box.min.z) || !std::isfinite(box.max.x)
        || !std::isfinite(box.max.y) || !std::isfinite(box.max.z))
      throw std::runtime_error("Facet period box is not finite");
    std::cout << "{\"state\":\"NATIVE_FACET_PERIOD_REGION_INITIALIZED\","
              << "\"surfaces\":6,\"cells\":2,"
              << "\"rotational_periodic_pair\":[901,902],"
              << "\"facet_surface_id\":903,\"transport_run\":false}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native facet period region: " << error.what() << '\n';
    return 1;
  }
}
