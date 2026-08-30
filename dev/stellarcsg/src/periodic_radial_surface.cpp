#include "stellarcsg/periodic_radial_surface.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace stellarcsg {
namespace {

constexpr double two_pi = 2.0 * 3.141592653589793238462643383279502884;

double wrap_phi(double phi)
{
  double wrapped = std::fmod(phi, two_pi);
  if (wrapped < 0.0) {
    wrapped += two_pi;
  }
  if (wrapped >= two_pi) {
    wrapped = 0.0;
  }
  return wrapped;
}

bool finite_axis(const AxisSample& axis)
{
  return std::isfinite(axis.R) && std::isfinite(axis.Z)
         && std::isfinite(axis.dR_dphi) && std::isfinite(axis.dZ_dphi);
}

bool finite_radius(const RadiusSample& radius)
{
  return std::isfinite(radius.value) && std::isfinite(radius.dtheta)
         && std::isfinite(radius.dphi);
}

double t_tolerance(double a, double b, const FastDistanceOptions& options)
{
  return options.absolute_t_tolerance
         + options.relative_t_tolerance * std::max(std::abs(a), std::abs(b));
}

struct FastEvaluator {
  const PeriodicRadialSurface& surface;
  Vec3 origin;
  Vec3 direction;
  RootSearchDiagnostics diagnostics {};

  double f(double t)
  {
    ++diagnostics.function_evaluations;
    return surface.evaluate(origin + t * direction);
  }

  double df(double t)
  {
    ++diagnostics.derivative_evaluations;
    return surface.directional_derivative(origin + t * direction, direction);
  }
};

struct RefinedRoot {
  bool found {false};
  double t {std::numeric_limits<double>::infinity()};
  double residual {std::numeric_limits<double>::infinity()};
  int iterations {0};
};

RefinedRoot refine_sign_change(FastEvaluator& evaluator, double a, double b,
  double fa, double fb, const FastDistanceOptions& options)
{
  RefinedRoot result;
  if (!std::isfinite(fa) || !std::isfinite(fb)) return result;
  if (std::abs(fa) <= options.absolute_f_tolerance) {
    return {true, a, std::abs(fa), 0};
  }
  if (std::abs(fb) <= options.absolute_f_tolerance) {
    return {true, b, std::abs(fb), 0};
  }
  if (std::signbit(fa) == std::signbit(fb)) return result;

  double x = std::abs(fa) < std::abs(fb) ? a : b;
  double fx = std::abs(fa) < std::abs(fb) ? fa : fb;
  for (int iteration = 1; iteration <= options.maximum_hybrid_iterations;
       ++iteration) {
    result.iterations = iteration;
    double candidate = a + 0.5 * (b - a);

    const double dfx = evaluator.df(x);
    if (std::isfinite(dfx) && std::abs(dfx) > options.derivative_tolerance) {
      const double newton = x - fx / dfx;
      if (newton > a && newton < b) candidate = newton;
    } else if (fb != fa) {
      const double secant = (a * fb - b * fa) / (fb - fa);
      if (secant > a && secant < b) candidate = secant;
    }

    double fc = evaluator.f(candidate);
    if (!std::isfinite(fc)) {
      candidate = a + 0.5 * (b - a);
      fc = evaluator.f(candidate);
      if (!std::isfinite(fc)) return {};
    }
    if (std::abs(fc) <= options.absolute_f_tolerance
        || (b - a) <= t_tolerance(a, b, options)) {
      return {true, candidate, std::abs(fc), iteration};
    }

    if (std::signbit(fa) != std::signbit(fc)) {
      b = candidate;
      fb = fc;
    } else {
      a = candidate;
      fa = fc;
    }
    x = std::abs(fa) < std::abs(fb) ? a : b;
    fx = std::abs(fa) < std::abs(fb) ? fa : fb;
  }

  const double midpoint = a + 0.5 * (b - a);
  const double residual = std::abs(evaluator.f(midpoint));
  return {residual <= options.tangent_residual_multiplier
                       * options.absolute_f_tolerance,
    midpoint, residual, options.maximum_hybrid_iterations};
}

RefinedRoot refine_stationary(FastEvaluator& evaluator, double a, double b,
  double dfa, double dfb, const FastDistanceOptions& options)
{
  RefinedRoot result;
  if (!std::isfinite(dfa) || !std::isfinite(dfb)) return result;
  double t = a;
  if (std::abs(dfa) <= options.derivative_tolerance) {
    t = a;
  } else if (std::abs(dfb) <= options.derivative_tolerance) {
    t = b;
  } else if (std::signbit(dfa) != std::signbit(dfb)) {
    for (int iteration = 1; iteration <= options.maximum_stationary_iterations;
         ++iteration) {
      result.iterations = iteration;
      const double midpoint = a + 0.5 * (b - a);
      const double dfm = evaluator.df(midpoint);
      if (!std::isfinite(dfm)) return {};
      if (std::abs(dfm) <= options.derivative_tolerance
          || (b - a) <= t_tolerance(a, b, options)) {
        t = midpoint;
        break;
      }
      if (std::signbit(dfa) != std::signbit(dfm)) {
        b = midpoint;
        dfb = dfm;
      } else {
        a = midpoint;
        dfa = dfm;
      }
      t = a + 0.5 * (b - a);
    }
  } else {
    return result;
  }

  // A stationary point is useful even when it is not itself a tangent root.
  // If its signed value is opposite to the interval endpoints, the interval
  // contains a close pair of ordinary roots. Returning the stationary point
  // lets the caller split the interval and refine the earlier crossing.
  const double residual = std::abs(evaluator.f(t));
  return {true, t, residual, result.iterations};
}

} // namespace

