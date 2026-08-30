#include "stellarcsg/compiled_swept_surface.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace stellarcsg {
namespace {

constexpr double two_pi =
  2.0 * 3.141592653589793238462643383279502884;

std::vector<double> component(
  const std::vector<double>& values, std::size_t count, std::size_t axis)
{
  if (values.size() != 3 * count) {
    throw std::invalid_argument("Swept-spline vector coefficient shape is invalid");
  }
  std::vector<double> result(count);
  for (std::size_t i = 0; i < count; ++i) result[i] = values[3 * i + axis];
  return result;
}

void validate(const SweptSplineSurfaceData& data)
{
  if (data.sample_count < 8) {
    throw std::invalid_argument("Swept-spline surface requires at least eight samples");
  }
  if (data.centerline_coefficients.size() != 3 * data.sample_count
      || data.normal_coefficients.size() != 3 * data.sample_count
      || data.binormal_coefficients.size() != 3 * data.sample_count
      || data.major_radius_coefficients.size() != data.sample_count
      || data.minor_radius_coefficients.size() != data.sample_count) {
    throw std::invalid_argument("Swept-spline coefficient dimensions are inconsistent");
  }
  if (!(data.length > 0.0) || !(data.characteristic_length > 0.0)) {
    throw std::invalid_argument("Swept-spline length scales must be positive");
  }
  for (const double radius : data.major_radius_coefficients) {
    if (!(radius > 0.0)) throw std::invalid_argument("Major radii must be positive");
  }
  for (const double radius : data.minor_radius_coefficients) {
    if (!(radius > 0.0)) throw std::invalid_argument("Minor radii must be positive");
  }
}

double wrap(double angle)
{
  double value = std::fmod(angle, two_pi);
  if (value < 0.0) value += two_pi;
  return value;
}

} // namespace

