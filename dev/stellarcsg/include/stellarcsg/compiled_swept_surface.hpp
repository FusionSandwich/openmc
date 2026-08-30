#ifndef STELLARCSG_COMPILED_SWEPT_SURFACE_HPP
#define STELLARCSG_COMPILED_SWEPT_SURFACE_HPP

#include "stellarcsg/compiled_periodic_surface.hpp"
#include "stellarcsg/uniform_periodic_cubic_spline.hpp"
#include "stellarcsg/vector.hpp"

#include <cstddef>
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

class CompiledSweptSplineSurface {
public:
  explicit CompiledSweptSplineSurface(SweptSplineSurfaceData data);

  [[nodiscard]] SweptLocalCoordinates local_coordinates(const Vec3& point) const;
  [[nodiscard]] double evaluate(const Vec3& point) const;
  [[nodiscard]] Vec3 normal(const Vec3& point) const;
  [[nodiscard]] DistanceResult distance_reference(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;
  [[nodiscard]] const BoundingBox& bounding_box() const noexcept { return bounds_; }
  [[nodiscard]] bool exact_torus_specialization() const noexcept
  {
    return static_cast<bool>(exact_torus_);
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

  [[nodiscard]] SweptLocalCoordinates frame(double angle) const;
  [[nodiscard]] double squared_distance(const Vec3& point, double angle) const;
};

} // namespace stellarcsg

#endif
