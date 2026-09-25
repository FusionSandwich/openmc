#include "stellarcsg/compiled_swept_surface_set.hpp"

#include "stellarcsg/performance_counters.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <numeric>
#include <optional>
#include <stdexcept>
#include <unordered_set>
#include <utility>

namespace stellarcsg {
namespace {

BoundingBox empty_box()
{
  return {{std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity()},
          {-std::numeric_limits<double>::infinity(),
            -std::numeric_limits<double>::infinity(),
            -std::numeric_limits<double>::infinity()}};
}

void extend(BoundingBox& box, const Vec3& point)
{
  box.lower.x = std::min(box.lower.x, point.x);
  box.lower.y = std::min(box.lower.y, point.y);
  box.lower.z = std::min(box.lower.z, point.z);
  box.upper.x = std::max(box.upper.x, point.x);
  box.upper.y = std::max(box.upper.y, point.y);
  box.upper.z = std::max(box.upper.z, point.z);
}

void extend(BoundingBox& box, const BoundingBox& other)
{
  extend(box, other.lower);
  extend(box, other.upper);
}

Vec3 centroid(const BoundingBox& box)
{
  return 0.5 * (box.lower + box.upper);
}

bool contains(const BoundingBox& box, const Vec3& point)
{
  return point.x >= box.lower.x && point.x <= box.upper.x
         && point.y >= box.lower.y && point.y <= box.upper.y
         && point.z >= box.lower.z && point.z <= box.upper.z;
}

} // namespace

CompiledSweptSplineSurfaceSet::CompiledSweptSplineSurfaceSet(
  std::vector<SweptSplineSurfaceData> coils)
{
  if (coils.empty()) {
    throw std::invalid_argument("Swept-spline surface set cannot be empty");
  }
  coils_.reserve(coils.size());
  coil_ids_.reserve(coils.size());
  std::unordered_set<int> seen_ids;
  for (auto& data : coils) {
    if (!seen_ids.insert(data.coil_id).second) {
      throw std::invalid_argument("Swept-spline surface member IDs must be unique");
    }
    coil_ids_.push_back(data.coil_id);
    coils_.push_back(
      std::make_unique<CompiledSweptSplineSurface>(std::move(data)));
  }
  indices_.resize(coils_.size());
  std::iota(indices_.begin(), indices_.end(), 0U);
  bvh_.reserve(2 * coils_.size());
  (void) build_node(0U, static_cast<std::uint32_t>(coils_.size()));
  bounds_ = bvh_.front().bbox;
}

std::uint32_t CompiledSweptSplineSurfaceSet::build_node(
  std::uint32_t first, std::uint32_t last)
{
  const auto node_index = static_cast<std::uint32_t>(bvh_.size());
  bvh_.push_back({});
  BoundingBox bounds = empty_box();
  BoundingBox centroids = empty_box();
  for (std::uint32_t i = first; i < last; ++i) {
    const auto& box = coils_[indices_[i]]->bounding_box();
    extend(bounds, box);
    extend(centroids, centroid(box));
  }
  bvh_[node_index].bbox = bounds;
  const std::uint32_t count = last - first;
  constexpr std::uint32_t leaf_size = 2;
  if (count <= leaf_size) {
    bvh_[node_index].first = first;
    bvh_[node_index].count = static_cast<std::uint16_t>(count);
    return node_index;
  }
  const Vec3 extent = centroids.upper - centroids.lower;
  const int axis = extent.y > extent.x ? (extent.z > extent.y ? 2 : 1)
                                      : (extent.z > extent.x ? 2 : 0);
  const auto component = [](const Vec3& value, int selected) {
    return selected == 0 ? value.x : (selected == 1 ? value.y : value.z);
  };
  const std::uint32_t middle = first + count / 2;
  std::nth_element(indices_.begin() + first, indices_.begin() + middle,
    indices_.begin() + last, [&](std::uint32_t lhs, std::uint32_t rhs) {
      return component(centroid(coils_[lhs]->bounding_box()), axis)
             < component(centroid(coils_[rhs]->bounding_box()), axis);
    });
  bvh_[node_index].left = build_node(first, middle);
  bvh_[node_index].right = build_node(middle, last);
  return node_index;
}

double CompiledSweptSplineSurfaceSet::evaluate(const Vec3& point) const
{
  std::array<std::uint32_t, 64> stack {};
  std::size_t stack_size = 0;
  stack[stack_size++] = 0U;
  double best_positive = std::numeric_limits<double>::infinity();
  double most_negative = 0.0;
  bool inside = false;
  while (stack_size != 0) {
    const auto& node = bvh_[stack[--stack_size]];
    if (!contains(node.bbox, point)) continue;
    if (node.leaf()) {
      for (std::uint32_t local = 0; local < node.count; ++local) {
        const auto coil_index = indices_[node.first + local];
        if (!contains(coils_[coil_index]->bounding_box(), point)) continue;
        const double value = coils_[coil_index]->evaluate(point);
        if (!std::isfinite(value)) {
          throw std::runtime_error("Swept-spline member classification is nonfinite");
        }
        if (value <= 0.0) {
          most_negative = inside ? std::min(most_negative, value) : value;
          inside = true;
        } else {
          best_positive = std::min(best_positive, value);
        }
      }
    } else {
      stack[stack_size++] = node.left;
      stack[stack_size++] = node.right;
    }
  }
  if (inside) return most_negative;
  return std::isfinite(best_positive) ? best_positive : 1.0;
}

Vec3 CompiledSweptSplineSurfaceSet::normal(const Vec3& point) const
{
  std::array<std::uint32_t, 64> stack {};
  std::size_t stack_size = 0;
  stack[stack_size++] = 0U;
  double best = std::numeric_limits<double>::infinity();
  std::size_t best_coil = coils_.size();
  while (stack_size != 0) {
    const auto& node = bvh_[stack[--stack_size]];
    if (!contains(node.bbox, point)) continue;
    if (node.leaf()) {
      for (std::uint32_t local = 0; local < node.count; ++local) {
        const auto coil_index = indices_[node.first + local];
        if (!contains(coils_[coil_index]->bounding_box(), point)) continue;
        const double residual = std::abs(coils_[coil_index]->evaluate(point));
        if (!std::isfinite(residual)) {
          throw std::runtime_error("Swept-spline member normal ownership is nonfinite");
        }
        if (residual < best || (residual == best &&
            (best_coil == coils_.size() || coil_ids_[coil_index] < coil_ids_[best_coil]))) {
          best = residual;
          best_coil = coil_index;
        }
      }
    } else {
      stack[stack_size++] = node.left;
      stack[stack_size++] = node.right;
    }
  }
  if (best_coil == coils_.size()) {
    throw std::runtime_error("Point is outside every swept-coil bound");
  }
  return coils_[best_coil]->normal(point);
}

SweptCoilSetDistanceResult CompiledSweptSplineSurfaceSet::distance(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0) || !std::isfinite(direction_norm)) {
    throw std::invalid_argument("Ray direction must be finite and non-zero");
  }
  const Vec3 ray_direction = direction / direction_norm;
  const auto root_interval = bounds_.ray_interval(origin, ray_direction);
  if (!root_interval || root_interval->exit < 0.0) return {};
  struct StackEntry { std::uint32_t node; double near_t; };
  std::array<StackEntry, 64> stack {};
  std::size_t stack_size = 0;
  stack[stack_size++] = {0U, root_interval->enter};
  double best_t = std::numeric_limits<double>::infinity();
  SweptCoilSetDistanceResult result;
  while (stack_size != 0) {
    const auto entry = stack[--stack_size];
    if (entry.near_t > best_t) continue;
    const auto& node = bvh_[entry.node];
    add_performance_counter(PerformanceCounter::candidate_bvh_nodes);
    if (node.leaf()) {
      for (std::uint32_t local = 0; local < node.count; ++local) {
        const auto coil_index = indices_[node.first + local];
        const auto interval = coils_[coil_index]->bounding_box().ray_interval(
          origin, ray_direction);
        if (!interval || interval->exit < 0.0 || interval->enter > best_t)
          continue;
        const auto candidate = coils_[coil_index]->distance(
          origin, ray_direction, coincident, options);
        if (candidate.disposition() == DistanceDisposition::unresolved) {
          throw std::runtime_error(
            "Swept-spline member has an unresolved nearest-boundary query");
        }
        if (candidate.found &&
            (!(candidate.distance >= 0.0) || !std::isfinite(candidate.distance))) {
          throw std::runtime_error("Swept-spline member returned invalid hit distance");
        }
        if (candidate.found && (candidate.distance < best_t ||
            (candidate.distance == best_t && coil_ids_[coil_index] < result.coil_id))) {
          best_t = candidate.distance;
          result.root = candidate;
          result.coil_id = coil_ids_[coil_index];
          result.coil_index = coil_index;
        }
      }
      continue;
    }
    const auto left = bvh_[node.left].bbox.ray_interval(origin, ray_direction);
    const auto right = bvh_[node.right].bbox.ray_interval(origin, ray_direction);
    const bool use_left = left && left->exit >= 0.0 && left->enter <= best_t;
    const bool use_right = right && right->exit >= 0.0 && right->enter <= best_t;
    if (use_left && use_right) {
      const bool left_first = left->enter <= right->enter;
      stack[stack_size++] = left_first
        ? StackEntry {node.right, right->enter}
        : StackEntry {node.left, left->enter};
      stack[stack_size++] = left_first
        ? StackEntry {node.left, left->enter}
        : StackEntry {node.right, right->enter};
    } else if (use_left || use_right) {
      stack[stack_size++] = use_left
        ? StackEntry {node.left, left->enter}
        : StackEntry {node.right, right->enter};
    }
  }
  if (!result.root.found) return result;

  // The first constituent crossing is a union crossing only when no other
  // member contains that point.  Keep the usual BVH path for the common
  // nonoverlapping case; an overlap needs an ordered walk of member roots.
  const auto masked_by_another = [&](const Vec3& point,
                                     std::size_t owner) {
    for (std::size_t index = 0; index < coils_.size(); ++index) {
      if (index == owner || !contains(coils_[index]->bounding_box(), point))
        continue;
      const double value = coils_[index]->evaluate(point);
      if (!std::isfinite(value)) {
        throw std::runtime_error(
          "Swept-spline member overlap classification is nonfinite");
      }
      if (value < 0.0) return true;
    }
    return false;
  };
  if (!masked_by_another(origin + best_t * ray_direction,
                        result.coil_index)) return result;

  struct Event {
    std::size_t index;
    double t;
    DistanceResult root;
  };
  std::vector<std::optional<Event>> events(coils_.size());
  const auto next_event = [&](std::size_t index, double from_t,
                              bool suppress_origin) -> std::optional<Event> {
    const Vec3 from = origin + from_t * ray_direction;
    const auto interval = coils_[index]->bounding_box().ray_interval(
      from, ray_direction);
    if (!interval || interval->exit < 0.0) return std::nullopt;
    auto root = coils_[index]->distance(
      from, ray_direction, suppress_origin, options);
    if (root.disposition() == DistanceDisposition::unresolved) {
      throw std::runtime_error(
        "Swept-spline member has an unresolved nearest-boundary query");
    }
    if (!root.found) return std::nullopt;
    const double t = from_t + root.distance;
    if (!(root.distance >= 0.0) || !std::isfinite(t)
        || (suppress_origin && !(t > from_t))) {
      throw std::runtime_error(
        "Swept-spline member did not advance to a finite next boundary");
    }
    return Event {index, t, root};
  };
  for (std::size_t index = 0; index < coils_.size(); ++index) {
    events[index] = next_event(index, 0.0, coincident);
  }
  constexpr std::size_t max_masked_events = 4096;
  for (std::size_t count = 0; count < max_masked_events; ++count) {
    std::optional<Event> first;
    for (const auto& event : events) {
      if (event && (!first || event->t < first->t
          || (event->t == first->t
              && coil_ids_[event->index] < coil_ids_[first->index]))) {
        first = event;
      }
    }
    if (!first) return {};
    const Vec3 point = origin + first->t * ray_direction;
    if (!masked_by_another(point, first->index)) {
      SweptCoilSetDistanceResult exterior;
      exterior.root = first->root;
      exterior.root.distance = first->t;
      exterior.coil_id = coil_ids_[first->index];
      exterior.coil_index = first->index;
      return exterior;
    }
    events[first->index] = next_event(first->index, first->t, true);
  }
  throw std::runtime_error(
    "Swept-spline union boundary event budget exhausted");
}

} // namespace stellarcsg