CompiledSweptSplineSurface::CompiledSweptSplineSurface(
  SweptSplineSurfaceData data)
  : data_ {[&data]() { validate(data); return std::move(data); }()}
  , center_x_ {data_.sample_count, 1,
      component(data_.centerline_coefficients, data_.sample_count, 0)}
  , center_y_ {data_.sample_count, 1,
      component(data_.centerline_coefficients, data_.sample_count, 1)}
  , center_z_ {data_.sample_count, 1,
      component(data_.centerline_coefficients, data_.sample_count, 2)}
  , normal_x_ {data_.sample_count, 1,
      component(data_.normal_coefficients, data_.sample_count, 0)}
  , normal_y_ {data_.sample_count, 1,
      component(data_.normal_coefficients, data_.sample_count, 1)}
  , normal_z_ {data_.sample_count, 1,
      component(data_.normal_coefficients, data_.sample_count, 2)}
  , binormal_x_ {data_.sample_count, 1,
      component(data_.binormal_coefficients, data_.sample_count, 0)}
  , binormal_y_ {data_.sample_count, 1,
      component(data_.binormal_coefficients, data_.sample_count, 1)}
  , binormal_z_ {data_.sample_count, 1,
      component(data_.binormal_coefficients, data_.sample_count, 2)}
  , major_radius_ {data_.sample_count, 1, data_.major_radius_coefficients}
  , minor_radius_ {data_.sample_count, 1, data_.minor_radius_coefficients}
{
  const double radius_max = std::max(
    *std::max_element(data_.major_radius_coefficients.begin(),
      data_.major_radius_coefficients.end()),
    *std::max_element(data_.minor_radius_coefficients.begin(),
      data_.minor_radius_coefficients.end()));
  bounds_ = {{std::numeric_limits<double>::infinity(),
               std::numeric_limits<double>::infinity(),
               std::numeric_limits<double>::infinity()},
             {-std::numeric_limits<double>::infinity(),
               -std::numeric_limits<double>::infinity(),
               -std::numeric_limits<double>::infinity()}};
  for (std::size_t i = 0; i < data_.sample_count; ++i) {
    bounds_.lower.x = std::min(bounds_.lower.x,
      data_.centerline_coefficients[3 * i]);
    bounds_.lower.y = std::min(bounds_.lower.y,
      data_.centerline_coefficients[3 * i + 1]);
    bounds_.lower.z = std::min(bounds_.lower.z,
      data_.centerline_coefficients[3 * i + 2]);
    bounds_.upper.x = std::max(bounds_.upper.x,
      data_.centerline_coefficients[3 * i]);
    bounds_.upper.y = std::max(bounds_.upper.y,
      data_.centerline_coefficients[3 * i + 1]);
    bounds_.upper.z = std::max(bounds_.upper.z,
      data_.centerline_coefficients[3 * i + 2]);
  }
  bounds_.lower = bounds_.lower - Vec3 {radius_max, radius_max, radius_max};
  bounds_.upper = bounds_.upper + Vec3 {radius_max, radius_max, radius_max};

  double radius_sum = 0.0;
  double z_sum = 0.0;
  double cross_sum = 0.0;
  bool circular = true;
  const std::size_t checks = std::max<std::size_t>(64, data_.sample_count);
  for (std::size_t i = 0; i < checks; ++i) {
    const double angle = two_pi * static_cast<double>(i)
                         / static_cast<double>(checks);
    const auto frame_value = frame(angle);
    const double radius = std::hypot(frame_value.center.x, frame_value.center.y);
    radius_sum += radius;
    z_sum += frame_value.center.z;
    cross_sum += frame_value.major_radius;
  }
  const double mean_radius = radius_sum / static_cast<double>(checks);
  const double mean_z = z_sum / static_cast<double>(checks);
  const double mean_cross = cross_sum / static_cast<double>(checks);
  const double tolerance = 1.0e-6 * data_.characteristic_length;
  for (std::size_t i = 0; i < checks; ++i) {
    const auto value = frame(two_pi * static_cast<double>(i)
                             / static_cast<double>(checks));
    circular = circular
      && std::abs(std::hypot(value.center.x, value.center.y) - mean_radius)
           <= tolerance
      && std::abs(value.center.z - mean_z) <= tolerance
      && std::abs(value.major_radius - mean_cross) <= tolerance
      && std::abs(value.minor_radius - mean_cross) <= tolerance;
  }
  if (circular) {
    PeriodicSplineSurfaceData torus;
    torus.content_id = "swept-exact-torus-specialization";
    torus.axis_r_coefficients.assign(8, mean_radius);
    torus.axis_z_coefficients.assign(8, mean_z);
    torus.n_theta = 12;
    torus.n_phi = 8;
    torus.radius_coefficients.assign(torus.n_theta * torus.n_phi, mean_cross);
    torus.characteristic_length = mean_radius + mean_cross;
    exact_torus_ = std::make_unique<CompiledPeriodicSplineSurface>(std::move(torus));
  }
}

SweptLocalCoordinates CompiledSweptSplineSurface::frame(double angle) const
{
  const double q = wrap(angle);
  const auto cx = center_x_.sample(q);
  const auto cy = center_y_.sample(q);
  const auto cz = center_z_.sample(q);
  Vec3 tangent = normalized({cx.derivative, cy.derivative, cz.derivative});
  Vec3 normal_value {normal_x_.sample(q).value, normal_y_.sample(q).value,
    normal_z_.sample(q).value};
  normal_value = normal_value - dot(normal_value, tangent) * tangent;
  normal_value = normalized(normal_value);
  Vec3 binormal_value = normalized(cross(tangent, normal_value));
  normal_value = cross(binormal_value, tangent);
  return {data_.coil_id, q * data_.length / two_pi, 0.0, 0.0,
    {cx.value, cy.value, cz.value}, tangent, normal_value, binormal_value,
    major_radius_.sample(q).value, minor_radius_.sample(q).value};
}

double CompiledSweptSplineSurface::squared_distance(
  const Vec3& point, double angle) const
{
  const auto value = frame(angle);
  return norm_squared(point - value.center);
}

