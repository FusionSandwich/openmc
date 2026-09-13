#include "stellarcsg/compiled_swept_surface_set.hpp"

#include "stellarcsg/performance_counters.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
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
  if (coils.size() > std::numeric_limits<std::uint32_t>::max() / 2)
    throw std::invalid_argument("Shared swept set exceeds uint32 BVH capacity");
  coils_.reserve(coils.size());
  coil_ids_.reserve(coils.size());
  for (auto& data : coils) {
    if (std::find(coil_ids_.begin(), coil_ids_.end(), data.coil_id) != coil_ids_.end())
      throw std::invalid_argument("Shared swept set contains duplicate coil IDs");
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
        if (residual < best) {
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

// Outward rounding of each slab arithmetic operation; only exact zero is
// parallel. Near-zero directions cannot justify discarding a distant hit.
static bool ray_may_intersect(
  const BoundingBox& box, const Vec3& origin, const Vec3& direction)
{
  const double infinity = std::numeric_limits<double>::infinity();
  double enter = 0.0;
  double exit = infinity;
  for (int i = 0; i != 3; ++i) {
    const double o = i == 0 ? origin.x : i == 1 ? origin.y : origin.z;
    const double d = i == 0 ? direction.x : i == 1 ? direction.y : direction.z;
    const double lo = i == 0 ? box.lower.x : i == 1 ? box.lower.y : box.lower.z;
    const double hi = i == 0 ? box.upper.x : i == 1 ? box.upper.y : box.upper.z;
    if (d == 0.0) {
      if (o < lo || o > hi) return false;
      continue;
    }
    double a = std::nextafter(lo - o, -infinity);
    double b = std::nextafter(hi - o, infinity);
    if (d < 0.0) std::swap(a, b);
    a = std::nextafter(a / d, -infinity);
    b = std::nextafter(b / d, infinity);
    enter = std::max(enter, a);
    exit = std::min(exit, b);
    if (enter > exit) return false;
  }
  return true;
}

std::size_t CompiledSweptSplineSurfaceSet::member_index(int coil_id) const
{
  const auto found = std::find(coil_ids_.begin(), coil_ids_.end(), coil_id);
  if (found == coil_ids_.end())
    throw std::invalid_argument("Requested coil ID is absent from shared set");
  return static_cast<std::size_t>(found - coil_ids_.begin());
}

void CompiledSweptSplineSurfaceSet::distance_members(const Vec3& origin,
  const Vec3& direction, bool coincident, const RootSearchOptions& options,
  std::vector<DistanceResult>& results, std::size_t coincident_member) const
{
  if (!std::isfinite(origin.x) || !std::isfinite(origin.y)
      || !std::isfinite(origin.z) || !std::isfinite(direction.x)
      || !std::isfinite(direction.y) || !std::isfinite(direction.z)
      || !(std::hypot(direction.x, direction.y, direction.z) > 0.0)
      || !std::isfinite(std::hypot(direction.x, direction.y, direction.z)))
    throw std::invalid_argument("Shared swept ray must be finite and nonzero");
  if (coincident && coincident_member == static_cast<std::size_t>(-1)) {
    // A union has no declared crossed member. The separated-box domain can
    // identify it uniquely; overlapping/missing bounds require explicit
    // unresolved status rather than suppressing roots of unrelated coils.
    for (std::size_t i = 0; i != coils_.size(); ++i) {
      if (contains(coils_[i]->bounding_box(), origin)) {
        if (coincident_member != static_cast<std::size_t>(-1))
          throw std::runtime_error("Ambiguous coincident member of swept union");
        coincident_member = i;
      }
    }
    if (coincident_member == static_cast<std::size_t>(-1))
      throw std::runtime_error("Missing coincident member of swept union");
  }
  if (coincident && coincident_member >= coils_.size())
    throw std::invalid_argument("Coincident swept member index is out of range");
  results.assign(coils_.size(), DistanceResult {});
  std::array<std::uint32_t, 64> stack {};
  std::size_t size = 0;
  stack[size++] = 0U;
  while (size != 0) {
    const auto& node = bvh_[stack[--size]];
    add_performance_counter(PerformanceCounter::candidate_bvh_nodes);
    // The crossed member may need a small negative root to associate a
    // rounded origin. A forward-only slab cannot exclude that member.
    if (!coincident && !ray_may_intersect(node.bbox, origin, direction)) continue;
    if (node.leaf()) {
      for (std::uint32_t local = 0; local < node.count; ++local) {
        const auto index = indices_[node.first + local];
        if (!(coincident && index == coincident_member)
            && !ray_may_intersect(coils_[index]->bounding_box(), origin, direction))
          continue;
        // Every potentially intersected member is resolved. Exceptions and
        // unresolved diagnostics must reach the caller; never publish a cache
        // containing partial results after a failed member solve.
        results[index] = coils_[index]->distance(origin, direction,
          coincident && index == coincident_member, options);
        if (results[index].root_diagnostics.unresolved_intervals != 0)
          throw std::runtime_error("Unresolved member in shared swept query");
      }
    } else {
      // Median uint32 tree depth is bounded, but never silently truncate.
      if (size + 2 > stack.size())
        throw std::runtime_error("Shared swept traversal capacity exhausted");
      stack[size++] = node.left;
      stack[size++] = node.right;
    }
  }
}

SweptCoilSetDistanceResult CompiledSweptSplineSurfaceSet::distance(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  std::vector<DistanceResult> members;
  distance_members(origin, direction, coincident, options, members);
  SweptCoilSetDistanceResult result;
  for (std::size_t i = 0; i != members.size(); ++i) {
    if (members[i].found && members[i].distance < result.root.distance) {
      result.root = members[i];
      result.coil_id = coil_ids_[i];
      result.coil_index = i;
    }
  }
  return result;
}

} // namespace stellarcsg