PeriodicRadialSurface::PeriodicRadialSurface(AxisField axis, RadiusField radius,
  BoundingBox conservative_bounds, double characteristic_length,
  double coordinate_singularity_tolerance, double minimum_feature_length)
  : axis_ {std::move(axis)}
  , radius_ {std::move(radius)}
  , conservative_bounds_ {conservative_bounds}
  , characteristic_length_ {characteristic_length}
  , coordinate_singularity_tolerance_ {coordinate_singularity_tolerance}
  , minimum_feature_length_ {minimum_feature_length > 0.0
        ? minimum_feature_length
        : characteristic_length / 16.0}
{
  if (!axis_ || !radius_) {
    throw std::invalid_argument("Axis and radius fields must be callable");
  }
  if (!conservative_bounds_.valid()) {
    throw std::invalid_argument("Surface bounding box is invalid");
  }
  if (!(characteristic_length_ > 0.0) || !std::isfinite(characteristic_length_)) {
    throw std::invalid_argument("Characteristic length must be finite and positive");
  }
  if (!(coordinate_singularity_tolerance_ > 0.0)) {
    throw std::invalid_argument("Coordinate singularity tolerance must be positive");
  }
  if (!(minimum_feature_length_ > 0.0)
      || !std::isfinite(minimum_feature_length_)) {
    throw std::invalid_argument("Minimum feature length must be finite and positive");
  }
}

SurfaceDiagnostics PeriodicRadialSurface::diagnostics() const noexcept
{
  return SurfaceDiagnostics {
    diagnostics_.evaluate_calls.load(std::memory_order_relaxed),
    diagnostics_.gradient_calls.load(std::memory_order_relaxed),
    diagnostics_.distance_calls.load(std::memory_order_relaxed),
    diagnostics_.fast_distance_calls.load(std::memory_order_relaxed),
    diagnostics_.reference_distance_calls.load(std::memory_order_relaxed),
    diagnostics_.fast_fallbacks.load(std::memory_order_relaxed),
    diagnostics_.finite_difference_directional_derivatives.load(
      std::memory_order_relaxed),
    diagnostics_.root_function_evaluations.load(std::memory_order_relaxed),
    diagnostics_.root_derivative_evaluations.load(std::memory_order_relaxed)};
}