SweptLocalCoordinates CompiledSweptSplineSurface::local_coordinates(
  const Vec3& point) const
{
  const std::size_t scan_count = 4 * data_.sample_count;
  const double step = two_pi / static_cast<double>(scan_count);
  std::size_t best = 0;
  double best_value = std::numeric_limits<double>::infinity();
  for (std::size_t i = 0; i < scan_count; ++i) {
    const double value = squared_distance(point, step * static_cast<double>(i));
    if (value < best_value) { best_value = value; best = i; }
  }
  double left = step * (static_cast<double>(best) - 1.0);
  double right = step * (static_cast<double>(best) + 1.0);
  constexpr double ratio = 0.6180339887498948482;
  double c = right - ratio * (right - left);
  double d = left + ratio * (right - left);
  double fc = squared_distance(point, c);
  double fd = squared_distance(point, d);
  for (int iteration = 0; iteration < 48; ++iteration) {
    if (fc < fd) { right = d; d = c; fd = fc;
      c = right - ratio * (right - left); fc = squared_distance(point, c); }
    else { left = c; c = d; fc = fd;
      d = left + ratio * (right - left); fd = squared_distance(point, d); }
  }
  auto result = frame(0.5 * (left + right));
  const Vec3 offset = point - result.center;
  result.u = dot(offset, result.normal);
  result.v = dot(offset, result.binormal);
  return result;
}

double CompiledSweptSplineSurface::evaluate(const Vec3& point) const
{
  if (exact_torus_) return exact_torus_->evaluate(point);
  const auto local = local_coordinates(point);
  const double u = local.u / local.major_radius;
  const double v = local.v / local.minor_radius;
  return u * u + v * v - 1.0;
}

Vec3 CompiledSweptSplineSurface::normal(const Vec3& point) const
{
  if (exact_torus_) return exact_torus_->normal(point);
  const double h = std::sqrt(std::numeric_limits<double>::epsilon())
                   * data_.characteristic_length;
  const Vec3 gradient {
    (evaluate(point + Vec3 {h, 0.0, 0.0})
      - evaluate(point - Vec3 {h, 0.0, 0.0})) / (2.0 * h),
    (evaluate(point + Vec3 {0.0, h, 0.0})
      - evaluate(point - Vec3 {0.0, h, 0.0})) / (2.0 * h),
    (evaluate(point + Vec3 {0.0, 0.0, h})
      - evaluate(point - Vec3 {0.0, 0.0, h})) / (2.0 * h)};
  return normalized(gradient);
}

DistanceResult CompiledSweptSplineSurface::distance_reference(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  if (exact_torus_) return exact_torus_->distance(origin, direction, coincident, options);
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0)) {
    throw std::invalid_argument("Ray direction must be non-zero");
  }
  const Vec3 u = direction / direction_norm;
  const auto interval = bounds_.ray_interval(origin, u);
  if (!interval) return {};
  double t_min = std::max(0.0, interval->enter);
  const double push = 8.0 * options.absolute_t_tolerance;
  if (coincident || std::abs(evaluate(origin)) <= options.absolute_f_tolerance)
    t_min = std::max(t_min, push);
  if (!(interval->exit > t_min)) return {};
  const auto function = [&](double t) { return evaluate(origin + t * u); };
  const auto derivative = [&](double t) {
    const double h = std::sqrt(std::numeric_limits<double>::epsilon())
                     * data_.characteristic_length;
    return (function(t + h) - function(t - h)) / (2.0 * h);
  };
  const auto root = find_nearest_root_reference(
    function, derivative, t_min, interval->exit, options);
  if (!root.found) return {false, std::numeric_limits<double>::infinity(),
    RootKind::sign_change, std::numeric_limits<double>::infinity(),
    root.diagnostics};
  return {true, root.root.t, root.root.kind, root.root.residual,
    root.diagnostics};
}

} // namespace stellarcsg
