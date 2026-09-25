#include "stellarcsg/compiled_facet_surface_set.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <limits>
#include <map>
#include <numeric>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace stellarcsg {
namespace {

using VertexBits = std::array<std::uint64_t, 3>;
using EdgeBits = std::pair<VertexBits, VertexBits>;

struct EdgeAudit {
  int count {0};
  int orientation {0};
};

struct LongVec {
  long double x, y, z;
};

LongVec as_long(const Vec3& value)
{
  return {value.x, value.y, value.z};
}

LongVec operator-(LongVec lhs, LongVec rhs)
{
  return {lhs.x - rhs.x, lhs.y - rhs.y, lhs.z - rhs.z};
}

long double dot_long(LongVec lhs, LongVec rhs)
{
  return lhs.x*rhs.x + lhs.y*rhs.y + lhs.z*rhs.z;
}

LongVec cross_long(LongVec lhs, LongVec rhs)
{
  return {lhs.y*rhs.z - lhs.z*rhs.y,
    lhs.z*rhs.x - lhs.x*rhs.z,
    lhs.x*rhs.y - lhs.y*rhs.x};
}

long double length_long(LongVec value)
{
  return std::sqrt(dot_long(value, value));
}

bool finite(const Vec3& value)
{
  return std::isfinite(value.x) && std::isfinite(value.y)
    && std::isfinite(value.z);
}

VertexBits bits(const Vec3& value)
{
  const std::array<double, 3> values {
    value.x == 0.0 ? 0.0 : value.x,
    value.y == 0.0 ? 0.0 : value.y,
    value.z == 0.0 ? 0.0 : value.z};
  VertexBits result {};
  for (std::size_t axis = 0; axis < 3; ++axis)
    std::memcpy(&result[axis], &values[axis], sizeof(double));
  return result;
}

BoundingBox triangle_box(const FacetTriangle& triangle)
{
  const Vec3 lower {
    std::min({triangle.a.x, triangle.b.x, triangle.c.x}),
    std::min({triangle.a.y, triangle.b.y, triangle.c.y}),
    std::min({triangle.a.z, triangle.b.z, triangle.c.z})};
  const Vec3 upper {
    std::max({triangle.a.x, triangle.b.x, triangle.c.x}),
    std::max({triangle.a.y, triangle.b.y, triangle.c.y}),
    std::max({triangle.a.z, triangle.b.z, triangle.c.z})};
  const double inf = std::numeric_limits<double>::infinity();
  return {{std::nextafter(lower.x, -inf), std::nextafter(lower.y, -inf),
           std::nextafter(lower.z, -inf)},
          {std::nextafter(upper.x, inf), std::nextafter(upper.y, inf),
           std::nextafter(upper.z, inf)}};
}

BoundingBox empty_box()
{
  const double inf = std::numeric_limits<double>::infinity();
  return {{inf, inf, inf}, {-inf, -inf, -inf}};
}

void extend(BoundingBox& target, const BoundingBox& source)
{
  target.lower.x = std::min(target.lower.x, source.lower.x);
  target.lower.y = std::min(target.lower.y, source.lower.y);
  target.lower.z = std::min(target.lower.z, source.lower.z);
  target.upper.x = std::max(target.upper.x, source.upper.x);
  target.upper.y = std::max(target.upper.y, source.upper.y);
  target.upper.z = std::max(target.upper.z, source.upper.z);
}

double component(const Vec3& value, int axis)
{
  return axis == 0 ? value.x : axis == 1 ? value.y : value.z;
}

} // namespace

