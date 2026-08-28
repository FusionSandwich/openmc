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

} // namespace

PeriodicRadialSurface::PeriodicRadialSurface(AxisField axis, RadiusField radius,
  BoundingBox conservative_bounds, double characteristic_length,
  double coordinate_singularity_tolerance)
  : axis_ {std::move(axis)}
  , radius_ {std::move(radius)}
  , conservative_bounds_ {conservative_bounds}
  , characteristic_length_ {characteristic_length}
  , coordinate_singularity_tolerance_ {coordinate_singularity_tolerance}
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
    // Move outside the numerical coincidence band before asking the root oracle
    // for the next crossing. A fixed machine-epsilon push is insufficient when
    // the surface residual tolerance is much larger than machine epsilon.
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
  diagnostics_.root_function_evaluations += root.diagnostics.function_evaluations;
  diagnostics_.root_derivative_evaluations += root.diagnostics.derivative_evaluations;

  if (!root.found) {
    return DistanceResult {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      root.diagnostics};
  }
  return DistanceResult {true, root.root.t, root.root.kind,
    root.root.residual, root.diagnostics};
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
