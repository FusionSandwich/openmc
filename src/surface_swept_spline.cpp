#include "openmc/surface_swept_spline.h"

#include <filesystem>
#include <cstdlib>
#include <iostream>
#include <stdexcept>

#include <fmt/core.h>

#include "openmc/constants.h"
#include "openmc/error.h"
#include "openmc/hdf5_interface.h"
#include "openmc/settings.h"
#include "openmc/xml_interface.h"
#include "stellarcsg/swept_coefficient_file.hpp"
#include "stellarcsg/performance_counters.hpp"

namespace openmc {
namespace {
stellarcsg::Vec3 convert(Position value) { return {value.x, value.y, value.z}; }
Direction convert(stellarcsg::Vec3 value) { return {value.x, value.y, value.z}; }
}

SurfaceSweptSpline::SurfaceSweptSpline(pugi::xml_node node) : Surface(node)
{
  if (!check_for_node(node, "data_file") || !check_for_node(node, "dataset"))
    fatal_error(fmt::format(
      "Swept-spline surface {} requires data_file and dataset", id_));
  data_file_ = get_node_value(node, "data_file", false, true);
  dataset_ = get_node_value(node, "dataset", false, true);
  if (check_for_node(node, "content_id"))
    content_id_ = get_node_value(node, "content_id", false, true);
  if (check_for_node(node, "units")
      && get_node_value(node, "units", true, true) != "cm")
    fatal_error(fmt::format("Swept-spline surface {} requires units='cm'", id_));
  std::filesystem::path path {data_file_};
  if (path.is_relative()) path = std::filesystem::path {settings::path_input} / path;
  try {
    auto data = stellarcsg::read_swept_spline_surface_hdf5(
      path.lexically_normal().string(), dataset_, content_id_);
    if (content_id_.empty()) content_id_ = data.content_id;
    surface_ = std::make_unique<stellarcsg::CompiledSweptSplineSurface>(
      std::move(data));
  } catch (const std::exception& error) {
    fatal_error(fmt::format("Unable to initialize swept-spline surface {}: {}",
      id_, error.what()));
  }
}

SurfaceSweptSpline::~SurfaceSweptSpline()
{
  if (std::getenv("STELLARCSG_REPORT_COUNTERS") == nullptr
      || !stellarcsg::performance_counters_enabled()) return;
  const auto c = stellarcsg::performance_counters_snapshot();
  std::cerr << "STELLARCSG_COUNTERS {"
            << "\"distance_calls\":" << c.distance_calls << ','
            << "\"evaluate_calls\":" << c.evaluate_calls << ','
            << "\"normal_calls\":" << c.normal_calls << ','
            << "\"candidate_bvh_nodes\":" << c.candidate_bvh_nodes << ','
            << "\"candidate_spans\":" << c.candidate_patches_or_segments << ','
            << "\"proxy_seeds\":" << c.proxy_seeds << ','
            << "\"newton_iterations\":" << c.newton_iterations << ','
            << "\"newton_failures\":" << c.newton_failures << ','
            << "\"local_subdivision_calls\":" << c.local_subdivision_calls << ','
            << "\"global_reference_calls\":" << c.global_reference_calls << ','
            << "\"accepted_roots\":" << c.accepted_roots << ','
            << "\"no_hit_returns\":" << c.no_hit_returns << ','
            << "\"cache_hits\":" << c.cache_hits << ','
            << "\"cache_misses\":" << c.cache_misses << "}\n";
}

double SurfaceSweptSpline::evaluate(Position r) const
{
  return surface_->evaluate(convert(r));
}

double SurfaceSweptSpline::distance(Position r, Direction u, bool coincident) const
{
  stellarcsg::RootSearchOptions options;
  options.initial_subdivisions = 48;
  options.max_refinement_levels = 6;
  const auto result = surface_->distance(
    convert(r), convert(u), coincident, options);
  return result.found ? result.distance : INFTY;
}

Direction SurfaceSweptSpline::normal(Position r) const
{
  return convert(surface_->normal(convert(r)));
}

BoundingBox SurfaceSweptSpline::bounding_box(bool pos_side) const
{
  if (pos_side) return BoundingBox::infinite();
  const auto& box = surface_->bounding_box();
  return {{box.lower.x, box.lower.y, box.lower.z},
    {box.upper.x, box.upper.y, box.upper.z}};
}

void SurfaceSweptSpline::to_hdf5_inner(hid_t group) const
{
  write_string(group, "type", "swept-spline", false);
  write_string(group, "data_file", data_file_, false);
  write_string(group, "dataset", dataset_, false);
  write_string(group, "content_id", content_id_, false);
}

} // namespace openmc