void PeriodicRadialSurface::reset_diagnostics() const noexcept
{
  diagnostics_.evaluate_calls.store(0, std::memory_order_relaxed);
  diagnostics_.gradient_calls.store(0, std::memory_order_relaxed);
  diagnostics_.distance_calls.store(0, std::memory_order_relaxed);
  diagnostics_.fast_distance_calls.store(0, std::memory_order_relaxed);
  diagnostics_.reference_distance_calls.store(0, std::memory_order_relaxed);
  diagnostics_.fast_fallbacks.store(0, std::memory_order_relaxed);
  diagnostics_.finite_difference_directional_derivatives.store(
    0, std::memory_order_relaxed);
  diagnostics_.root_function_evaluations.store(0, std::memory_order_relaxed);
  diagnostics_.root_derivative_evaluations.store(0, std::memory_order_relaxed);
}

LocalCoordinates PeriodicRadialSurface::local_coordinates(const Vec3& point) const
{
  const double R = std::hypot(point.x, point.y);
  const double phi = wrap_phi(std::atan2(point.y, point.x));
  const AxisSample axis = axis_(phi);
  if (!finite_axis(axis)) {
    throw std::domain_error("Axis field returned a non-finite sample");
  }

  const double q_R = R - axis.R;
  const double q_Z = point.z - axis.Z;
  const double rho = std::hypot(q_R, q_Z);
  const double theta = rho > coordinate_singularity_tolerance_
                         ? std::atan2(q_Z, q_R)
                         : 0.0;
  const RadiusSample surface_radius = radius_(theta, phi);
  if (!finite_radius(surface_radius) || !(surface_radius.value > 0.0)) {
    throw std::domain_error("Radius field must return a finite, positive radius");
  }

  return LocalCoordinates {
    R, phi, q_R, q_Z, rho, theta, axis, surface_radius};
}

double PeriodicRadialSurface::evaluate(const Vec3& point) const
{
  ++diagnostics_.evaluate_calls;
  const auto local = local_coordinates(point);
  return local.rho - local.surface_radius.value;
}

Vec3 PeriodicRadialSurface::gradient(const Vec3& point) const
{
  ++diagnostics_.gradient_calls;
  const auto local = local_coordinates(point);
  if (local.R <= coordinate_singularity_tolerance_) {
    throw std::domain_error("Cylindrical azimuth is singular at R=0");
  }
  if (local.rho <= coordinate_singularity_tolerance_) {
    throw std::domain_error("Poloidal angle is singular on the reference axis");
  }

  const double inv_rho = 1.0 / local.rho;
  const double inv_rho_squared = inv_rho * inv_rho;

  const double rho_R = local.q_R * inv_rho;
  const double rho_Z = local.q_Z * inv_rho;
  const double rho_phi =
    -(local.q_R * local.axis.dR_dphi + local.q_Z * local.axis.dZ_dphi) * inv_rho;

  const double theta_R = -local.q_Z * inv_rho_squared;
  const double theta_Z = local.q_R * inv_rho_squared;
  const double theta_phi =
    (local.q_Z * local.axis.dR_dphi - local.q_R * local.axis.dZ_dphi)
    * inv_rho_squared;

  const double F_R = rho_R - local.surface_radius.dtheta * theta_R;
  const double F_Z = rho_Z - local.surface_radius.dtheta * theta_Z;
  const double F_phi = rho_phi - local.surface_radius.dtheta * theta_phi
                       - local.surface_radius.dphi;

  const double inv_R = 1.0 / local.R;
  const double inv_R_squared = inv_R * inv_R;
  return {
    F_R * point.x * inv_R - F_phi * point.y * inv_R_squared,
    F_R * point.y * inv_R + F_phi * point.x * inv_R_squared,
    F_Z,
  };
}

