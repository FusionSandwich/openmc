#include "openmc/surface_facet_set.h"

#include <cmath>
#include <filesystem>
#include <stdexcept>
#include <utility>

#include <fmt/core.h>

#include "openmc/constants.h"
#include "openmc/error.h"
#include "openmc/hdf5_interface.h"
#include "openmc/settings.h"
#include "openmc/xml_interface.h"
#include "stellarcsg/facet_payload_file.hpp"

namespace openmc {
namespace {

stellarcsg::Vec3 convert(Position value) { return {value.x, value.y, value.z}; }
Direction to_direction(stellarcsg::Vec3 value)
{
  return {value.x, value.y, value.z};
}

} // namespace

SurfaceFacetSet::SurfaceFacetSet(pugi::xml_node node) : Surface(node)
{
  if (!check_for_node(node, "data_file") || !check_for_node(node, "dataset")
      || !check_for_node(node, "content_id")) {
    fatal_error(fmt::format("Facet-set surface {} requires data_file, "
                            "dataset and content_id", id_));
  }
  data_file_ = get_node_value(node, "data_file", false, true);
  dataset_ = get_node_value(node, "dataset", false, true);
  content_id_ = get_node_value(node, "content_id", false, true);
  if (check_for_node(node, "periodic_caps")) {
    periodic_caps_ = get_node_value(node, "periodic_caps", false, true);
    if (periodic_caps_ != "x0" && periodic_caps_ != "y0"
        && periodic_caps_ != "x0 y0")
      fatal_error(fmt::format("Facet-set surface {} periodic_caps must be "
                              "x0, y0 or 'x0 y0'", id_));
    skip_x_cap_ = periodic_caps_.find("x0") != std::string::npos;
    skip_y_cap_ = periodic_caps_.find("y0") != std::string::npos;
  }
  if (dataset_.empty() || dataset_.front() != '/')
    fatal_error(fmt::format("Facet-set surface {} requires an absolute "
                            "HDF5 dataset path", id_));
  if (check_for_node(node, "units")
      && get_node_value(node, "units", true, true) != "cm")
    fatal_error(fmt::format("Facet-set surface {} requires units='cm'", id_));
  if (check_for_node(node, "boundary")
      && get_node_value(node, "boundary", true, true) == "periodic")
    fatal_error(fmt::format("Facet-set surface {} cannot be periodic", id_));
  std::filesystem::path path {data_file_};
  if (path.is_relative()) path = std::filesystem::path {settings::path_input} / path;
  try {
    auto data = stellarcsg::read_facet_payload_hdf5(
      path.lexically_normal().string(), dataset_, content_id_);
    surface_ = std::make_unique<stellarcsg::CompiledFacetSurfaceSet>(
      std::move(data.triangles));
    if ((skip_x_cap_ && surface_->periodic_cap_count(0) == 0)
        || (skip_y_cap_ && surface_->periodic_cap_count(1) == 0))
      throw std::runtime_error("Requested periodic cap has no oriented triangles");
  } catch (const std::exception& error) {
    fatal_error(fmt::format("Unable to initialize facet-set surface {}: {}",
      id_, error.what()));
  }
}

double SurfaceFacetSet::evaluate(Position r) const
{
  const auto inside = surface_->contains(convert(r));
  if (!inside && surface_->normal_at(convert(r))) return 0.0;
  if (!inside)
    throw std::runtime_error("Facet-set surface " + std::to_string(id_)
                             + " has an unresolved side query");
  return *inside ? -1.0 : 1.0;
}

double SurfaceFacetSet::distance(Position r, Direction u, bool coincident) const
{
  const auto result = surface_->distance(convert(r), convert(u), coincident,
    skip_x_cap_, skip_y_cap_);
  if (result.terminal_unresolved)
    throw std::runtime_error("Facet-set surface " + std::to_string(id_)
                             + " has an unresolved nearest-boundary query");
  if (!result.found) return INFTY;
  if (!std::isfinite(result.distance) || !(result.distance > 0.0))
    throw std::runtime_error("Facet-set surface " + std::to_string(id_)
                             + " returned an invalid hit distance");
  return result.distance;
}

Direction SurfaceFacetSet::normal(Position r) const
{
  const auto value = surface_->normal_at(convert(r));
  if (!value)
    throw std::runtime_error("Facet-set surface " + std::to_string(id_)
                             + " has an unresolved local normal");
  return to_direction(*value);
}

BoundingBox SurfaceFacetSet::bounding_box(bool pos_side) const
{
  if (pos_side) return BoundingBox::infinite();
  const auto& box = surface_->bounding_box();
  return {{box.lower.x, box.lower.y, box.lower.z},
    {box.upper.x, box.upper.y, box.upper.z}};
}

void SurfaceFacetSet::to_hdf5_inner(hid_t group) const
{
  write_string(group, "type", "facet-set", false);
  write_string(group, "data_file", data_file_, false);
  write_string(group, "dataset", dataset_, false);
  write_string(group, "content_id", content_id_, false);
  if (!periodic_caps_.empty())
    write_string(group, "periodic_caps", periodic_caps_, false);
}

} // namespace openmc
