#ifndef STELLARCSG_COMPILED_SWEPT_SURFACE_HPP
#define STELLARCSG_COMPILED_SWEPT_SURFACE_HPP

#include "stellarcsg/compiled_periodic_surface.hpp"
#include "stellarcsg/uniform_periodic_cubic_spline.hpp"
#include "stellarcsg/vector.hpp"

#include <cstddef>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace stellarcsg {

struct SweptSplineSurfaceData {
  int coil_id {0};
  std::string content_id {};
  std::string canonical_metadata_json {};
  std::size_t sample_count {0};
  std::vector<double> centerline_coefficients {};
  std::vector<double> normal_coefficients {};
  std::vector<double> binormal_coefficients {};
  std::vector<double> major_radius_coefficients {};
  std::vector<double> minor_radius_coefficients {};
  double length {0.0};
  double characteristic_length {1.0};
};

struct SweptLocalCoordinates {
  int coil_id {0};
  double arc_coordinate {0.0};
  double u {0.0};
  double v {0.0};
  Vec3 center {};
  Vec3 tangent {};
  Vec3 normal {};
  Vec3 binormal {};
  double major_radius {0.0};
  double minor_radius {0.0};
};

struct SweptSpan {
  double angle_min {0.0};
  double angle_max {0.0};
  BoundingBox centerline_bbox {};
  BoundingBox conservative_bbox {};
  Vec3 proxy_start {};
  Vec3 proxy_end {};
  double radius_bound {0.0};
  double proxy_radius {0.0};
  // Four local monomial coefficients for center x/y/z, supplied normal
  // x/y/z, major radius, and minor radius.
  std::array<double, 32> power {};
};

struct SweptSpanBVHNode {
  BoundingBox centerline_bbox {};
  BoundingBox bbox {};
  std::uint32_t left {0};
  std::uint32_t right {0};
  std::uint32_t first {0};
  std::uint16_t count {0};
  [[nodiscard]] bool leaf() const noexcept { return count != 0; }
};

class CompiledSweptSplineSurface {
public:
  explicit CompiledSweptSplineSurface(
    SweptSplineSurfaceData data, bool force_general_solver = false);

  [[nodiscard]] SweptLocalCoordinates local_coordinates(const Vec3& point) const;
  [[nodiscard]] double evaluate(const Vec3& point) const;
  [[nodiscard]] Vec3 normal(const Vec3& point) const;
  [[nodiscard]] DistanceResult distance_reference(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;
  [[nodiscard]] DistanceResult distance(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;
  [[nodiscard]] const BoundingBox& bounding_box() const noexcept { return bounds_; }
  [[nodiscard]] bool exact_torus_specialization() const noexcept
  {
    return static_cast<bool>(exact_torus_);
  }
  [[nodiscard]] ExactCircularTorusParameters exact_circular_torus_parameters()
    const noexcept
  {
    return exact_torus_ ? exact_torus_->exact_circular_torus_parameters()
                        : ExactCircularTorusParameters {};
  }
  [[nodiscard]] const std::vector<SweptSpan>& spans() const noexcept
  {
    return spans_;
  }
  [[nodiscard]] const std::vector<SweptSpanBVHNode>& span_bvh() const noexcept
  {
    return span_bvh_;
  }

private:
  SweptSplineSurfaceData data_;
  UniformPeriodicCubicSpline center_x_;
  UniformPeriodicCubicSpline center_y_;
  UniformPeriodicCubicSpline center_z_;
  UniformPeriodicCubicSpline normal_x_;
  UniformPeriodicCubicSpline normal_y_;
  UniformPeriodicCubicSpline normal_z_;
  UniformPeriodicCubicSpline binormal_x_;
  UniformPeriodicCubicSpline binormal_y_;
  UniformPeriodicCubicSpline binormal_z_;
  UniformPeriodicCubicSpline major_radius_;
  UniformPeriodicCubicSpline minor_radius_;
  BoundingBox bounds_;
  std::unique_ptr<CompiledPeriodicSplineSurface> exact_torus_;
  std::vector<SweptSpan> spans_ {};
  std::vector<std::uint32_t> span_indices_ {};
  std::vector<SweptSpanBVHNode> span_bvh_ {};
  std::uint64_t instance_id_ {0};
  bool circular_cross_section_ {false};
  double circular_radius_ {0.0};

  [[nodiscard]] SweptLocalCoordinates frame(double angle) const;
  [[nodiscard]] SweptLocalCoordinates frame_in_span(
    const SweptSpan& span, double angle) const;
  [[nodiscard]] double squared_distance(const Vec3& point, double angle) const;
  [[nodiscard]] Vec3 surface_point(
    const SweptSpan& span, double angle, double alpha) const;
  void center_derivatives(const SweptSpan& span, double angle,
    Vec3& center, Vec3& first, Vec3& second) const;
  void surface_derivatives(const SweptSpan& span, double angle, double alpha,
    Vec3& position, Vec3& dangle, Vec3& dalpha) const;
  [[nodiscard]] double evaluate_in_span(
    const Vec3& point, const SweptSpan& span, double* angle = nullptr) const;
  void build_spans();
  [[nodiscard]] std::uint32_t build_span_bvh_node(
    std::uint32_t first, std::uint32_t last);
};

} // namespace stellarcsg

#endif
