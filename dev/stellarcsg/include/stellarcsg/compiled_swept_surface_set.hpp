#ifndef STELLARCSG_COMPILED_SWEPT_SURFACE_SET_HPP
#define STELLARCSG_COMPILED_SWEPT_SURFACE_SET_HPP

#include "stellarcsg/compiled_swept_surface.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

namespace stellarcsg {

struct SweptCoilBVHNode {
  BoundingBox bbox {};
  std::uint32_t left {0};
  std::uint32_t right {0};
  std::uint32_t first {0};
  std::uint16_t count {0};
  [[nodiscard]] bool leaf() const noexcept { return count != 0; }
};

struct SweptCoilSetDistanceResult {
  DistanceResult root {};
  int coil_id {-1};
  std::size_t coil_index {0};
};

class CompiledSweptSplineSurfaceSet {
public:
  explicit CompiledSweptSplineSurfaceSet(
    std::vector<SweptSplineSurfaceData> coils);

  [[nodiscard]] double evaluate(const Vec3& point) const;
  [[nodiscard]] Vec3 normal(const Vec3& point) const;
  [[nodiscard]] SweptCoilSetDistanceResult distance(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;
  [[nodiscard]] const BoundingBox& bounding_box() const noexcept
  {
    return bounds_;
  }
  [[nodiscard]] std::size_t size() const noexcept { return coils_.size(); }
  [[nodiscard]] const std::vector<SweptCoilBVHNode>& coil_bvh() const noexcept
  {
    return bvh_;
  }

private:
  std::vector<std::unique_ptr<CompiledSweptSplineSurface>> coils_ {};
  std::vector<int> coil_ids_ {};
  std::vector<std::uint32_t> indices_ {};
  std::vector<SweptCoilBVHNode> bvh_ {};
  BoundingBox bounds_ {};

  [[nodiscard]] std::uint32_t build_node(
    std::uint32_t first, std::uint32_t last);
};

} // namespace stellarcsg

#endif