CompiledFacetSurfaceSet::CompiledFacetSurfaceSet(
  std::vector<FacetTriangle> triangles)
  : triangles_ {std::move(triangles)}
{
  if (triangles_.empty()
      || triangles_.size() > std::numeric_limits<std::uint32_t>::max()) {
    throw std::invalid_argument("Facet set requires a finite nonempty triangle count");
  }
  std::map<std::pair<int, EdgeBits>, EdgeAudit> edges;
  triangle_boxes_.reserve(triangles_.size());
  for (const auto& triangle : triangles_) {
    if (!finite(triangle.a) || !finite(triangle.b) || !finite(triangle.c)) {
      throw std::invalid_argument("Facet vertices must be finite");
    }
    const LongVec e1 = as_long(triangle.b) - as_long(triangle.a);
    const LongVec e2 = as_long(triangle.c) - as_long(triangle.a);
    const long double area2 = length_long(cross_long(e1, e2));
    if (!(area2 > 0.0L) || !std::isfinite(area2)) {
      throw std::invalid_argument("Facet triangle has zero or nonfinite area");
    }
    const std::array<VertexBits, 3> vertices {
      bits(triangle.a), bits(triangle.b), bits(triangle.c)};
    for (int edge = 0; edge < 3; ++edge) {
      const auto& left = vertices[static_cast<std::size_t>(edge)];
      const auto& right = vertices[static_cast<std::size_t>((edge + 1) % 3)];
      if (left == right)
        throw std::invalid_argument("Facet triangle has a repeated vertex");
      const bool forward = left < right;
      auto& audit = edges[{triangle.component_id,
        forward ? EdgeBits {left, right} : EdgeBits {right, left}}];
      ++audit.count;
      audit.orientation += forward ? 1 : -1;
    }
    triangle_boxes_.push_back(triangle_box(triangle));
  }
  for (const auto& item : edges) {
    if (item.second.count != 2 || item.second.orientation != 0) {
      throw std::invalid_argument(
        "Each facet component must have a closed consistently oriented edge set");
    }
  }
  indices_.resize(triangles_.size());
  std::iota(indices_.begin(), indices_.end(), 0U);
  nodes_.reserve(2 * triangles_.size());
  (void) build_node(0U, static_cast<std::uint32_t>(triangles_.size()));
  bounds_ = nodes_.front().bbox;
}

std::uint32_t CompiledFacetSurfaceSet::build_node(
  std::uint32_t first, std::uint32_t last)
{
  const auto index = static_cast<std::uint32_t>(nodes_.size());
  nodes_.push_back({});
  BoundingBox box = empty_box();
  BoundingBox center_box = empty_box();
  for (std::uint32_t i = first; i < last; ++i) {
    const auto& triangle = triangle_boxes_[indices_[i]];
    extend(box, triangle);
    const Vec3 center = 0.5 * (triangle.lower + triangle.upper);
    extend(center_box, {center, center});
  }
  nodes_[index].bbox = box;
  const auto count = last - first;
  if (count <= 4) {
    nodes_[index].first = first;
    nodes_[index].count = static_cast<std::uint16_t>(count);
    return index;
  }
  const Vec3 extent = center_box.upper - center_box.lower;
  const int axis = extent.y > extent.x
    ? (extent.z > extent.y ? 2 : 1)
    : (extent.z > extent.x ? 2 : 0);
  const auto middle = first + count/2;
  std::nth_element(indices_.begin() + first, indices_.begin() + middle,
    indices_.begin() + last, [&](std::uint32_t lhs, std::uint32_t rhs) {
      const auto& a = triangle_boxes_[lhs];
      const auto& b = triangle_boxes_[rhs];
      return component(a.lower + a.upper, axis)
             < component(b.lower + b.upper, axis);
    });
  nodes_[index].left = build_node(first, middle);
  nodes_[index].right = build_node(middle, last);
  return index;
}

CompiledFacetSurfaceSet::TriangleRayResult
CompiledFacetSurfaceSet::intersect_triangle(
  std::size_t index, const Vec3& origin, const Vec3& direction) const
{
  const auto& triangle = triangles_[index];
  const LongVec e1 = as_long(triangle.b) - as_long(triangle.a);
  const LongVec e2 = as_long(triangle.c) - as_long(triangle.a);
  const LongVec d = as_long(direction);
  const LongVec delta = as_long(origin) - as_long(triangle.a);
  const LongVec h = cross_long(d, e2);
  const long double determinant = dot_long(e1, h);
  const long double scale = length_long(e1) * length_long(e2)
                            * length_long(d);
  const long double eps = 256.0L
    * std::numeric_limits<long double>::epsilon();
  if (!std::isfinite(determinant) || !std::isfinite(scale))
    return {false, true, std::numeric_limits<double>::infinity()};
  if (std::abs(determinant) <= eps * scale) {
    const LongVec geometric_normal = cross_long(e1, e2);
    const long double plane_gap = dot_long(geometric_normal, delta);
    const long double plane_scale = length_long(geometric_normal)
      * (length_long(delta) + 1.0L);
    return {false, std::abs(plane_gap) <= eps * plane_scale,
      std::numeric_limits<double>::infinity()};
  }
  const long double reciprocal = 1.0L / determinant;
  const long double u = reciprocal * dot_long(delta, h);
  const LongVec q = cross_long(delta, e1);
  const long double v = reciprocal * dot_long(d, q);
  const long double w = 1.0L - u - v;
  const long double t = reciprocal * dot_long(e2, q);
  constexpr long double bary_tolerance = 1.0e-14L;
  constexpr long double t_tolerance = 1.0e-12L;
  if (!std::isfinite(u) || !std::isfinite(v) || !std::isfinite(t))
    return {false, true, std::numeric_limits<double>::infinity()};
  if (u < -bary_tolerance || v < -bary_tolerance
      || w < -bary_tolerance || t < -t_tolerance)
    return {};
  if (u <= bary_tolerance || v <= bary_tolerance
      || w <= bary_tolerance || t <= t_tolerance)
    return {false, true, static_cast<double>(t)};
  const double result = static_cast<double>(t);
  if (!(result > 0.0) || !std::isfinite(result))
    return {false, true, result};
  return {true, false, result};
}