Vec3 PeriodicRadialSurface::normal(const Vec3& point) const
{
  return normalized(gradient(point));
}

double PeriodicRadialSurface::directional_derivative(
  const Vec3& point, const Vec3& direction) const
{
  try {
    return dot(gradient(point), direction);
  } catch (const std::domain_error&) {
    ++diagnostics_.finite_difference_directional_derivatives;
    const double direction_norm = norm(direction);
    if (!(direction_norm > 0.0)) {
      throw std::invalid_argument("Ray direction must be non-zero");
    }
    const double h = std::sqrt(std::numeric_limits<double>::epsilon())
                     * characteristic_length_ / direction_norm;
    return (evaluate(point + h * direction) - evaluate(point - h * direction))
           / (2.0 * h);
  }
}

DistanceResult PeriodicRadialSurface::distance_reference(const Vec3& origin,
  const Vec3& direction, bool coincident, const RootSearchOptions& options) const
{
  ++diagnostics_.distance_calls;
  ++diagnostics_.reference_distance_calls;
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0) || !std::isfinite(direction_norm)) {
    throw std::invalid_argument("Ray direction must be finite and non-zero");
  }
  const Vec3 unit_direction = direction / direction_norm;
  const auto bounds_interval = conservative_bounds_.ray_interval(origin, unit_direction);
  if (!bounds_interval) {
    return {};
  }

  const double crossing_push = std::max(options.absolute_t_tolerance * 8.0,
    std::numeric_limits<double>::epsilon() * characteristic_length_ * 64.0);
  double t_min = std::max(0.0, bounds_interval->enter);
  const double t_max = bounds_interval->exit;
  if (coincident || std::abs(evaluate(origin)) <= options.absolute_f_tolerance) {
    t_min = std::max(t_min, crossing_push);
    for (int attempt = 0; attempt < 40 && t_min < t_max; ++attempt) {
      if (std::abs(evaluate(origin + t_min * unit_direction))
          > 4.0 * options.absolute_f_tolerance) {
        break;
      }
      t_min *= 2.0;
    }
  }
  if (!(t_max > t_min)) {
    return {};
  }

  const auto function = [&](double t) {
    return evaluate(origin + t * unit_direction);
  };
  const auto derivative = [&](double t) {
    return directional_derivative(origin + t * unit_direction, unit_direction);
  };

  RootSearchResult root =
    find_nearest_root_reference(function, derivative, t_min, t_max, options);
  diagnostics_.root_function_evaluations.fetch_add(
    root.diagnostics.function_evaluations, std::memory_order_relaxed);
  diagnostics_.root_derivative_evaluations.fetch_add(
    root.diagnostics.derivative_evaluations, std::memory_order_relaxed);

  if (!root.found) {
    return DistanceResult {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      root.diagnostics, false, 0, 0};
  }
  return DistanceResult {true, root.root.t, root.root.kind,
    root.root.residual, root.diagnostics, false, 0, 0};
}

