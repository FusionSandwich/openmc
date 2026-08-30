#ifndef STELLARCSG_PERIODIC_RADIAL_SURFACE_HPP
#define STELLARCSG_PERIODIC_RADIAL_SURFACE_HPP

#include "stellarcsg/root_solver.hpp"
#include "stellarcsg/vector.hpp"

#include <atomic>
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

// Options for the production-oriented bounded-work ray search. The algorithm
// scans the finite surface AABB in increasing t, refines the first detected
// sign-changing or tangent bracket using safeguarded Newton iterations, and
// can fall back to the independent reference search when the fast scan is
// inconclusive. The fallback is intentionally visible in diagnostics.
struct FastDistanceOptions {
  int minimum_scan_intervals {16};
  int maximum_scan_intervals {256};
  int maximum_hybrid_iterations {40};
  int maximum_stationary_iterations {48};
  double maximum_scan_step_fraction {0.40};
  double absolute_t_tolerance {1.0e-11};
  double relative_t_tolerance {1.0e-11};
  double absolute_f_tolerance {1.0e-10};
  double derivative_tolerance {1.0e-12};
  double tangent_residual_multiplier {24.0};
  bool fallback_to_reference {true};
  RootSearchOptions fallback_options {};
};

struct SurfaceDiagnostics {
  long evaluate_calls {0};
  long gradient_calls {0};
  long distance_calls {0};
  long fast_distance_calls {0};
  long reference_distance_calls {0};
  long fast_fallbacks {0};
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
  bool used_fallback {false};
  int scan_intervals {0};
  int hybrid_iterations {0};
};

class PeriodicRadialSurface {
public:
  PeriodicRadialSurface(AxisField axis, RadiusField radius,
    BoundingBox conservative_bounds, double characteristic_length,
    double coordinate_singularity_tolerance = 1.0e-13,
    double minimum_feature_length = 0.0);

  [[nodiscard]] LocalCoordinates local_coordinates(const Vec3& point) const;
  [[nodiscard]] double evaluate(const Vec3& point) const;
  [[nodiscard]] Vec3 gradient(const Vec3& point) const;
  [[nodiscard]] Vec3 normal(const Vec3& point) const;
  [[nodiscard]] double directional_derivative(
    const Vec3& point, const Vec3& direction) const;

  [[nodiscard]] DistanceResult distance_reference(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;

  [[nodiscard]] DistanceResult distance_fast(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const FastDistanceOptions& options = {}) const;

  [[nodiscard]] const BoundingBox& bounding_box() const noexcept
  {
    return conservative_bounds_;
  }

  [[nodiscard]] double minimum_feature_length() const noexcept
  {
    return minimum_feature_length_;
  }

  [[nodiscard]] SurfaceDiagnostics diagnostics() const noexcept;
  void reset_diagnostics() const noexcept;

private:
  AxisField axis_;
  RadiusField radius_;
  BoundingBox conservative_bounds_;
  double characteristic_length_;
  double coordinate_singularity_tolerance_;
  double minimum_feature_length_;

  struct AtomicDiagnostics {
    std::atomic<long> evaluate_calls {0};
    std::atomic<long> gradient_calls {0};
    std::atomic<long> distance_calls {0};
    std::atomic<long> fast_distance_calls {0};
    std::atomic<long> reference_distance_calls {0};
    std::atomic<long> fast_fallbacks {0};
    std::atomic<long> finite_difference_directional_derivatives {0};
    std::atomic<long> root_function_evaluations {0};
    std::atomic<long> root_derivative_evaluations {0};
  };
  mutable AtomicDiagnostics diagnostics_ {};
};

[[nodiscard]] AxisField circular_axis(double major_radius, double z_offset = 0.0);
[[nodiscard]] RadiusField constant_radius(double minor_radius);

} // namespace stellarcsg

#endif
