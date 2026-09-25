#ifndef STELLARCSG_COMPILED_FACET_SURFACE_SET_HPP
#define STELLARCSG_COMPILED_FACET_SURFACE_SET_HPP

#include "stellarcsg/vector.hpp"

#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <vector>

namespace stellarcsg {

struct FacetTriangle {
  Vec3 a {};
  Vec3 b {};
  Vec3 c {};
  int component_id {0};
};

struct FacetDistanceResult {
  bool found {false};
  double distance {std::numeric_limits<double>::infinity()};
  std::size_t triangle_index {0};
  int component_id {-1};
  Vec3 outward_normal {};
  bool terminal_unresolved {false};
};

// A fail-closed ray-query reference for closed, oriented triangle components.
// It represents the supplied facets, not an inferred continuous CAD surface.
class CompiledFacetSurfaceSet {
public:
  explicit CompiledFacetSurfaceSet(std::vector<FacetTriangle> triangles);

  // Returns physical distance in the same units as the vertices, for any
  // finite nonzero direction. Ambiguous earlier contacts set terminal_unresolved.
  [[nodiscard]] FacetDistanceResult distance(const Vec3& origin,
    const Vec3& direction) const;
  // nullopt means at least one probe ray is geometrically ambiguous.
  [[nodiscard]] std::optional<bool> contains(const Vec3& point) const;
  [[nodiscard]] const BoundingBox& bounding_box() const noexcept
  {
    return bounds_;
  }
  [[nodiscard]] std::size_t triangle_count() const noexcept
  {
    return triangles_.size();
  }

private:
  struct Node {
    BoundingBox bbox {};
    std::uint32_t left {0};
    std::uint32_t right {0};
    std::uint32_t first {0};
    std::uint16_t count {0};
    [[nodiscard]] bool leaf() const noexcept { return count != 0; }
  };
  struct TriangleRayResult {
    bool hit {false};
    bool ambiguous {false};
    double t {std::numeric_limits<double>::infinity()};
  };

  std::vector<FacetTriangle> triangles_ {};
  std::vector<BoundingBox> triangle_boxes_ {};
  std::vector<std::uint32_t> indices_ {};
  std::vector<Node> nodes_ {};
  BoundingBox bounds_ {};

  [[nodiscard]] std::uint32_t build_node(
    std::uint32_t first, std::uint32_t last);
  [[nodiscard]] TriangleRayResult intersect_triangle(
    std::size_t index, const Vec3& origin, const Vec3& direction) const;
  [[nodiscard]] std::optional<bool> parity_ray(
    const Vec3& point, const Vec3& direction) const;
};

} // namespace stellarcsg

#endif
