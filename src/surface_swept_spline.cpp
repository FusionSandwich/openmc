#include "openmc/surface_swept_spline.h"

#include <cassert>
#include <cmath>
#include <filesystem>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <atomic>
#include <map>
#include <mutex>
#include <tuple>
#include <limits>

#include <fmt/core.h>

#include "openmc/constants.h"
#include "openmc/error.h"
#include "openmc/hdf5_interface.h"
#include "openmc/settings.h"
#include "openmc/xml_interface.h"
#include "stellarcsg/swept_coefficient_file.hpp"
#include "stellarcsg/performance_counters.hpp"
#include "stellarcsg/sha256.hpp"

namespace openmc {

// Immutable geometry/options shared by member surfaces. Query results are
// thread-local and keyed by this owning context plus every ray component and
// coincidence flag. Holding the context prevents pointer-reuse cache aliases.
struct SweptSharedContext {
  std::shared_ptr<const stellarcsg::CompiledSweptSplineSurfaceSet> surfaces;
  stellarcsg::RootSearchOptions options;
  bool report_counters {false};
  mutable std::atomic<unsigned long long> traversals {0};
  mutable std::atomic<unsigned long long> cache_hits {0};
};

namespace {
stellarcsg::Vec3 convert(Position value) { return {value.x, value.y, value.z}; }
Direction convert(stellarcsg::Vec3 value) { return {value.x, value.y, value.z}; }

std::shared_ptr<const SweptSharedContext> shared_context(
  std::vector<stellarcsg::SweptSplineSurfaceData> coils)
{
  // Hash the actual parsed geometry and IDs, including uncanonicalized scalar
  // attributes. Reusing a filename/content_id alone permits stale geometry.
  stellarcsg::Sha256 hash;
  for (const auto& data : coils) {
    hash.update(&data.coil_id, sizeof(data.coil_id));
    hash.update(&data.sample_count, sizeof(data.sample_count));
    hash.update(&data.length, sizeof(data.length));
    hash.update(&data.characteristic_length, sizeof(data.characteristic_length));
    for (const auto* array : {&data.centerline_coefficients,
           &data.normal_coefficients, &data.binormal_coefficients,
           &data.major_radius_coefficients, &data.minor_radius_coefficients}) {
      const auto size = array->size();
      hash.update(&size, sizeof(size));
      hash.update(array->data(), size * sizeof(double));
    }
  }
  static std::mutex mutex;
  static std::map<std::string, std::weak_ptr<const SweptSharedContext>> registry;
  const auto key = hash.hex_digest();
  std::lock_guard<std::mutex> lock(mutex);
  auto& entry = registry[key];
  if (auto existing = entry.lock()) return existing;
  auto context = std::make_shared<SweptSharedContext>();
  context->surfaces = std::make_shared<stellarcsg::CompiledSweptSplineSurfaceSet>(
    std::move(coils));
  context->options.initial_subdivisions = 48;
  context->options.max_refinement_levels = 6;
  context->report_counters = std::getenv("STELLARCSG_REPORT_SHARED") != nullptr;
  entry = context;
  return context;
}

const std::vector<stellarcsg::DistanceResult>& shared_distances(
  const std::shared_ptr<const SweptSharedContext>& context,
  Position r, Direction u, bool coincident, std::size_t coincident_member)
{
  struct Cache {
    std::shared_ptr<const SweptSharedContext> owner;
    Position r;
    Direction u;
    bool coincident {false};
    std::size_t coincident_member {static_cast<std::size_t>(-1)};
    bool ready {false};
    std::vector<stellarcsg::DistanceResult> results;
  };
  static thread_local Cache cache;
  if (cache.ready && cache.owner == context && cache.coincident == coincident
      && cache.coincident_member == coincident_member
      && cache.r.x == r.x && cache.r.y == r.y && cache.r.z == r.z
      && cache.u.x == u.x && cache.u.y == u.y && cache.u.z == u.z) {
    if (context->report_counters)
      context->cache_hits.fetch_add(1, std::memory_order_relaxed);
    return cache.results;
  }
  cache.ready = false;
  cache.owner = context;
  cache.r = r;
  cache.u = u;
  cache.coincident = coincident;
  cache.coincident_member = coincident_member;
  if (context->report_counters)
    context->traversals.fetch_add(1, std::memory_order_relaxed);
  context->surfaces->distance_members(convert(r), convert(u), coincident,
    context->options, cache.results, coincident_member);
  cache.ready = true;
  return cache.results;
}
}

SurfaceSweptSpline::SurfaceSweptSpline(pugi::xml_node node) : Surface(node)
{
  const bool single = check_for_node(node, "dataset");
  const bool collection = check_for_node(node, "dataset_prefix")
                          && check_for_node(node, "dataset_count");
  if (!check_for_node(node, "data_file") || single == collection)
    fatal_error(fmt::format(
      "Swept-spline surface {} requires data_file and exactly one of dataset "
      "or dataset_prefix plus dataset_count", id_));
  data_file_ = get_node_value(node, "data_file", false, true);
  if (single) dataset_ = get_node_value(node, "dataset", false, true);
  if (collection) {
    dataset_prefix_ = get_node_value(node, "dataset_prefix", false, true);
    dataset_count_ = std::stoi(
      get_node_value(node, "dataset_count", false, true));
    if (check_for_node(node, "dataset_start")) {
      dataset_start_ = std::stoi(
        get_node_value(node, "dataset_start", false, true));
    }
    if (dataset_count_ <= 0) fatal_error(fmt::format(
      "Swept-spline surface {} requires a positive dataset_count", id_));
    if (dataset_start_ < 0 || dataset_start_ > std::numeric_limits<int>::max()
        - (dataset_count_ - 1))
      fatal_error("Swept-spline collection index range overflows");
    if (check_for_node(node, "member_id")) {
      member_id_ = std::stoi(get_node_value(node, "member_id", false, true));
      if (member_id_ < dataset_start_ || member_id_ - dataset_start_ >= dataset_count_)
        fatal_error("Swept-spline member_id must belong to the collection");
    }
  }
  if (single && check_for_node(node, "member_id"))
    fatal_error("Swept-spline member_id requires a collection");
  if (check_for_node(node, "content_id"))
    content_id_ = get_node_value(node, "content_id", false, true);
  if (check_for_node(node, "solver"))
    solver_ = get_node_value(node, "solver", true, true);
  if (solver_ != "auto" && solver_ != "general")
    fatal_error(fmt::format("Swept-spline surface {} requires solver='auto' "
                            "or 'general'; received '{}'", id_, solver_));
  if (collection && solver_ != "auto")
    fatal_error(fmt::format("Swept-spline collection surface {} currently "
                            "requires solver='auto'", id_));
  if (check_for_node(node, "units")
      && get_node_value(node, "units", true, true) != "cm")
    fatal_error(fmt::format("Swept-spline surface {} requires units='cm'", id_));
  std::filesystem::path path {data_file_};
  if (path.is_relative()) path = std::filesystem::path {settings::path_input} / path;
  try {
    const auto filename = path.lexically_normal().string();
    if (single) {
      auto data = stellarcsg::read_swept_spline_surface_hdf5(
        filename, dataset_, content_id_);
      if (content_id_.empty()) content_id_ = data.content_id;
      surface_ = std::make_unique<stellarcsg::CompiledSweptSplineSurface>(
        std::move(data), solver_ == "general");
    } else {
      if (!content_id_.empty()) fatal_error(fmt::format(
        "Swept-spline collection surface {} uses per-coil content IDs and "
        "must not specify content_id", id_));
      std::vector<stellarcsg::SweptSplineSurfaceData> coils;
      coils.reserve(static_cast<std::size_t>(dataset_count_));
      for (int offset = 0; offset < dataset_count_; ++offset) {
        const int coil_id = dataset_start_ + offset;
        coils.push_back(stellarcsg::read_swept_spline_surface_hdf5(
          filename, fmt::format("{}{:03d}", dataset_prefix_, coil_id)));
        if (coils.back().coil_id != coil_id)
          throw std::invalid_argument(
            "Shared collection coil_id must match its declared dataset suffix");
      }
      shared_context_ = shared_context(std::move(coils));
      surface_set_ = shared_context_->surfaces;
      if (member_id_ >= 0)
        member_index_ = surface_set_->member_index(member_id_);
    }
  } catch (const std::exception& error) {
    fatal_error(fmt::format("Unable to initialize swept-spline surface {}: {}",
      id_, error.what()));
  }
  use_native_exact_torus_ = surface_ && solver_ == "auto"
    && surface_->exact_torus_specialization();
  if (use_native_exact_torus_)
    exact_torus_ = surface_->exact_circular_torus_parameters();
  root_options_.initial_subdivisions = 48;
  root_options_.max_refinement_levels = 6;
}

SurfaceSweptSpline::~SurfaceSweptSpline()
{
  if (shared_context_ && std::getenv("STELLARCSG_REPORT_SHARED"))
    std::cerr << "STELLARCSG_SHARED surface=" << id_
              << " traversals=" << shared_context_->traversals.load()
              << " cache_hits=" << shared_context_->cache_hits.load() << '\n';
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
  try {
  if (!std::isfinite(r.x) || !std::isfinite(r.y) || !std::isfinite(r.z))
    throw std::invalid_argument("Swept classification point must be finite");
  // Region classification only needs the sign. A point outside the member's
  // conservative control hull cannot be inside its finite solid.
  if (!use_native_exact_torus_ && (surface_ || member_id_ >= 0)) {
    const auto& box = surface_ ? surface_->bounding_box()
      : surface_set_->member(member_index_).bounding_box();
    if (r.x < box.lower.x || r.x > box.upper.x || r.y < box.lower.y
        || r.y > box.upper.y || r.z < box.lower.z || r.z > box.upper.z)
      return 1.0;
  }
  if (member_id_ >= 0)
    return surface_set_->member(member_index_).evaluate(convert(r));
  if (use_native_exact_torus_) {
    const double radial_offset = std::hypot(r.x, r.y)
      - exact_torus_.major_radius;
    return std::hypot(radial_offset, r.z - exact_torus_.z_offset)
      - exact_torus_.minor_radius;
  }
  return surface_ ? surface_->evaluate(convert(r))
                  : surface_set_->evaluate(convert(r));
  } catch (const std::exception& error) {
    fatal_error(fmt::format("Unresolved swept-spline classification on surface {}: {}",
      id_, error.what()));
  }
}

double SurfaceSweptSpline::distance(Position r, Direction u, bool coincident) const
{
  try {
  if (use_native_exact_torus_) {
#ifndef NDEBUG
    assert(std::abs(u.norm() - 1.0) < 1.0e-10);
#endif
    return torus_distance(r.x, r.y, r.z - exact_torus_.z_offset,
      u.x, u.y, u.z, exact_torus_.major_radius,
      exact_torus_.minor_radius, exact_torus_.minor_radius, coincident);
  }
  if (surface_) {
    const auto result = surface_->distance(
      convert(r), convert(u), coincident, root_options_);
    if (result.root_diagnostics.unresolved_intervals != 0)
      throw std::runtime_error("Unresolved swept intersection interval");
    return result.found ? result.distance : INFTY;
  }
  const auto& results = shared_distances(shared_context_, r, u, coincident,
    coincident && member_id_ >= 0 ? member_index_ : static_cast<std::size_t>(-1));
  if (member_id_ >= 0) {
    const auto& result = results.at(member_index_);
    return result.found ? result.distance : INFTY;
  }
  double nearest = INFTY;
  for (const auto& result : results)
    if (result.found) nearest = std::min(nearest, result.distance);
  return nearest;
  } catch (const std::exception& error) {
    fatal_error(fmt::format("Unresolved swept-spline distance on surface {}: {}",
      id_, error.what()));
  }
}

Direction SurfaceSweptSpline::normal(Position r) const
{
  try {
  if (!std::isfinite(r.x) || !std::isfinite(r.y) || !std::isfinite(r.z))
    throw std::invalid_argument("Swept normal point must be finite");
  if (member_id_ >= 0)
    return convert(surface_set_->member(member_index_).normal(convert(r)));
  if (use_native_exact_torus_) {
    const double z = r.z - exact_torus_.z_offset;
    const double radial = std::hypot(r.x, r.y);
    const double radial_offset = radial - exact_torus_.major_radius;
    const double nx = r.x * radial_offset;
    const double ny = r.y * radial_offset;
    const double nz = radial * z;
    const double inverse_norm = 1.0 / std::sqrt(
      nx * nx + ny * ny + nz * nz);
    return {nx * inverse_norm, ny * inverse_norm, nz * inverse_norm};
  }
  return convert(surface_ ? surface_->normal(convert(r))
                          : surface_set_->normal(convert(r)));
  } catch (const std::exception& error) {
    fatal_error(fmt::format("Unresolved swept-spline normal on surface {}: {}",
      id_, error.what()));
  }
}

BoundingBox SurfaceSweptSpline::bounding_box(bool pos_side) const
{
  if (pos_side) return BoundingBox::infinite();
  const auto& box = surface_ ? surface_->bounding_box() : member_id_ >= 0
    ? surface_set_->member(member_index_).bounding_box() : surface_set_->bounding_box();
  return {{box.lower.x, box.lower.y, box.lower.z},
    {box.upper.x, box.upper.y, box.upper.z}};
}

void SurfaceSweptSpline::to_hdf5_inner(hid_t group) const
{
  write_string(group, "type", "swept-spline", false);
  write_string(group, "data_file", data_file_, false);
  if (surface_) {
    write_string(group, "dataset", dataset_, false);
    write_string(group, "content_id", content_id_, false);
    write_string(group, "solver", solver_, false);
  } else {
    write_string(group, "dataset_prefix", dataset_prefix_, false);
    write_dataset(group, "dataset_start", dataset_start_);
    write_dataset(group, "dataset_count", dataset_count_);
    if (member_id_ >= 0) write_dataset(group, "member_id", member_id_);
  }
}

} // namespace openmc