FacetDistanceResult CompiledFacetSurfaceSet::distance(
  const Vec3& origin, const Vec3& direction) const
{
  const double direction_length = norm(direction);
  if (!finite(origin) || !finite(direction)
      || !(direction_length > 0.0) || !std::isfinite(direction_length)) {
    throw std::invalid_argument("Facet ray must have finite origin and nonzero direction");
  }
  const Vec3 unit_direction = normalized(direction);
  FacetDistanceResult best;
  double earliest_ambiguity = std::numeric_limits<double>::infinity();
  std::vector<std::uint32_t> stack {0U};
  while (!stack.empty()) {
    const auto node_index = stack.back();
    stack.pop_back();
    const auto& node = nodes_[node_index];
    const auto interval = node.bbox.ray_interval(origin, unit_direction);
    if (!interval || interval->exit <= 0.0
        || interval->enter > best.distance) continue;
    if (node.leaf()) {
      for (std::uint32_t i = 0; i < node.count; ++i) {
        const auto triangle_index = indices_[node.first + i];
        const auto local = triangle_boxes_[triangle_index].ray_interval(
          origin, unit_direction);
        if (!local || local->exit <= 0.0 || local->enter > best.distance)
          continue;
        const auto hit = intersect_triangle(triangle_index, origin, unit_direction);
        if (hit.ambiguous) {
          earliest_ambiguity = std::min(earliest_ambiguity,
            std::max(0.0, local->enter));
        } else if (hit.hit && hit.t < best.distance) {
          const auto& triangle = triangles_[triangle_index];
          best.found = true;
          best.distance = hit.t;
          best.triangle_index = triangle_index;
          best.component_id = triangle.component_id;
          const LongVec geometric_normal = cross_long(
            as_long(triangle.b) - as_long(triangle.a),
            as_long(triangle.c) - as_long(triangle.a));
          const long double magnitude = length_long(geometric_normal);
          best.outward_normal = {
            static_cast<double>(geometric_normal.x / magnitude),
            static_cast<double>(geometric_normal.y / magnitude),
            static_cast<double>(geometric_normal.z / magnitude)};
        }
      }
    } else {
      stack.push_back(node.left);
      stack.push_back(node.right);
    }
  }
  best.terminal_unresolved = std::isfinite(earliest_ambiguity)
    && (!best.found || earliest_ambiguity <= best.distance);
  return best;
}

std::optional<bool> CompiledFacetSurfaceSet::parity_ray(
  const Vec3& point, const Vec3& direction) const
{
  std::vector<std::uint32_t> stack {0U};
  std::size_t hit_count = 0;
  while (!stack.empty()) {
    const auto node_index = stack.back();
    stack.pop_back();
    const auto& node = nodes_[node_index];
    const auto interval = node.bbox.ray_interval(point, direction);
    if (!interval || interval->exit <= 0.0) continue;
    if (node.leaf()) {
      for (std::uint32_t i = 0; i < node.count; ++i) {
        const auto triangle_index = indices_[node.first + i];
        const auto local = triangle_boxes_[triangle_index].ray_interval(
          point, direction);
        if (!local || local->exit <= 0.0) continue;
        const auto result = intersect_triangle(triangle_index, point, direction);
        if (result.ambiguous) return std::nullopt;
        if (result.hit) ++hit_count;
      }
    } else {
      stack.push_back(node.left);
      stack.push_back(node.right);
    }
  }
  return (hit_count % 2) == 1;
}

std::optional<bool> CompiledFacetSurfaceSet::contains(const Vec3& point) const
{
  if (!finite(point))
    throw std::invalid_argument("Facet query point must be finite");
  const std::array<Vec3, 3> directions {
    normalized({0.573, 0.711, 0.404}),
    normalized({0.797, -0.363, 0.483}),
    normalized({-0.299, 0.821, 0.486})};
  const auto first = parity_ray(point, directions[0]);
  if (!first) return std::nullopt;
  for (std::size_t index = 1; index < directions.size(); ++index) {
    const auto other = parity_ray(point, directions[index]);
    if (!other || *other != *first) return std::nullopt;
  }
  return first;
}

} // namespace stellarcsg
