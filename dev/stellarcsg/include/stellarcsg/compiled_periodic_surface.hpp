#ifndef STELLARCSG_COMPILED_PERIODIC_SURFACE_HPP
#define STELLARCSG_COMPILED_PERIODIC_SURFACE_HPP

#include "stellarcsg/periodic_radial_surface.hpp"
#include "stellarcsg/uniform_periodic_bicubic_spline.hpp"
#include "stellarcsg/uniform_periodic_cubic_spline.hpp"

#include <cstddef>
#include <string>
#include <vector>

namespace stellarcsg {

// Frozen, device-independent coefficient payload. Values are in centimetres
// and angles are in radians. The first production schema is deliberately small
// enough to review and replay locally.
struct PeriodicSplineSurfaceData {
  int schema_major {1};
  int schema_minor {0};
  std::string content_id {};
  std::string units {"cm"};
  int n_field_periods {1};
  std::vector<double> axis_r_coefficients {};
  std::vector<double> axis_z_coefficients {};
  std::size_t n_theta {0};
  std::size_t n_phi {0};
  std::vector<double> radius_coefficients {};
  double characteristic_length {1.0};
  double coordinate_singularity_tolerance {1.0e-12};
};

// Compiles coefficient arrays into allocation-free spline evaluations. The
// current nearest-root implementation remains the conservative reference
// search from PeriodicRadialSurface and is not yet the final fast transport
// algorithm.
class CompiledPeriodicSplineSurface {
public:
  explicit CompiledPeriodicSplineSurface(PeriodicSplineSurfaceData data);

  [[nodiscard]] double evaluate(const Vec3& point) const;
  [[nodiscard]] Vec3 gradient(const Vec3& point) const;
  [[nodiscard]] Vec3 normal(const Vec3& point) const;
  [[nodiscard]] DistanceResult distance_reference(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;
  [[nodiscard]] DistanceResult distance_fast(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const FastDistanceOptions& options = {}) const;

  [[nodiscard]] const BoundingBox& bounding_box() const noexcept
  {
    return surface_.bounding_box();
  }
  [[nodiscard]] const PeriodicSplineSurfaceData& data() const noexcept
  {
    return data_;
  }

private:
  PeriodicSplineSurfaceData data_;
  UniformPeriodicCubicSpline axis_r_;
  UniformPeriodicCubicSpline axis_z_;
  UniformPeriodicBicubicSpline radius_;
  PeriodicRadialSurface surface_;

  [[nodiscard]] static BoundingBox conservative_bounds(
    const PeriodicSplineSurfaceData& data);
};

} // namespace stellarcsg

#endif
