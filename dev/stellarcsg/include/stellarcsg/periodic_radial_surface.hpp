#ifndef STELLARCSG_PERIODIC_RADIAL_SURFACE_HPP
#define STELLARCSG_PERIODIC_RADIAL_SURFACE_HPP

#include "stellarcsg/root_solver.hpp"
#include "stellarcsg/vector.hpp"

#include <functional>
#include <limits>

namespace stellarcsg {

struct AxisSample {
  double R {0.0};
  double Z {0.0};
  double dR_dphi {0.0};
  double dZ_dphi {0.0};
};

struct RadiusSample {
  double value {0.0};
  double dtheta {0.0};
  double dphi {0.0};
};

using AxisField = std::function<AxisSample(double phi)>;
using RadiusField = std::function<RadiusSample(double theta, double phi)>;

struct LocalCoordinates {
  double R {0.0};
  double phi {0.0};
  double q_R {0.0};
  double q_Z {0.0};
  double rho {0.0};
  double theta {0.0};
  AxisSample axis {};
  RadiusSample surface_radius {};
};

struct SurfaceDiagnostics {
  long evaluate_calls {0};
  long gradient_calls {0};
  long distance_calls {0};
  long finite_difference_directional_derivatives {0};
  long root_function_evaluations {0};
  long root_derivative_evaluations {0};
};

struct DistanceResult {
  bool found {false};
  double distance {std::numeric_limits<double>::infinity()};
  RootKind kind {RootKind::sign_change};
  double residual {std::numeric_limits<double>::infinity()};
  RootSearchDiagnostics root_diagnostics {};
};

class PeriodicRadialSurface {
public:
  PeriodicRadialSurface(AxisField axis, RadiusField radius,
    BoundingBox conservative_bounds, double characteristic_length,
    double coordinate_singularity_tolerance = 1.0e-13);

  [[nodiscard]] LocalCoordinates local_coordinates(const Vec3& point) const;
  [[nodiscard]] double evaluate(const Vec3& point) const;
  [[nodiscard]] Vec3 gradient(const Vec3& point) const;
  [[nodiscard]] Vec3 normal(const Vec3& point) const;
  [[nodiscard]] double directional_derivative(
    const Vec3& point, const Vec3& direction) const;

  [[nodiscard]] DistanceResult distance_reference(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;

  [[nodiscard]] const BoundingBox& bounding_box() const noexcept
  {
    return conservative_bounds_;
  }

  [[nodiscard]] SurfaceDiagnostics diagnostics() const noexcept
  {
    return diagnostics_;
  }

  void reset_diagnostics() const noexcept { diagnostics_ = {}; }

private:
  AxisField axis_;
  RadiusField radius_;
  BoundingBox conservative_bounds_;
  double characteristic_length_;
  double coordinate_singularity_tolerance_;
  mutable SurfaceDiagnostics diagnostics_ {};
};

[[nodiscard]] AxisField circular_axis(double major_radius, double z_offset = 0.0);
[[nodiscard]] RadiusField constant_radius(double minor_radius);

} // namespace stellarcsg

#endif
