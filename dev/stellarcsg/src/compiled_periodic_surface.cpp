#include "stellarcsg/compiled_periodic_surface.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace stellarcsg {
namespace {

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
{}

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
  return surface_.distance_reference(origin, direction, coincident, options);
}

} // namespace stellarcsg
