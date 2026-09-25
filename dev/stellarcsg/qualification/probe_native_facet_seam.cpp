// Inspect first native boundary ownership on each accepted-mesh period cap.
#include "openmc/cell.h"
#include "openmc/boundary_condition.h"
#include "openmc/geometry.h"
#include "openmc/geometry_aux.h"
#include "openmc/particle.h"
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "stellarcsg/facet_payload_file.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
  try {
    if (argc != 4)
      throw std::invalid_argument("usage: probe_native_facet_seam REGION PAYLOAD CONTENT_ID");
    openmc::settings::path_input = std::string(argv[1]) + "/";
    openmc::read_geometry_xml();
    openmc::finalize_geometry();
    openmc::finalize_cell_densities();
    const auto payload = stellarcsg::read_facet_payload_hdf5(
      argv[2], "/facets/one_period", argv[3]);
    int cap_count[2] {0, 0};
    int facet_first[2] {0, 0};
    int plane_first[2] {0, 0};
    int coil_handoff[2] {0, 0};
    int further_facet_hit[2] {0, 0};
    for (const auto& triangle : payload.triangles) {
      const stellarcsg::Vec3 center = (triangle.a + triangle.b + triangle.c) / 3.0;
      for (int axis = 0; axis < 2; ++axis) {
        const double a = axis == 0 ? triangle.a.x : triangle.a.y;
        const double b = axis == 0 ? triangle.b.x : triangle.b.y;
        const double c = axis == 0 ? triangle.c.x : triangle.c.y;
        if (std::max({std::abs(a), std::abs(b), std::abs(c)}) > 1e-10)
          continue;
        ++cap_count[axis];
        openmc::Position point {center.x, center.y, center.z};
        point[axis] = 1e-3;
        openmc::Direction direction {0.0, 0.0, 0.0};
        direction[axis] = -1.0;
        openmc::Particle particle;
        particle.init_from_r_u(point, direction);
        if (!openmc::exhaustive_find_cell(particle)
            || openmc::model::cells.at(particle.coord(0).cell())->id_ != 1001)
          throw std::runtime_error("cap interior particle not in coil cell");
        const auto info = openmc::distance_to_boundary(particle);
        const int surface_index = std::abs(info.surface()) - 1;
        if (surface_index < 0)
          throw std::runtime_error("no finite first cap boundary");
        const int id = openmc::model::surfaces.at(surface_index)->id_;
        if (id == 903) ++facet_first[axis];
        else if (id == (axis == 0 ? 901 : 902)) ++plane_first[axis];
        else throw std::runtime_error("unexpected first cap boundary");
        const double facet = openmc::model::surfaces.at(
          openmc::model::surface_map.at(903))->distance(
            point, direction, false);
        if (facet < 1e300) ++further_facet_hit[axis];
        if (id == (axis == 0 ? 901 : 902)) {
          const int plane_index = openmc::model::surface_map.at(id);
          const auto& plane = *openmc::model::surfaces.at(plane_index);
          particle.r()[axis] = 0.0;
          particle.id() = id;
          particle.wgt() = 1.0;
          particle.surface() = -(plane_index + 1);
          plane.bc_->handle_particle(particle, plane);
          if (openmc::model::cells.at(particle.coord(0).cell())->id_ != 1001
              || particle.wgt() != 1.0)
            throw std::runtime_error("periodic cap handoff left coil cell");
          ++coil_handoff[axis];
        }
      }
    }
    std::cout << "{\"cap_count\":[" << cap_count[0] << ',' << cap_count[1]
              << "],\"facet_first\":[" << facet_first[0] << ','
              << facet_first[1] << "],\"periodic_plane_first\":["
              << plane_first[0] << ',' << plane_first[1]
              << "],\"coil_handoff\":["
              << coil_handoff[0] << ',' << coil_handoff[1]
              << "],\"further_facet_hit\":["
              << further_facet_hit[0] << ',' << further_facet_hit[1]
              << "],\"histories\":0}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native facet seam: " << error.what() << '\n';
    return 1;
  }
}
