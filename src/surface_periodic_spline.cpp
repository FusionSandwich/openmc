#include "openmc/surface_periodic_spline.h"

#include <filesystem>
#include <stdexcept>
#include <string>
#include <utility>

#include <fmt/core.h>

#include "openmc/constants.h"
#include "openmc/error.h"
#include "openmc/hdf5_interface.h"
#include "openmc/settings.h"
#include "openmc/xml_interface.h"
#include "stellarcsg/coefficient_file.hpp"

namespace openmc {
namespace {

stellarcsg::Vec3 to_vec3(Position value)
{
  return {value.x, value.y, value.z};
}

Direction to_direction(stellarcsg::Vec3 value)
{
  return {value.x, value.y, value.z};
}

std::string resolve_input_path(const std::string& filename)
{
  std::filesystem::path path {filename};
  if (path.is_relative()) {
    path = std::filesystem::path {settings::path_input} / path;
  }
  return path.lexically_normal().string();
}

} // namespace

SurfacePeriodicSpline::SurfacePeriodicSpline(pugi::xml_node surf_node)
  : Surface(surf_node)
{
  if (!check_for_node(surf_node, "data_file")) {
    fatal_error(
      fmt::format("Periodic-spline surface {} requires data_file", id_));
  }
  if (!check_for_node(surf_node, "dataset")) {
    fatal_error(fmt::format("Periodic-spline surface {} requires dataset", id_));
  }

  data_file_ = get_node_value(surf_node, "data_file", false, true);
  dataset_ = get_node_value(surf_node, "dataset", false, true);
  if (check_for_node(surf_node, "content_id")) {
    content_id_ = get_node_value(surf_node, "content_id", false, true);
  }
  if (check_for_node(surf_node, "solver")) {
    solver_ = get_node_value(surf_node, "solver", true, true);
  }
  if (check_for_node(surf_node, "units") &&
      get_node_value(surf_node, "units", true, true) != "cm") {
    fatal_error(fmt::format(
      "Periodic-spline surface {} requires units='cm'", id_));
  }
  if (solver_ != "reference") {
    fatal_error(fmt::format("Periodic-spline surface {} only supports "
                            "solver='reference'; received '{}'",
      id_, solver_));
  }

  resolved_data_file_ = resolve_input_path(data_file_);
  try {
    auto data = stellarcsg::read_periodic_spline_surface_hdf5(
      resolved_data_file_, dataset_, content_id_);
    if (content_id_.empty()) content_id_ = data.content_id;
    surface_ = std::make_unique<stellarcsg::CompiledPeriodicSplineSurface>(
      std::move(data));
  } catch (const std::exception& error) {
    fatal_error(fmt::format(
      "Unable to initialize periodic-spline surface {} from '{}:{}': {}",
      id_, resolved_data_file_, dataset_, error.what()));
  }
}

double SurfacePeriodicSpline::evaluate(Position r) const
{
  return surface_->evaluate(to_vec3(r));
}

double SurfacePeriodicSpline::distance(
  Position r, Direction u, bool coincident) const
{
  stellarcsg::RootSearchOptions options;
  options.initial_subdivisions = 96;
  options.max_refinement_levels = 7;
  options.require_refinement_stability = true;
  const auto result = surface_->distance_reference(
    to_vec3(r), to_vec3(u), coincident, options);
  return result.found ? result.distance : INFTY;
}

Direction SurfacePeriodicSpline::normal(Position r) const
{
  return to_direction(surface_->normal(to_vec3(r)));
}

BoundingBox SurfacePeriodicSpline::bounding_box(bool pos_side) const
{
  if (pos_side) return BoundingBox::infinite();
  const auto& box = surface_->bounding_box();
  return {{box.lower.x, box.lower.y, box.lower.z},
    {box.upper.x, box.upper.y, box.upper.z}};
}

void SurfacePeriodicSpline::to_hdf5_inner(hid_t group_id) const
{
  write_string(group_id, "type", "periodic-spline", false);
  write_string(group_id, "data_file", data_file_, false);
  write_string(group_id, "dataset", dataset_, false);
  write_string(group_id, "content_id", content_id_, false);
  write_string(group_id, "solver", solver_, false);
}

} // namespace openmc
