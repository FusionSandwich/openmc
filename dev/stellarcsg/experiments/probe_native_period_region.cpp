// Initialize the provisional period geometry through native OpenMC, without
// materials, source, particle histories, or transport.
#include "openmc/boundary_condition.h"
#include "openmc/cell.h"
#include "openmc/geometry_aux.h"
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/surface_swept_spline.h"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
  try {
    if (argc != 2)
      throw std::invalid_argument("usage: probe_native_period_region XML_DIRECTORY");
    openmc::settings::path_input = std::string(argv[1]) + "/";
    openmc::read_geometry_xml();
    if (openmc::model::cells.size() != 2 || openmc::model::surfaces.size() != 6)
      throw std::runtime_error("native cell/surface count differs");
    const auto& x = *openmc::model::surfaces.at(openmc::model::surface_map.at(901));
    const auto& y = *openmc::model::surfaces.at(openmc::model::surface_map.at(902));
    const auto& coil = *openmc::model::surfaces.at(openmc::model::surface_map.at(903));
    const auto* x_bc = dynamic_cast<const openmc::RotationalPeriodicBC*>(x.bc_.get());
    const auto* y_bc = dynamic_cast<const openmc::RotationalPeriodicBC*>(y.bc_.get());
    if (!x_bc || !y_bc
        || openmc::model::surfaces.at(x_bc->j_surf())->id_ != 902
        || openmc::model::surfaces.at(y_bc->j_surf())->id_ != 901
        || dynamic_cast<const openmc::SurfaceSweptSpline*>(&coil) == nullptr)
      throw std::runtime_error("native periodic pair or swept selector differs");
    for (const auto& cell : openmc::model::cells) {
      if (cell->id_ != 1001 && cell->id_ != 1002)
        throw std::runtime_error("unexpected native period cell");
      bool positive_x = false;
      bool positive_y = false;
      bool found_coil = false;
      for (int signed_surface : cell->surfaces()) {
        const int id = openmc::model::surfaces.at(
          static_cast<std::size_t>(std::abs(signed_surface) - 1))->id_;
        if (id == 901 && signed_surface > 0) positive_x = true;
        if (id == 902 && signed_surface > 0) positive_y = true;
        if (id == 903 && (signed_surface < 0) == (cell->id_ == 1001))
          found_coil = true;
      }
      if (!positive_x || !positive_y || !found_coil)
        throw std::runtime_error("native period cell lost a sector or coil sense");
    }
    std::cout << "{\"state\":\"NATIVE_PERIOD_REGION_INITIALIZED\","
              << "\"surfaces\":6,\"cells\":2,"
              << "\"rotational_periodic_pair\":[901,902],"
              << "\"swept_selector_id\":903,\"transport_run\":false}\n";
    openmc::free_memory_geometry();
    openmc::free_memory_surfaces();
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native period region: " << error.what() << '\n';
    return 1;
  }
}
