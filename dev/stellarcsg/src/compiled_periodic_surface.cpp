#include "stellarcsg/compiled_periodic_surface.hpp"

#include <algorithm>
#include <cmath>
#include <complex>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <utility>

namespace oqs {
void quartic_solver(double coeff[5], std::complex<double> roots[4]);
}

namespace stellarcsg {
namespace {

constexpr double two_pi =
  2.0 * 3.141592653589793238462643383279502884;

AxisField make_axis_field(const UniformPeriodicCubicSpline* r_axis,
  const UniformPeriodicCubicSpline* z_axis)
{
  return [r_axis, z_axis](double phi) {
    const auto r = r_axis->sample(phi);
    const auto z = z_axis->sample(phi);
    return AxisSample {r.value, z.value, r.derivative, z.derivative};
  };
}

RadiusField make_radius_field(const UniformPeriodicBicubicSpline* radius)
{
  return [radius](double theta, double phi) {
    const auto sample = radius->sample(theta, phi);
    return RadiusSample {sample.value, sample.dtheta, sample.dphi};
  };
}

void validate_data(const PeriodicSplineSurfaceData& data)
{
  if (data.schema_major != 1) {
    throw std::invalid_argument("Unsupported periodic-spline schema major version");
  }
  if (data.units != "cm") {
    throw std::invalid_argument("Periodic-spline geometry must be stored in cm");
  }
  if (data.n_field_periods <= 0) {
    throw std::invalid_argument("Field-period count must be positive");
  }
  if (data.axis_r_coefficients.size() < 4
      || data.axis_r_coefficients.size() != data.axis_z_coefficients.size()) {
    throw std::invalid_argument(
      "Axis R and Z coefficient arrays must have equal length >= 4");
  }
  if (data.n_theta < 4 || data.n_phi < 4
      || data.radius_coefficients.size() != data.n_theta * data.n_phi) {
    throw std::invalid_argument("Invalid radial bicubic coefficient dimensions");
  }
  if (!(data.characteristic_length > 0.0)
      || !std::isfinite(data.characteristic_length)) {
    throw std::invalid_argument("Characteristic length must be finite and positive");
  }
  if (!(data.coordinate_singularity_tolerance > 0.0)
      || !std::isfinite(data.coordinate_singularity_tolerance)) {
    throw std::invalid_argument(
      "Coordinate singularity tolerance must be finite and positive");
  }
  for (double radius : data.radius_coefficients) {
    if (!(radius > 0.0) || !std::isfinite(radius)) {
      throw std::invalid_argument(
        "Radial B-spline coefficients must be finite and positive");
    }
  }
}

double mean(const std::vector<double>& values)
{
  return std::accumulate(values.begin(), values.end(), 0.0)
         / static_cast<double>(values.size());
}

bool scale_aware_constant(const std::vector<double>& values, double scale)
{
  const auto bounds = std::minmax_element(values.begin(), values.end());
  const double local_scale = std::max(
    {1.0, scale, std::abs(*bounds.first), std::abs(*bounds.second)});
  const double tolerance = 256.0 * std::numeric_limits<double>::epsilon()
                           * local_scale;
  return *bounds.second - *bounds.first <= tolerance;
}

PeriodicSurfaceSpecialization detect_specialization(
  const PeriodicSplineSurfaceData& data)
{
  if (!scale_aware_constant(
        data.axis_r_coefficients, data.characteristic_length)
      || !scale_aware_constant(
        data.axis_z_coefficients, data.characteristic_length)) {
    return PeriodicSurfaceSpecialization::general_periodic;
  }

  bool axisymmetric = true;
  for (std::size_t i = 0; i < data.n_theta; ++i) {
    const auto first = data.radius_coefficients.begin()
                       + static_cast<std::ptrdiff_t>(i * data.n_phi);
    const std::vector<double> row(first,
      first + static_cast<std::ptrdiff_t>(data.n_phi));
    if (!scale_aware_constant(row, data.characteristic_length)) {
      axisymmetric = false;
      break;
    }
  }
  if (!axisymmetric) {
    return PeriodicSurfaceSpecialization::general_periodic;
  }
  return scale_aware_constant(
           data.radius_coefficients, data.characteristic_length)
           ? PeriodicSurfaceSpecialization::exact_circular_torus
           : PeriodicSurfaceSpecialization::shaped_axisymmetric;
}

} // namespace

BoundingBox CompiledPeriodicSplineSurface::conservative_bounds(
  const PeriodicSplineSurfaceData& data)
{
  const auto r_axis_bounds = std::minmax_element(
    data.axis_r_coefficients.begin(), data.axis_r_coefficients.end());
  const auto z_axis_bounds = std::minmax_element(
    data.axis_z_coefficients.begin(), data.axis_z_coefficients.end());
  const double radius_max = *std::max_element(
    data.radius_coefficients.begin(), data.radius_coefficients.end());
  const double radial_extent = std::max(
    std::abs(*r_axis_bounds.first), std::abs(*r_axis_bounds.second)) + radius_max;
  const double epsilon = std::max(1.0e-10 * data.characteristic_length, 1.0e-9);
  return BoundingBox {
    {-radial_extent - epsilon, -radial_extent - epsilon,
      *z_axis_bounds.first - radius_max - epsilon},
    {radial_extent + epsilon, radial_extent + epsilon,
      *z_axis_bounds.second + radius_max + epsilon}};
}

CompiledPeriodicSplineSurface::CompiledPeriodicSplineSurface(
  PeriodicSplineSurfaceData data)
  : data_ {[&data]() {
      validate_data(data);
      return std::move(data);
    }()}
  , axis_r_ {data_.axis_r_coefficients.size(), data_.n_field_periods,
      data_.axis_r_coefficients}
  , axis_z_ {data_.axis_z_coefficients.size(), data_.n_field_periods,
      data_.axis_z_coefficients}
  , radius_ {data_.n_theta, data_.n_phi, data_.n_field_periods,
      data_.radius_coefficients}
  , surface_ {make_axis_field(&axis_r_, &axis_z_), make_radius_field(&radius_),
      conservative_bounds(data_), data_.characteristic_length,
      data_.coordinate_singularity_tolerance}
{
  specialization_ = detect_specialization(data_);
  if (specialization_ == PeriodicSurfaceSpecialization::exact_circular_torus) {
    torus_major_radius_ = mean(data_.axis_r_coefficients);
    torus_z_offset_ = mean(data_.axis_z_coefficients);
    torus_minor_radius_ = mean(data_.radius_coefficients);
  } else if (specialization_
             == PeriodicSurfaceSpecialization::shaped_axisymmetric) {
    const auto bounds = std::minmax_element(
      data_.radius_coefficients.begin(), data_.radius_coefficients.end());
    axisymmetric_radius_derivative_bound_ =
      2.0 * (*bounds.second - *bounds.first)
      * static_cast<double>(data_.n_theta) / two_pi;
  }
}

double CompiledPeriodicSplineSurface::evaluate(const Vec3& point) const
{
  return surface_.evaluate(point);
}

Vec3 CompiledPeriodicSplineSurface::gradient(const Vec3& point) const
{
  return surface_.gradient(point);
}

Vec3 CompiledPeriodicSplineSurface::normal(const Vec3& point) const
{
  return surface_.normal(point);
}

DistanceResult CompiledPeriodicSplineSurface::distance_reference(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  auto result = surface_.distance_reference(origin, direction, coincident, options);
  result.root_diagnostics.solver_path = SolverPath::global_reference;
  result.root_diagnostics.fallback_reason =
    SolverFallbackReason::reference_requested;
  return result;
}

DistanceResult CompiledPeriodicSplineSurface::distance(const Vec3& origin,
  const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  if (specialization_ == PeriodicSurfaceSpecialization::exact_circular_torus) {
    return distance_exact_torus(origin, direction, coincident, options);
  }
  if (specialization_
      == PeriodicSurfaceSpecialization::shaped_axisymmetric) {
    return distance_shaped_axisymmetric(
      origin, direction, coincident, options);
  }
  auto result = surface_.distance_reference(origin, direction, coincident, options);
  result.root_diagnostics.solver_path = SolverPath::reference_fallback;
  result.root_diagnostics.fallback_reason =
    SolverFallbackReason::general_periodic_surface;
  ++result.root_diagnostics.reference_fallback_calls;
  return result;
}

DistanceResult CompiledPeriodicSplineSurface::distance_shaped_axisymmetric(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0) || !std::isfinite(direction_norm)) {
    throw std::invalid_argument("Ray direction must be finite and non-zero");
  }
  const Vec3 u = direction / direction_norm;
  const auto bounds = bounding_box().ray_interval(origin, u);
  RootSearchDiagnostics diagnostics;
  diagnostics.solver_path = SolverPath::shaped_axisymmetric_certified;
  diagnostics.fallback_reason = SolverFallbackReason::none;
  if (!bounds) {
    return DistanceResult {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      diagnostics};
  }

  const auto function = [&](double t) {
    ++diagnostics.function_evaluations;
    return evaluate(origin + t * u);
  };
  double t_min = std::max(0.0, bounds->enter);
  const double t_max = bounds->exit;
  const double crossing_push = std::max(options.absolute_t_tolerance * 8.0,
    std::numeric_limits<double>::epsilon() * data_.characteristic_length * 64.0);
  if (coincident || std::abs(evaluate(origin)) <= options.absolute_f_tolerance) {
    t_min = std::max(t_min, crossing_push);
    for (int attempt = 0; attempt < 40 && t_min < t_max; ++attempt) {
      if (std::abs(function(t_min)) > 4.0 * options.absolute_f_tolerance) break;
      t_min *= 2.0;
    }
  }
  if (!(t_max > t_min)) {
    return DistanceResult {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      diagnostics};
  }

  struct Interval {
    double a;
    double b;
    double fa;
    double fb;
  };
  std::vector<Interval> stack;
  stack.push_back({t_min, t_max, function(t_min), function(t_max)});
  constexpr long interval_budget = 20000;
  const double isolation_width = std::max(
    64.0 * options.absolute_t_tolerance,
    1.0e-10 * data_.characteristic_length);

  const auto fallback = [&](SolverFallbackReason reason) {
    auto oracle = surface_.distance_reference(origin, direction, coincident, options);
    oracle.root_diagnostics.certified_excluded_intervals =
      diagnostics.certified_excluded_intervals;
    oracle.root_diagnostics.subdivided_intervals = diagnostics.subdivided_intervals;
    oracle.root_diagnostics.unresolved_intervals = diagnostics.unresolved_intervals;
    oracle.root_diagnostics.solver_path = SolverPath::reference_fallback;
    oracle.root_diagnostics.fallback_reason = reason;
    oracle.root_diagnostics.reference_fallback_calls = 1;
    return oracle;
  };

  while (!stack.empty()) {
    if (diagnostics.subdivided_intervals > interval_budget) {
      return fallback(SolverFallbackReason::interval_budget_exhausted);
    }
    const Interval interval = stack.back();
    stack.pop_back();
    const double midpoint = interval.a + 0.5 * (interval.b - interval.a);
    const double fm = function(midpoint);
    const double half_width = 0.5 * (interval.b - interval.a);
    const auto local = surface_.local_coordinates(origin + midpoint * u);
    const double rho_lower = std::max(0.0, local.rho - half_width);
    if (rho_lower > data_.coordinate_singularity_tolerance) {
      const double derivative_bound = 1.0
        + axisymmetric_radius_derivative_bound_ / rho_lower;
      if (std::abs(fm) > derivative_bound * half_width
                            + options.absolute_f_tolerance) {
        ++diagnostics.certified_excluded_intervals;
        continue;
      }
    }

    if (interval.b - interval.a <= isolation_width) {
      const bool left_bracket = std::signbit(interval.fa) != std::signbit(fm);
      const bool right_bracket = std::signbit(fm) != std::signbit(interval.fb);
      if (!left_bracket && !right_bracket
          && std::abs(fm) > options.absolute_f_tolerance) {
        ++diagnostics.unresolved_intervals;
        return fallback(
          SolverFallbackReason::unresolved_tangent_or_degenerate_interval);
      }
      double a = left_bracket ? interval.a : midpoint;
      double b = left_bracket ? midpoint : interval.b;
      double fa = left_bracket ? interval.fa : fm;
      double fb = left_bracket ? fm : interval.fb;
      if (!left_bracket && !right_bracket) {
        return DistanceResult {true, midpoint, RootKind::stationary_tangent,
          std::abs(fm), diagnostics};
      }
      double x = a + 0.5 * (b - a);
      double fx = function(x);
      for (int iteration = 0;
           iteration < options.max_bisection_iterations; ++iteration) {
        ++diagnostics.safeguarded_newton_iterations;
        if (std::abs(fx) <= options.absolute_f_tolerance
            || b - a <= options.absolute_t_tolerance
                          + options.relative_t_tolerance
                            * std::max(std::abs(a), std::abs(b))) break;
        if (std::signbit(fa) != std::signbit(fx)) {
          b = x;
          fb = fx;
        } else {
          a = x;
          fa = fx;
        }
        ++diagnostics.derivative_evaluations;
        const double derivative =
          surface_.directional_derivative(origin + x * u, u);
        const double newton = x - fx / derivative;
        x = std::isfinite(newton) && newton > a && newton < b
          ? newton : a + 0.5 * (b - a);
        fx = function(x);
      }
      (void) fb;
      return DistanceResult {true, x, RootKind::sign_change,
        std::abs(fx), diagnostics};
    }

    ++diagnostics.subdivided_intervals;
    stack.push_back({midpoint, interval.b, fm, interval.fb});
    stack.push_back({interval.a, midpoint, interval.fa, fm});
  }

  return DistanceResult {false, std::numeric_limits<double>::infinity(),
    RootKind::sign_change, std::numeric_limits<double>::infinity(),
    diagnostics};
}

