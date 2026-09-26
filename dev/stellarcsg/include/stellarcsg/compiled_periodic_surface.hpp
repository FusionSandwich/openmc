#ifndef STELLARCSG_COMPILED_PERIODIC_SURFACE_HPP
#define STELLARCSG_COMPILED_PERIODIC_SURFACE_HPP

#include "stellarcsg/periodic_radial_surface.hpp"
#include "stellarcsg/uniform_periodic_bicubic_spline.hpp"
#include "stellarcsg/uniform_periodic_cubic_spline.hpp"

#include <cstddef>
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace stellarcsg {

enum class PeriodicSurfaceSpecialization {
  exact_circular_torus,
  shaped_axisymmetric,
  general_periodic,
};

struct ParametricSurfaceSample {
  Vec3 position {};
  Vec3 dtheta {};
  Vec3 dphi {};
};

struct ParametricBounds {
  double theta_min {0.0};
  double theta_max {0.0};
  double phi_min {0.0};
  double phi_max {0.0};
};

struct PeriodicPatch {
  ParametricBounds uv {};
  BoundingBox conservative_bbox {};
  BoundingBox proxy_bbox {};
  std::array<Vec3, 4> proxy_corners {};
  // Tensor-product power coefficients for this one-cell bicubic patch.
  // radius_power[4 * theta_power + phi_power].
  std::array<double, 16> radius_power {};
  double proxy_error_bound {0.0};
  std::array<std::int32_t, 4> neighbors {{-1, -1, -1, -1}};
};

struct PeriodicPatchBVHNode {
  BoundingBox bbox {};
  std::uint32_t left {0};
  std::uint32_t right {0};
  std::uint32_t first {0};
  std::uint16_t count {0};

  [[nodiscard]] bool leaf() const noexcept { return count != 0; }
};

// Frozen, device-independent coefficient payload. Values are in centimetres
// and angles are in radians. The first production schema is deliberately small
// enough to review and replay locally.
struct PeriodicSplineSurfaceData {
  int schema_major {1};
  int schema_minor {0};
  std::string content_id {};
  std::string canonical_metadata_json {};
  std::string units {"cm"};
  int n_field_periods {1};
  std::vector<double> axis_r_coefficients {};
  std::vector<double> axis_z_coefficients {};
  std::size_t n_theta {0};
  std::size_t n_phi {0};
  std::vector<double> radius_coefficients {};
  double characteristic_length {1.0};
  double coordinate_singularity_tolerance {1.0e-12};
  bool force_general_solver {false};
};

// Compiles coefficient arrays into allocation-free spline evaluations. General
// periodic surfaces use conservative parametric patches, a flattened BVH, and
// local safeguarded correction. The broad interval solver is retained only as
// an explicit offline correctness oracle/negative precursor.
class CompiledPeriodicSplineSurface {
public:
  explicit CompiledPeriodicSplineSurface(PeriodicSplineSurfaceData data);

  [[nodiscard]] double evaluate(const Vec3& point) const;
  [[nodiscard]] Vec3 gradient(const Vec3& point) const;
  [[nodiscard]] Vec3 normal(const Vec3& point) const;
  [[nodiscard]] DistanceResult distance_reference(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;
  [[nodiscard]] DistanceResult distance(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;

  [[nodiscard]] PeriodicSurfaceSpecialization specialization() const noexcept
  {
    return specialization_;
  }

  [[nodiscard]] const BoundingBox& bounding_box() const noexcept
  {
    return surface_.bounding_box();
  }
  [[nodiscard]] const PeriodicSplineSurfaceData& data() const noexcept
  {
    return data_;
  }
  [[nodiscard]] const std::vector<PeriodicPatch>& patches() const noexcept
  {
    return patches_;
  }
  [[nodiscard]] const std::vector<PeriodicPatchBVHNode>& patch_bvh() const noexcept
  {
    return patch_bvh_;
  }
  [[nodiscard]] ParametricSurfaceSample sample_parametric(
    double theta, double phi) const;

private:
  PeriodicSplineSurfaceData data_;
  UniformPeriodicCubicSpline axis_r_;
  UniformPeriodicCubicSpline axis_z_;
  UniformPeriodicBicubicSpline radius_;
  PeriodicRadialSurface surface_;
  PeriodicSurfaceSpecialization specialization_ {
    PeriodicSurfaceSpecialization::general_periodic};
  double torus_major_radius_ {0.0};
  double torus_minor_radius_ {0.0};
  double torus_z_offset_ {0.0};
  double axisymmetric_radius_derivative_bound_ {0.0};
  double axis_derivative_bound_ {0.0};
  double radius_theta_derivative_bound_ {0.0};
  double radius_phi_derivative_bound_ {0.0};
  double radius_coefficient_min_ {0.0};
  double radius_coefficient_max_ {0.0};
  std::vector<double> axis_local_derivative_bounds_ {};
  std::vector<double> radius_local_theta_derivative_bounds_ {};
  std::vector<double> radius_local_phi_derivative_bounds_ {};
  bool axis_patch_aligned_ {false};
  std::vector<std::array<double, 8>> axis_patch_power_ {};
  std::vector<PeriodicPatch> patches_ {};
  std::vector<std::uint32_t> patch_indices_ {};
  std::vector<PeriodicPatchBVHNode> patch_bvh_ {};

  [[nodiscard]] static BoundingBox conservative_bounds(
    const PeriodicSplineSurfaceData& data);
  [[nodiscard]] DistanceResult distance_exact_torus(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options) const;
  [[nodiscard]] DistanceResult distance_shaped_axisymmetric(
    const Vec3& origin, const Vec3& direction, bool coincident,
    const RootSearchOptions& options) const;
  [[nodiscard]] DistanceResult distance_general_periodic(
    const Vec3& origin, const Vec3& direction, bool coincident,
    const RootSearchOptions& options) const;
  [[nodiscard]] DistanceResult distance_general_periodic_interval_precursor(
    const Vec3& origin, const Vec3& direction, bool coincident,
    const RootSearchOptions& options) const;
  [[nodiscard]] ParametricSurfaceSample sample_patch_parametric(
    const PeriodicPatch& patch, double theta, double phi) const;
  void build_periodic_patches();
  [[nodiscard]] std::uint32_t build_patch_bvh_node(
    std::uint32_t first, std::uint32_t last);
};

} // namespace stellarcsg

#endif