DistanceResult PeriodicRadialSurface::distance_fast(const Vec3& origin,
  const Vec3& direction, bool coincident,
  const FastDistanceOptions& options) const
{
  ++diagnostics_.distance_calls;
  ++diagnostics_.fast_distance_calls;
  if (options.minimum_scan_intervals < 2
      || options.maximum_scan_intervals < options.minimum_scan_intervals
      || options.maximum_hybrid_iterations < 1
      || !(options.maximum_scan_step_fraction > 0.0)
      || !(options.absolute_f_tolerance > 0.0)) {
    throw std::invalid_argument("Fast distance options are invalid");
  }

  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0) || !std::isfinite(direction_norm)) {
    throw std::invalid_argument("Ray direction must be finite and non-zero");
  }
  const Vec3 unit_direction = direction / direction_norm;
  const auto bounds_interval = conservative_bounds_.ray_interval(origin, unit_direction);
  if (!bounds_interval) return {};

  double t_min = std::max(0.0, bounds_interval->enter);
  const double t_max = bounds_interval->exit;
  const double crossing_push = std::max(options.absolute_t_tolerance * 8.0,
    std::numeric_limits<double>::epsilon() * characteristic_length_ * 64.0);
  if (coincident || std::abs(evaluate(origin)) <= options.absolute_f_tolerance) {
    t_min = std::max(t_min, crossing_push);
    for (int attempt = 0; attempt < 40 && t_min < t_max; ++attempt) {
      if (std::abs(evaluate(origin + t_min * unit_direction))
          > 4.0 * options.absolute_f_tolerance) break;
      t_min *= 2.0;
    }
  }
  if (!(t_max > t_min)) return {};

  const double maximum_step = std::max(options.absolute_t_tolerance * 64.0,
    options.maximum_scan_step_fraction * minimum_feature_length_);
  int intervals = static_cast<int>(std::ceil((t_max - t_min) / maximum_step));
  intervals = std::clamp(intervals, options.minimum_scan_intervals,
    options.maximum_scan_intervals);
  const double step = (t_max - t_min) / static_cast<double>(intervals);

  FastEvaluator evaluator {*this, origin, unit_direction};
  double a = t_min;
  double fa = evaluator.f(a);
  double dfa = evaluator.df(a);
  int total_iterations = 0;

  for (int i = 0; i < intervals; ++i) {
    const double b = i + 1 == intervals ? t_max : t_min + step * (i + 1);
    const double fb = evaluator.f(b);
    const double dfb = evaluator.df(b);

    if (std::isfinite(fa) && std::abs(fa) <= options.absolute_f_tolerance) {
      diagnostics_.root_function_evaluations.fetch_add(
        evaluator.diagnostics.function_evaluations, std::memory_order_relaxed);
      diagnostics_.root_derivative_evaluations.fetch_add(
        evaluator.diagnostics.derivative_evaluations, std::memory_order_relaxed);
      return {true, a, RootKind::sampled_zero, std::abs(fa),
        evaluator.diagnostics, false, intervals, total_iterations};
    }

    // Midpoint sampling catches a common two-crossing interval that has equal
    // endpoint signs without paying for a globally refined scan.
    const double midpoint = a + 0.5 * (b - a);
    const double fm = evaluator.f(midpoint);
    const double dfm = evaluator.df(midpoint);
    const struct Segment {
      double left;
      double right;
      double fleft;
      double fright;
      double dfleft;
      double dfright;
    } segments[2] {{a, midpoint, fa, fm, dfa, dfm},
      {midpoint, b, fm, fb, dfm, dfb}};

    for (const auto& segment : segments) {
      if (!std::isfinite(segment.fleft) || !std::isfinite(segment.fright)) continue;
      if (std::signbit(segment.fleft) != std::signbit(segment.fright)) {
        const auto root = refine_sign_change(evaluator, segment.left, segment.right,
          segment.fleft, segment.fright, options);
        total_iterations += root.iterations;
        if (root.found) {
          diagnostics_.root_function_evaluations.fetch_add(
        evaluator.diagnostics.function_evaluations, std::memory_order_relaxed);
          diagnostics_.root_derivative_evaluations.fetch_add(
        evaluator.diagnostics.derivative_evaluations, std::memory_order_relaxed);
          return {true, root.t, RootKind::sign_change, root.residual,
            evaluator.diagnostics, false, intervals, total_iterations};
        }
      }

      const bool stationary_possible =
        std::isfinite(segment.dfleft) && std::isfinite(segment.dfright)
        && (std::signbit(segment.dfleft) != std::signbit(segment.dfright)
            || std::abs(segment.dfleft) <= options.derivative_tolerance
            || std::abs(segment.dfright) <= options.derivative_tolerance);
      if (stationary_possible) {
        const auto stationary = refine_stationary(evaluator, segment.left,
          segment.right, segment.dfleft, segment.dfright, options);
        total_iterations += stationary.iterations;
        if (stationary.found) {
          const double fs = evaluator.f(stationary.t);
          if (std::abs(fs) <= options.tangent_residual_multiplier
                              * options.absolute_f_tolerance) {
            diagnostics_.root_function_evaluations.fetch_add(
              evaluator.diagnostics.function_evaluations,
              std::memory_order_relaxed);
            diagnostics_.root_derivative_evaluations.fetch_add(
              evaluator.diagnostics.derivative_evaluations,
              std::memory_order_relaxed);
            return {true, stationary.t, RootKind::stationary_tangent,
              std::abs(fs), evaluator.diagnostics, false, intervals,
              total_iterations};
          }

          // A stationary value with opposite sign from either endpoint means
          // a close pair of crossings was hidden inside a scan segment. Search
          // the left half first so the returned root is the nearest positive
          // intersection along the ray.
          if (std::signbit(segment.fleft) != std::signbit(fs)) {
            const auto root = refine_sign_change(evaluator, segment.left,
              stationary.t, segment.fleft, fs, options);
            total_iterations += root.iterations;
            if (root.found) {
              diagnostics_.root_function_evaluations.fetch_add(
                evaluator.diagnostics.function_evaluations,
                std::memory_order_relaxed);
              diagnostics_.root_derivative_evaluations.fetch_add(
                evaluator.diagnostics.derivative_evaluations,
                std::memory_order_relaxed);
              return {true, root.t, RootKind::sign_change, root.residual,
                evaluator.diagnostics, false, intervals, total_iterations};
            }
          }
          if (std::signbit(fs) != std::signbit(segment.fright)) {
            const auto root = refine_sign_change(evaluator, stationary.t,
              segment.right, fs, segment.fright, options);
            total_iterations += root.iterations;
            if (root.found) {
              diagnostics_.root_function_evaluations.fetch_add(
                evaluator.diagnostics.function_evaluations,
                std::memory_order_relaxed);
              diagnostics_.root_derivative_evaluations.fetch_add(
                evaluator.diagnostics.derivative_evaluations,
                std::memory_order_relaxed);
              return {true, root.t, RootKind::sign_change, root.residual,
                evaluator.diagnostics, false, intervals, total_iterations};
            }
          }
        }
      }
    }

    a = b;
    fa = fb;
    dfa = dfb;
  }

  diagnostics_.root_function_evaluations.fetch_add(
        evaluator.diagnostics.function_evaluations, std::memory_order_relaxed);
  diagnostics_.root_derivative_evaluations.fetch_add(
        evaluator.diagnostics.derivative_evaluations, std::memory_order_relaxed);
  if (!options.fallback_to_reference) {
    return {false, std::numeric_limits<double>::infinity(), RootKind::sign_change,
      std::numeric_limits<double>::infinity(), evaluator.diagnostics, false,
      intervals, total_iterations};
  }

  ++diagnostics_.fast_fallbacks;
  auto fallback = distance_reference(origin, direction, coincident,
    options.fallback_options);
  fallback.used_fallback = true;
  fallback.scan_intervals = intervals;
  fallback.hybrid_iterations = total_iterations;
  return fallback;
}

AxisField circular_axis(double major_radius, double z_offset)
{
  if (!(major_radius > 0.0) || !std::isfinite(major_radius)
      || !std::isfinite(z_offset)) {
    throw std::invalid_argument("Circular-axis parameters are invalid");
  }
  return [major_radius, z_offset](double) {
    return AxisSample {major_radius, z_offset, 0.0, 0.0};
  };
}

RadiusField constant_radius(double minor_radius)
{
  if (!(minor_radius > 0.0) || !std::isfinite(minor_radius)) {
    throw std::invalid_argument("Minor radius must be finite and positive");
  }
  return [minor_radius](double, double) {
    return RadiusSample {minor_radius, 0.0, 0.0};
  };
}

} // namespace stellarcsg