DistanceResult CompiledPeriodicSplineSurface::distance_exact_torus(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0) || !std::isfinite(direction_norm)) {
    throw std::invalid_argument("Ray direction must be finite and non-zero");
  }
  const Vec3 u = direction / direction_norm;
  const double z = origin.z - torus_z_offset_;
  const double c2 = dot(u, u);
  const double c1 = 2.0 * (dot(origin, u) - torus_z_offset_ * u.z);
  const double c0 = origin.x * origin.x + origin.y * origin.y + z * z
                    + torus_major_radius_ * torus_major_radius_
                    - torus_minor_radius_ * torus_minor_radius_;
  const double four_major_squared =
    4.0 * torus_major_radius_ * torus_major_radius_;
  const double c2p = four_major_squared * (u.x * u.x + u.y * u.y);
  const double c1p = 2.0 * four_major_squared
                     * (origin.x * u.x + origin.y * u.y);
  const double c0p = four_major_squared
                     * (origin.x * origin.x + origin.y * origin.y);

  double coefficients[5] {
    coincident ? 0.0 : c0 * c0 - c0p,
    2.0 * c0 * c1 - c1p,
    c1 * c1 + 2.0 * c0 * c2 - c2p,
    2.0 * c1 * c2,
    c2 * c2};
  std::complex<double> roots[4];
  oqs::quartic_solver(coefficients, roots);

  RootSearchDiagnostics diagnostics;
  diagnostics.solver_path = SolverPath::exact_circular_torus;
  diagnostics.fallback_reason = SolverFallbackReason::none;
  const double crossing_push = std::max(options.absolute_t_tolerance * 8.0,
    std::numeric_limits<double>::epsilon() * data_.characteristic_length * 64.0);
  const double cutoff = coincident ? crossing_push : 0.0;
  double nearest = std::numeric_limits<double>::infinity();
  double nearest_residual = std::numeric_limits<double>::infinity();
  for (const auto& candidate : roots) {
    const double imaginary_tolerance =
      64.0 * std::sqrt(std::numeric_limits<double>::epsilon())
      * std::max(1.0, std::abs(candidate.real()));
    if (std::abs(candidate.imag()) > imaginary_tolerance) continue;
    double t = candidate.real();
    const double strict_imaginary_tolerance =
      64.0 * std::numeric_limits<double>::epsilon()
      * std::max(1.0, std::abs(t));
    const double candidate_derivative = coefficients[1]
      + t * (2.0 * coefficients[2]
        + t * (3.0 * coefficients[3] + t * 4.0 * coefficients[4]));
    const double derivative_scale = std::abs(coefficients[1])
      + std::abs(t) * (2.0 * std::abs(coefficients[2])
        + std::abs(t) * (3.0 * std::abs(coefficients[3])
          + std::abs(t) * 4.0 * std::abs(coefficients[4])));
    const bool repeated_root_candidate =
      std::abs(candidate_derivative)
      <= 64.0 * std::sqrt(std::numeric_limits<double>::epsilon())
           * std::max(1.0, derivative_scale);
    if (std::abs(candidate.imag()) > strict_imaginary_tolerance
        || repeated_root_candidate) {
      // A real double root is ill-conditioned in a general quartic solver and
      // is commonly returned as a tiny complex-conjugate pair. Its location is
      // a simple root of the derivative cubic, which is well-conditioned.
      for (int iteration = 0; iteration < 12; ++iteration) {
        const double derivative = coefficients[1]
          + t * (2.0 * coefficients[2]
            + t * (3.0 * coefficients[3] + t * 4.0 * coefficients[4]));
        const double second_derivative = 2.0 * coefficients[2]
          + t * (6.0 * coefficients[3] + t * 12.0 * coefficients[4]);
        if (!(std::abs(second_derivative) > 0.0)
            || !std::isfinite(second_derivative)) break;
        const double update = derivative / second_derivative;
        t -= update;
        if (std::abs(update) <= 2.0 * std::numeric_limits<double>::epsilon()
                                  * std::max(1.0, std::abs(t))) break;
      }
    }
    if (!(t > cutoff) || !(t < nearest)) continue;
    const Vec3 point = origin + t * u;
    const double shifted_z = point.z - torus_z_offset_;
    const double physical_sheet = point.x * point.x + point.y * point.y
                                  + shifted_z * shifted_z
                                  + torus_major_radius_ * torus_major_radius_
                                  - torus_minor_radius_ * torus_minor_radius_;
    const double sheet_tolerance = 1024.0
      * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length * data_.characteristic_length;
    if (physical_sheet < -sheet_tolerance) continue;
    const double residual = std::abs(evaluate(point));
    const double residual_tolerance = std::max(
      64.0 * options.absolute_f_tolerance,
      4096.0 * std::numeric_limits<double>::epsilon()
        * data_.characteristic_length);
    if (residual > residual_tolerance) continue;
    nearest = t;
    nearest_residual = residual;
  }
  if (!std::isfinite(nearest)) {
    return DistanceResult {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      diagnostics};
  }
  return DistanceResult {true, nearest, RootKind::sign_change,
    nearest_residual, diagnostics};
}

} // namespace stellarcsg
