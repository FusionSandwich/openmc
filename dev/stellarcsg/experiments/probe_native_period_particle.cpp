// Exercise the native rotational periodic handoff at both sector planes.
// Test particles stay well outside every swept-coil bounding box.
#include "openmc/boundary_condition.h"
#include "openmc/cell.h"
#include "openmc/geometry.h"
#include "openmc/geometry_aux.h"
#include "openmc/particle.h"
#include "openmc/settings.h"
#include "openmc/surface.h"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
void cross_and_check(int from_id, int to_id, openmc::Position origin,
  openmc::Direction direction, openmc::Position expected_position,
  openmc::Direction expected_direction)
{
  const auto from_index = openmc::model::surface_map.at(from_id);
  const auto to_index = openmc::model::surface_map.at(to_id);
  const auto& plane = *openmc::model::surfaces.at(from_index);
  if (dynamic_cast<const openmc::RotationalPeriodicBC*>(plane.bc_.get()) == nullptr)
    throw std::runtime_error("native plane has no rotational periodic BC");
  openmc::Particle particle;
  openmc::Position interior = origin;
  interior[from_id == 901 ? 0 : 1] = 1e-3;
  particle.init_from_r_u(interior, direction);
  if (!openmc::exhaustive_find_cell(particle)
      || openmc::model::cells.at(particle.coord(0).cell())->id_ != 1002)
    throw std::runtime_error("periodic test particle was not located inside");
  particle.r() = origin;
  particle.id() = from_id;
  particle.wgt() = 1.0;
  particle.surface() = -(from_index + 1);
  plane.bc_->handle_particle(particle, plane);
  if (particle.surface() != to_index + 1
      || openmc::model::cells.at(particle.coord(0).cell())->id_ != 1002
      || particle.wgt() != 1.0)
    throw std::runtime_error("native periodic crossing lost cell or sense");
  for (int axis = 0; axis < 3; ++axis) {
    if (std::abs(particle.r()[axis] - expected_position[axis]) > 1e-9
        || std::abs(particle.u()[axis] - expected_direction[axis]) > 1e-12)
      throw std::runtime_error("native periodic rotation changed phase space");
  }
}
}

int main(int argc, char** argv)
{
  try {
    if (argc != 2)
      throw std::invalid_argument("usage: probe_native_period_particle XML_DIRECTORY");
    openmc::settings::path_input = std::string(argv[1]) + "/";
    openmc::read_geometry_xml();
    openmc::finalize_geometry();
    openmc::finalize_cell_densities();
    cross_and_check(901, 902, {0.0, 2300.0, 0.0}, {-1.0, 0.0, 0.0},
      {2300.0, 0.0, 0.0}, {0.0, 1.0, 0.0});
    cross_and_check(902, 901, {2300.0, 0.0, 0.0}, {0.0, -1.0, 0.0},
      {0.0, 2300.0, 0.0}, {1.0, 0.0, 0.0});
    std::cout << "{\"state\":\"NATIVE_PERIOD_PARTICLE_CROSSINGS_PASS\","
              << "\"crossings\":2,\"cell_id\":1002,"
              << "\"transport_histories\":0}\n";
    openmc::free_memory_geometry();
    openmc::free_memory_surfaces();
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native period particle: " << error.what() << '\n';
    return 1;
  }
}
