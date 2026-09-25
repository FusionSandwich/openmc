#include "stellarcsg/compiled_periodic_surface.hpp"
#include "stellarcsg/performance_counters.hpp"

#include <algorithm>
#include <cmath>
#include <complex>
#include <array>
#include <cstdint>
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

double cyclic_derivative_bound(const std::vector<double>& values,
  double coordinate_scale)
{
  double maximum_difference = 0.0;
  for (std::size_t i = 0; i < values.size(); ++i) {
    maximum_difference = std::max(maximum_difference,
      std::abs(values[(i + 1) % values.size()] - values[i]));
  }
  // A cardinal cubic B-spline derivative is a convex combination of the
  // three adjacent cyclic control-point differences in its active cell.
  return maximum_difference * coordinate_scale;
}

double bicubic_theta_derivative_bound(const PeriodicSplineSurfaceData& data)
{
  double maximum_difference = 0.0;
  for (std::size_t i = 0; i < data.n_theta; ++i) {
    const std::size_t next = (i + 1) % data.n_theta;
    for (std::size_t j = 0; j < data.n_phi; ++j) {
      maximum_difference = std::max(maximum_difference,
        std::abs(data.radius_coefficients[next * data.n_phi + j]
          - data.radius_coefficients[i * data.n_phi + j]));
    }
  }
  return maximum_difference * static_cast<double>(data.n_theta) / two_pi;
}

double bicubic_phi_derivative_bound(const PeriodicSplineSurfaceData& data)
{
  double maximum_difference = 0.0;
  for (std::size_t i = 0; i < data.n_theta; ++i) {
    for (std::size_t j = 0; j < data.n_phi; ++j) {
      const std::size_t next = (j + 1) % data.n_phi;
      maximum_difference = std::max(maximum_difference,
        std::abs(data.radius_coefficients[i * data.n_phi + next]
          - data.radius_coefficients[i * data.n_phi + j]));
    }
  }
  return maximum_difference
         * static_cast<double>(data.n_phi
           * static_cast<std::size_t>(data.n_field_periods)) / two_pi;
}

std::size_t wrap_index(long index, std::size_t size)
{
  const long signed_size = static_cast<long>(size);
  long wrapped = index % signed_size;
  if (wrapped < 0) wrapped += signed_size;
  return static_cast<std::size_t>(wrapped);
}

std::size_t periodic_cell(double angle, std::size_t size, int multiplier)
{
  double reduced = std::fmod(static_cast<double>(multiplier) * angle, two_pi);
  if (reduced < 0.0) reduced += two_pi;
  const auto cell = static_cast<std::size_t>(
    std::floor(reduced * static_cast<double>(size) / two_pi));
  return cell < size ? cell : 0U;
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
  const double axis_coordinate_scale =
    static_cast<double>(data_.axis_r_coefficients.size()
      * static_cast<std::size_t>(data_.n_field_periods)) / two_pi;
  const double axis_r_derivative_bound = cyclic_derivative_bound(
    data_.axis_r_coefficients, axis_coordinate_scale);
  const double axis_z_derivative_bound = cyclic_derivative_bound(
    data_.axis_z_coefficients, axis_coordinate_scale);
  axis_derivative_bound_ = std::hypot(
    axis_r_derivative_bound, axis_z_derivative_bound);
  radius_theta_derivative_bound_ = bicubic_theta_derivative_bound(data_);
  radius_phi_derivative_bound_ = bicubic_phi_derivative_bound(data_);
  const auto radius_bounds = std::minmax_element(
    data_.radius_coefficients.begin(), data_.radius_coefficients.end());
  radius_coefficient_min_ = *radius_bounds.first;
  radius_coefficient_max_ = *radius_bounds.second;
  const std::size_t axis_size = data_.axis_r_coefficients.size();
  axis_local_derivative_bounds_.resize(axis_size);
  for (std::size_t center = 0; center < axis_size; ++center) {
    double local_maximum = 0.0;
    for (long offset = -3; offset <= 3; ++offset) {
      const std::size_t i = wrap_index(
        static_cast<long>(center) + offset, axis_size);
      const std::size_t next = (i + 1) % axis_size;
      local_maximum = std::max(local_maximum, std::hypot(
        data_.axis_r_coefficients[next] - data_.axis_r_coefficients[i],
        data_.axis_z_coefficients[next] - data_.axis_z_coefficients[i]));
    }
    axis_local_derivative_bounds_[center] =
      local_maximum * axis_coordinate_scale;
  }
  const std::size_t radius_size = data_.n_theta * data_.n_phi;
  radius_local_theta_derivative_bounds_.resize(radius_size);
  radius_local_phi_derivative_bounds_.resize(radius_size);
  const double theta_scale = static_cast<double>(data_.n_theta) / two_pi;
  const double phi_scale = static_cast<double>(data_.n_phi
    * static_cast<std::size_t>(data_.n_field_periods)) / two_pi;
  for (std::size_t center_i = 0; center_i < data_.n_theta; ++center_i) {
    for (std::size_t center_j = 0; center_j < data_.n_phi; ++center_j) {
      double theta_maximum = 0.0;
      double phi_maximum = 0.0;
      for (long di = -3; di <= 3; ++di) {
        const std::size_t i = wrap_index(
          static_cast<long>(center_i) + di, data_.n_theta);
        const std::size_t next_i = (i + 1) % data_.n_theta;
        for (long dj = -3; dj <= 3; ++dj) {
          const std::size_t j = wrap_index(
            static_cast<long>(center_j) + dj, data_.n_phi);
          const std::size_t next_j = (j + 1) % data_.n_phi;
          theta_maximum = std::max(theta_maximum, std::abs(
            data_.radius_coefficients[next_i * data_.n_phi + j]
            - data_.radius_coefficients[i * data_.n_phi + j]));
          phi_maximum = std::max(phi_maximum, std::abs(
            data_.radius_coefficients[i * data_.n_phi + next_j]
            - data_.radius_coefficients[i * data_.n_phi + j]));
        }
      }
      const std::size_t flat = center_i * data_.n_phi + center_j;
      radius_local_theta_derivative_bounds_[flat] =
        theta_maximum * theta_scale;
      radius_local_phi_derivative_bounds_[flat] = phi_maximum * phi_scale;
    }
  }
  if (data_.force_general_solver) {
    specialization_ = PeriodicSurfaceSpecialization::general_periodic;
  }
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
  if (specialization_ == PeriodicSurfaceSpecialization::general_periodic) {
    build_periodic_patches();
  }
}

double CompiledPeriodicSplineSurface::evaluate(const Vec3& point) const
{
  add_performance_counter(PerformanceCounter::evaluate_calls);
  return surface_.evaluate(point);
}

Vec3 CompiledPeriodicSplineSurface::gradient(const Vec3& point) const
{
  return surface_.gradient(point);
}

Vec3 CompiledPeriodicSplineSurface::normal(const Vec3& point) const
{
  add_performance_counter(PerformanceCounter::normal_calls);
  return surface_.normal(point);
}

DistanceResult CompiledPeriodicSplineSurface::distance_reference(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  add_performance_counter(PerformanceCounter::distance_calls);
  add_performance_counter(PerformanceCounter::global_reference_calls);
  if (coincident) add_performance_counter(PerformanceCounter::coincident_cases);
  [[maybe_unused]] ScopedDistanceTimer timer;
  auto result = surface_.distance_reference(origin, direction, coincident, options);
  result.root_diagnostics.solver_path = SolverPath::global_reference;
  result.root_diagnostics.fallback_reason =
    SolverFallbackReason::reference_requested;
  add_performance_counter(result.found ? PerformanceCounter::accepted_roots
                                       : PerformanceCounter::no_hit_returns);
  if (result.found) record_residual(result.residual, data_.characteristic_length);
  return result;
}

DistanceResult CompiledPeriodicSplineSurface::distance(const Vec3& origin,
  const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  add_performance_counter(PerformanceCounter::distance_calls);
  if (coincident) add_performance_counter(PerformanceCounter::coincident_cases);
  [[maybe_unused]] ScopedDistanceTimer timer;
  DistanceResult result;
  if (specialization_ == PeriodicSurfaceSpecialization::exact_circular_torus) {
    result = distance_exact_torus(origin, direction, coincident, options);
  } else if (specialization_
             == PeriodicSurfaceSpecialization::shaped_axisymmetric) {
    result = distance_shaped_axisymmetric(origin, direction, coincident, options);
  } else {
    result = distance_general_periodic(origin, direction, coincident, options);
  }
#ifdef STELLARCSG_VERIFY_FAST_WITH_ORACLE
  if (specialization_ == PeriodicSurfaceSpecialization::general_periodic) {
    static thread_local std::uint64_t verification_counter = 0;
    if ((verification_counter++ & 4095U) == 0U) {
      const auto oracle = surface_.distance_reference(
        origin, direction, coincident, options);
      const double tolerance = options.absolute_t_tolerance * 32.0
        + options.relative_t_tolerance
          * std::max(std::abs(result.distance), std::abs(oracle.distance));
      if (result.found != oracle.found
          || (result.found && std::abs(result.distance - oracle.distance)
                               > tolerance)) {
        throw std::runtime_error(
          "Periodic patch result disagrees with the independent oracle");
      }
    }
  }
#endif
  add_performance_counter(result.found ? PerformanceCounter::accepted_roots
                                       : PerformanceCounter::no_hit_returns);
  if (result.found) record_residual(result.residual, data_.characteristic_length);
  return result;
}

namespace {

BoundingBox empty_box()
{
  const double infinity = std::numeric_limits<double>::infinity();
  return {{infinity, infinity, infinity},
    {-infinity, -infinity, -infinity}};
}

void extend(BoundingBox& box, const Vec3& point)
{
  box.lower.x = std::min(box.lower.x, point.x);
  box.lower.y = std::min(box.lower.y, point.y);
  box.lower.z = std::min(box.lower.z, point.z);
  box.upper.x = std::max(box.upper.x, point.x);
  box.upper.y = std::max(box.upper.y, point.y);
  box.upper.z = std::max(box.upper.z, point.z);
}

void extend(BoundingBox& box, const BoundingBox& other)
{
  extend(box, other.lower);
  extend(box, other.upper);
}

double component(const Vec3& value, int axis)
{
  if (axis == 0) return value.x;
  if (axis == 1) return value.y;
  return value.z;
}

Vec3 box_centroid(const BoundingBox& box)
{
  return 0.5 * (box.lower + box.upper);
}

struct ScalarInterval {
  double lower {0.0};
  double upper {0.0};
};

constexpr std::array<std::array<double, 4>, 4> bspline_to_bezier {{
  {{1.0 / 6.0, 4.0 / 6.0, 1.0 / 6.0, 0.0}},
  {{0.0, 4.0 / 6.0, 2.0 / 6.0, 0.0}},
  {{0.0, 2.0 / 6.0, 4.0 / 6.0, 0.0}},
  {{0.0, 1.0 / 6.0, 4.0 / 6.0, 1.0 / 6.0}}}};

// Cardinal cubic B-spline controls to local monomial coefficients, ordered
// by increasing power. The patch solver can then use Horner arithmetic with
// no periodic wrapping or radius-cell search.
constexpr std::array<std::array<double, 4>, 4> bspline_to_power {{
  {{1.0 / 6.0, 4.0 / 6.0, 1.0 / 6.0, 0.0}},
  {{-0.5, 0.0, 0.5, 0.0}},
  {{0.5, -1.0, 0.5, 0.0}},
  {{-1.0 / 6.0, 0.5, -0.5, 1.0 / 6.0}}}};

struct TriangleHit {
  bool found {false};
  double t {0.0};
  double b1 {0.0};
  double b2 {0.0};
};

TriangleHit intersect_triangle(const Vec3& origin, const Vec3& direction,
  const Vec3& p0, const Vec3& p1, const Vec3& p2)
{
  const Vec3 edge1 = p1 - p0;
  const Vec3 edge2 = p2 - p0;
  const Vec3 p = cross(direction, edge2);
  const double determinant = dot(edge1, p);
  const double determinant_tolerance = 64.0
    * std::numeric_limits<double>::epsilon()
    * std::max(1.0, norm(edge1) * norm(edge2));
  if (std::abs(determinant) <= determinant_tolerance) return {};
  const double inverse = 1.0 / determinant;
  const Vec3 offset = origin - p0;
  const double b1 = dot(offset, p) * inverse;
  if (b1 < -1.0e-12 || b1 > 1.0 + 1.0e-12) return {};
  const Vec3 q = cross(offset, edge1);
  const double b2 = dot(direction, q) * inverse;
  if (b2 < -1.0e-12 || b1 + b2 > 1.0 + 1.0e-12) return {};
  return {true, dot(edge2, q) * inverse, b1, b2};
}

double point_segment_distance_squared(
  const Vec3& point, const Vec3& a, const Vec3& b)
{
  const Vec3 edge = b - a;
  const double denominator = norm_squared(edge);
  const double parameter = denominator > 0.0
    ? std::clamp(dot(point - a, edge) / denominator, 0.0, 1.0) : 0.0;
  return norm_squared(point - (a + parameter * edge));
}

double segment_segment_distance_squared(const Vec3& p0, const Vec3& p1,
  const Vec3& q0, const Vec3& q1)
{
  const Vec3 d1 = p1 - p0;
  const Vec3 d2 = q1 - q0;
  const Vec3 r = p0 - q0;
  const double a = norm_squared(d1);
  const double e = norm_squared(d2);
  const double f = dot(d2, r);
  const double epsilon = 64.0 * std::numeric_limits<double>::epsilon();
  double s = 0.0;
  double t = 0.0;
  if (a <= epsilon && e <= epsilon) return norm_squared(p0 - q0);
  if (a <= epsilon) {
    t = std::clamp(f / e, 0.0, 1.0);
  } else {
    const double c = dot(d1, r);
    if (e <= epsilon) {
      s = std::clamp(-c / a, 0.0, 1.0);
    } else {
      const double b = dot(d1, d2);
      const double denominator = a * e - b * b;
      if (std::abs(denominator) > epsilon * a * e) {
        s = std::clamp((b * f - c * e) / denominator, 0.0, 1.0);
      }
      const double nominal_t = (b * s + f) / e;
      if (nominal_t < 0.0) {
        t = 0.0;
        s = std::clamp(-c / a, 0.0, 1.0);
      } else if (nominal_t > 1.0) {
        t = 1.0;
        s = std::clamp((b - c) / a, 0.0, 1.0);
      } else {
        t = nominal_t;
      }
    }
  }
  return norm_squared((p0 + s * d1) - (q0 + t * d2));
}

double point_triangle_distance_squared(const Vec3& point,
  const Vec3& a, const Vec3& b, const Vec3& c)
{
  const Vec3 ab = b - a;
  const Vec3 ac = c - a;
  const Vec3 ap = point - a;
  const double d1 = dot(ab, ap);
  const double d2 = dot(ac, ap);
  if (d1 <= 0.0 && d2 <= 0.0) return norm_squared(ap);
  const Vec3 bp = point - b;
  const double d3 = dot(ab, bp);
  const double d4 = dot(ac, bp);
  if (d3 >= 0.0 && d4 <= d3) return norm_squared(bp);
  const double vc = d1 * d4 - d3 * d2;
  if (vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0) {
    const double v = d1 / (d1 - d3);
    return norm_squared(point - (a + v * ab));
  }
  const Vec3 cp = point - c;
  const double d5 = dot(ab, cp);
  const double d6 = dot(ac, cp);
  if (d6 >= 0.0 && d5 <= d6) return norm_squared(cp);
  const double vb = d5 * d2 - d1 * d6;
  if (vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0) {
    const double w = d2 / (d2 - d6);
    return norm_squared(point - (a + w * ac));
  }
  const double va = d3 * d6 - d5 * d4;
  if (va <= 0.0 && d4 - d3 >= 0.0 && d5 - d6 >= 0.0) {
    const double w = (d4 - d3) / ((d4 - d3) + (d5 - d6));
    return norm_squared(point - (b + w * (c - b)));
  }
  const Vec3 normal_value = cross(ab, ac);
  const double normal_squared = norm_squared(normal_value);
  if (!(normal_squared > 0.0)) {
    return std::min({point_segment_distance_squared(point, a, b),
      point_segment_distance_squared(point, b, c),
      point_segment_distance_squared(point, c, a)});
  }
  const double signed_distance = dot(ap, normal_value);
  return signed_distance * signed_distance / normal_squared;
}

double segment_triangle_distance_squared(const Vec3& segment_a,
  const Vec3& segment_b, const Vec3& a, const Vec3& b, const Vec3& c)
{
  const auto hit = intersect_triangle(segment_a, segment_b - segment_a, a, b, c);
  if (hit.found && hit.t >= 0.0 && hit.t <= 1.0) return 0.0;
  return std::min({
    point_triangle_distance_squared(segment_a, a, b, c),
    point_triangle_distance_squared(segment_b, a, b, c),
    segment_segment_distance_squared(segment_a, segment_b, a, b),
    segment_segment_distance_squared(segment_a, segment_b, b, c),
    segment_segment_distance_squared(segment_a, segment_b, c, a)});
}

} // namespace

ParametricSurfaceSample CompiledPeriodicSplineSurface::sample_parametric(
  double theta, double phi) const
{
  const auto axis_r = axis_r_.sample(phi);
  const auto axis_z = axis_z_.sample(phi);
  const auto radius = radius_.sample(theta, phi);
  const double cosine_theta = std::cos(theta);
  const double sine_theta = std::sin(theta);
  const double cosine_phi = std::cos(phi);
  const double sine_phi = std::sin(phi);
  const double cylindrical_r = axis_r.value + radius.value * cosine_theta;
  const double z = axis_z.value + radius.value * sine_theta;
  const double r_theta = radius.dtheta * cosine_theta
                         - radius.value * sine_theta;
  const double z_theta = radius.dtheta * sine_theta
                         + radius.value * cosine_theta;
  const double r_phi = axis_r.derivative + radius.dphi * cosine_theta;
  const double z_phi = axis_z.derivative + radius.dphi * sine_theta;
  return {
    {cylindrical_r * cosine_phi, cylindrical_r * sine_phi, z},
    {r_theta * cosine_phi, r_theta * sine_phi, z_theta},
    {r_phi * cosine_phi - cylindrical_r * sine_phi,
      r_phi * sine_phi + cylindrical_r * cosine_phi, z_phi}};
}

ParametricSurfaceSample CompiledPeriodicSplineSurface::sample_patch_parametric(
  const PeriodicPatch& patch, double theta, double phi) const
{
  const double theta_scale = static_cast<double>(data_.n_theta) / two_pi;
  const double phi_scale = static_cast<double>(data_.n_phi
    * static_cast<std::size_t>(data_.n_field_periods)) / two_pi;
  const double u = (theta - patch.uv.theta_min) * theta_scale;
  const double v = (phi - patch.uv.phi_min) * phi_scale;

  std::array<double, 4> phi_polynomial {};
  std::array<double, 4> phi_derivative {};
  for (std::size_t p = 0; p < 4; ++p) {
    const double c0 = patch.radius_power[4 * p];
    const double c1 = patch.radius_power[4 * p + 1];
    const double c2 = patch.radius_power[4 * p + 2];
    const double c3 = patch.radius_power[4 * p + 3];
    phi_polynomial[p] = ((c3 * v + c2) * v + c1) * v + c0;
    phi_derivative[p] = (3.0 * c3 * v + 2.0 * c2) * v + c1;
  }
  const double radius_value = ((phi_polynomial[3] * u
    + phi_polynomial[2]) * u + phi_polynomial[1]) * u
    + phi_polynomial[0];
  const double radius_dtheta = ((3.0 * phi_polynomial[3] * u
    + 2.0 * phi_polynomial[2]) * u + phi_polynomial[1]) * theta_scale;
  const double radius_dphi = (((phi_derivative[3] * u
    + phi_derivative[2]) * u + phi_derivative[1]) * u
    + phi_derivative[0]) * phi_scale;

  double axis_r_value = 0.0;
  double axis_z_value = 0.0;
  double axis_r_derivative = 0.0;
  double axis_z_derivative = 0.0;
  if (axis_patch_aligned_) {
    const std::size_t physical_phi_count = data_.n_phi
      * static_cast<std::size_t>(data_.n_field_periods);
    const std::size_t phi_patch = std::min(physical_phi_count - 1,
      static_cast<std::size_t>(patch.uv.phi_min * phi_scale + 0.5));
    const auto& axis_power = axis_patch_power_[phi_patch];
    axis_r_value = ((axis_power[3] * v + axis_power[2]) * v
      + axis_power[1]) * v + axis_power[0];
    axis_z_value = ((axis_power[7] * v + axis_power[6]) * v
      + axis_power[5]) * v + axis_power[4];
    axis_r_derivative = (3.0 * axis_power[3] * v
      + 2.0 * axis_power[2]) * v + axis_power[1];
    axis_z_derivative = (3.0 * axis_power[7] * v
      + 2.0 * axis_power[6]) * v + axis_power[5];
    axis_r_derivative *= phi_scale;
    axis_z_derivative *= phi_scale;
  } else {
    const double axis_scale = static_cast<double>(
      data_.axis_r_coefficients.size()
      * static_cast<std::size_t>(data_.n_field_periods)) / two_pi;
    const double axis_coordinate = phi * axis_scale;
    const long axis_global_cell = static_cast<long>(std::floor(axis_coordinate));
    const double axis_u = axis_coordinate - static_cast<double>(axis_global_cell);
    const double axis_u2 = axis_u * axis_u;
    const double axis_u3 = axis_u2 * axis_u;
    const double one_minus_axis_u = 1.0 - axis_u;
    const std::array<double, 4> axis_basis {{
      one_minus_axis_u * one_minus_axis_u * one_minus_axis_u / 6.0,
      (3.0 * axis_u3 - 6.0 * axis_u2 + 4.0) / 6.0,
      (-3.0 * axis_u3 + 3.0 * axis_u2 + 3.0 * axis_u + 1.0) / 6.0,
      axis_u3 / 6.0}};
    const std::array<double, 4> axis_derivative_basis {{
      -0.5 * one_minus_axis_u * one_minus_axis_u,
      1.5 * axis_u2 - 2.0 * axis_u,
      -1.5 * axis_u2 + axis_u + 0.5,
      0.5 * axis_u2}};
    for (long a = 0; a < 4; ++a) {
      const std::size_t control = wrap_index(axis_global_cell + a - 1,
        data_.axis_r_coefficients.size());
      const std::size_t ai = static_cast<std::size_t>(a);
      axis_r_value += data_.axis_r_coefficients[control] * axis_basis[ai];
      axis_z_value += data_.axis_z_coefficients[control] * axis_basis[ai];
      axis_r_derivative += data_.axis_r_coefficients[control]
                           * axis_derivative_basis[ai] * axis_scale;
      axis_z_derivative += data_.axis_z_coefficients[control]
                           * axis_derivative_basis[ai] * axis_scale;
    }
  }

  const double cosine_theta = std::cos(theta);
  const double sine_theta = std::sin(theta);
  const double cosine_phi = std::cos(phi);
  const double sine_phi = std::sin(phi);
  const double cylindrical_r = axis_r_value + radius_value * cosine_theta;
  const double z = axis_z_value + radius_value * sine_theta;
  const double r_theta = radius_dtheta * cosine_theta
                         - radius_value * sine_theta;
  const double z_theta = radius_dtheta * sine_theta
                         + radius_value * cosine_theta;
  const double r_phi = axis_r_derivative + radius_dphi * cosine_theta;
  const double z_phi = axis_z_derivative + radius_dphi * sine_theta;
  return {
    {cylindrical_r * cosine_phi, cylindrical_r * sine_phi, z},
    {r_theta * cosine_phi, r_theta * sine_phi, z_theta},
    {r_phi * cosine_phi - cylindrical_r * sine_phi,
      r_phi * sine_phi + cylindrical_r * cosine_phi, z_phi}};
}

void CompiledPeriodicSplineSurface::build_periodic_patches()
{
  const std::size_t physical_phi_count = data_.n_phi
    * static_cast<std::size_t>(data_.n_field_periods);
  constexpr std::size_t patch_stride = 1;
  const std::size_t theta_patch_count =
    (data_.n_theta + patch_stride - 1) / patch_stride;
  const std::size_t phi_patch_count =
    (physical_phi_count + patch_stride - 1) / patch_stride;
  const std::size_t patch_count = theta_patch_count * phi_patch_count;
  axis_patch_aligned_ = data_.axis_r_coefficients.size() == data_.n_phi;
  axis_patch_power_.clear();
  if (axis_patch_aligned_) {
    axis_patch_power_.resize(physical_phi_count);
    for (std::size_t j = 0; j < physical_phi_count; ++j) {
      const std::size_t cell = j % data_.n_phi;
      for (std::size_t p = 0; p < 4; ++p) {
        double r_coefficient = 0.0;
        double z_coefficient = 0.0;
        for (std::size_t a = 0; a < 4; ++a) {
          const std::size_t control = wrap_index(
            static_cast<long>(cell) + static_cast<long>(a) - 1,
            data_.axis_r_coefficients.size());
          r_coefficient += bspline_to_power[p][a]
                           * data_.axis_r_coefficients[control];
          z_coefficient += bspline_to_power[p][a]
                           * data_.axis_z_coefficients[control];
        }
        axis_patch_power_[j][p] = r_coefficient;
        axis_patch_power_[j][4 + p] = z_coefficient;
      }
    }
  }
  patches_.clear();
  patches_.reserve(patch_count);
  const double theta_base_step = two_pi / static_cast<double>(data_.n_theta);
  const double phi_base_step = two_pi / static_cast<double>(physical_phi_count);
  const double rounding = std::max(
    64.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length,
    1.0e-12 * data_.characteristic_length);
  const auto axis_r_bounds = std::minmax_element(
    data_.axis_r_coefficients.begin(), data_.axis_r_coefficients.end());
  const ScalarInterval global_axis_r_interval {
    *axis_r_bounds.first, *axis_r_bounds.second};
  const double axis_scale = static_cast<double>(
    data_.axis_r_coefficients.size()
    * static_cast<std::size_t>(data_.n_field_periods)) / two_pi;
  double global_axis_second_bound = 0.0;
  for (std::size_t center = 0;
       center < data_.axis_r_coefficients.size(); ++center) {
    const std::size_t previous = wrap_index(
      static_cast<long>(center) - 1, data_.axis_r_coefficients.size());
    const std::size_t next = wrap_index(
      static_cast<long>(center) + 1, data_.axis_r_coefficients.size());
    global_axis_second_bound = std::max(global_axis_second_bound, std::hypot(
      data_.axis_r_coefficients[next]
        - 2.0 * data_.axis_r_coefficients[center]
        + data_.axis_r_coefficients[previous],
      data_.axis_z_coefficients[next]
        - 2.0 * data_.axis_z_coefficients[center]
        + data_.axis_z_coefficients[previous]));
  }
  global_axis_second_bound *= axis_scale * axis_scale;

  for (std::size_t patch_i = 0; patch_i < theta_patch_count; ++patch_i) {
    const std::size_t i = patch_i * patch_stride;
    const std::size_t theta_span_cells = std::min(
      patch_stride, data_.n_theta - i);
    const double theta0 = theta_base_step * static_cast<double>(i);
    const double theta1 = theta_base_step
      * static_cast<double>(i + theta_span_cells);
    for (std::size_t patch_j = 0; patch_j < phi_patch_count; ++patch_j) {
      const std::size_t j = patch_j * patch_stride;
      const std::size_t phi_span_cells = std::min(
        patch_stride, physical_phi_count - j);
      const double phi0 = phi_base_step * static_cast<double>(j);
      const double phi1 = phi_base_step
        * static_cast<double>(j + phi_span_cells);
      const double theta_step = theta1 - theta0;
      const double phi_step = phi1 - phi0;
      PeriodicPatch patch;
      patch.uv = {theta0, theta1, phi0, phi1};
      for (std::size_t p = 0; p < 4; ++p) {
        for (std::size_t q = 0; q < 4; ++q) {
          double coefficient = 0.0;
          for (std::size_t control_a = 0; control_a < 4; ++control_a) {
            const std::size_t control_i = wrap_index(
              static_cast<long>(i) + static_cast<long>(control_a) - 1,
              data_.n_theta);
            for (std::size_t control_b = 0; control_b < 4; ++control_b) {
              const std::size_t control_j = wrap_index(
                static_cast<long>(j) + static_cast<long>(control_b) - 1,
                data_.n_phi);
              coefficient += bspline_to_power[p][control_a]
                             * bspline_to_power[q][control_b]
                             * data_.radius_coefficients[
                               control_i * data_.n_phi + control_j];
            }
          }
          patch.radius_power[4 * p + q] = coefficient;
        }
      }
      patch.proxy_corners = {{
        sample_parametric(theta0, phi0).position,
        sample_parametric(theta1, phi0).position,
        sample_parametric(theta1, phi1).position,
        sample_parametric(theta0, phi1).position}};
      patch.proxy_bbox = empty_box();
      for (const auto& corner : patch.proxy_corners) {
        extend(patch.proxy_bbox, corner);
      }
      ScalarInterval radius_interval {
        std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity()};
      double local_theta_derivative_bound = 0.0;
      double local_phi_derivative_bound = 0.0;
      for (std::size_t cell_di = 0; cell_di < theta_span_cells; ++cell_di) {
        const std::size_t cell_i = (i + cell_di) % data_.n_theta;
        for (std::size_t cell_dj = 0; cell_dj < phi_span_cells; ++cell_dj) {
          const std::size_t cell_j = (j + cell_dj) % data_.n_phi;
          const std::size_t local_flat = cell_i * data_.n_phi + cell_j;
          local_theta_derivative_bound = std::max(
            local_theta_derivative_bound,
            radius_local_theta_derivative_bounds_[local_flat]);
          local_phi_derivative_bound = std::max(
            local_phi_derivative_bound,
            radius_local_phi_derivative_bounds_[local_flat]);
          for (std::size_t a = 0; a < 4; ++a) {
            for (std::size_t b = 0; b < 4; ++b) {
              double value = 0.0;
              for (std::size_t control_a = 0; control_a < 4; ++control_a) {
                const std::size_t control_i = wrap_index(
                  static_cast<long>(cell_i)
                    + static_cast<long>(control_a) - 1,
                  data_.n_theta);
                for (std::size_t control_b = 0; control_b < 4; ++control_b) {
                  const std::size_t control_j = wrap_index(
                    static_cast<long>(cell_j)
                      + static_cast<long>(control_b) - 1,
                    data_.n_phi);
                  value += bspline_to_bezier[a][control_a]
                           * bspline_to_bezier[b][control_b]
                           * data_.radius_coefficients[
                             control_i * data_.n_phi + control_j];
                }
              }
              radius_interval.lower = std::min(radius_interval.lower, value);
              radius_interval.upper = std::max(radius_interval.upper, value);
            }
          }
        }
      }
      double radius_theta_second_bound = 0.0;
      double radius_phi_second_bound = 0.0;
      for (long di = -2;
           di <= static_cast<long>(theta_span_cells) + 1; ++di) {
        const std::size_t previous_i = wrap_index(
          static_cast<long>(i) + di - 1, data_.n_theta);
        const std::size_t center_i = wrap_index(
          static_cast<long>(i) + di, data_.n_theta);
        const std::size_t next_i = wrap_index(
          static_cast<long>(i) + di + 1, data_.n_theta);
        for (long dj = -2;
             dj <= static_cast<long>(phi_span_cells) + 1; ++dj) {
          const std::size_t previous_j = wrap_index(
            static_cast<long>(j) + dj - 1, data_.n_phi);
          const std::size_t center_j = wrap_index(
            static_cast<long>(j) + dj, data_.n_phi);
          const std::size_t next_j = wrap_index(
            static_cast<long>(j) + dj + 1, data_.n_phi);
          radius_theta_second_bound = std::max(
            radius_theta_second_bound, std::abs(
              data_.radius_coefficients[next_i * data_.n_phi + center_j]
              - 2.0 * data_.radius_coefficients[
                center_i * data_.n_phi + center_j]
              + data_.radius_coefficients[
                previous_i * data_.n_phi + center_j]));
          radius_phi_second_bound = std::max(
            radius_phi_second_bound, std::abs(
              data_.radius_coefficients[center_i * data_.n_phi + next_j]
              - 2.0 * data_.radius_coefficients[
                center_i * data_.n_phi + center_j]
              + data_.radius_coefficients[
                center_i * data_.n_phi + previous_j]));
        }
      }
      const double theta_scale = static_cast<double>(data_.n_theta) / two_pi;
      const double phi_scale = static_cast<double>(physical_phi_count) / two_pi;
      radius_theta_second_bound *= theta_scale * theta_scale;
      radius_phi_second_bound *= phi_scale * phi_scale;
      const double radius_magnitude_bound = std::max(
        std::abs(radius_interval.lower), std::abs(radius_interval.upper));
      const double theta_second_bound = radius_theta_second_bound
        + 2.0 * local_theta_derivative_bound + radius_magnitude_bound;
      const double cylindrical_r_upper = std::max(
        std::abs(global_axis_r_interval.lower),
        std::abs(global_axis_r_interval.upper)) + radius_magnitude_bound;
      const double phi_second_bound = global_axis_second_bound
        + 2.0 * radius_phi_second_bound + cylindrical_r_upper
        + 2.0 * (axis_derivative_bound_ + local_phi_derivative_bound);
      const double proxy_error = theta_step * theta_step
                                   * theta_second_bound / 8.0
                                 + phi_step * phi_step
                                   * phi_second_bound / 8.0
                                 + 0.25 * norm(patch.proxy_corners[0]
                                   - patch.proxy_corners[1]
                                   + patch.proxy_corners[2]
                                   - patch.proxy_corners[3])
                                 + rounding;
      patch.conservative_bbox = {
        {std::nextafter(patch.proxy_bbox.lower.x - proxy_error,
           -std::numeric_limits<double>::infinity()),
          std::nextafter(patch.proxy_bbox.lower.y - proxy_error,
            -std::numeric_limits<double>::infinity()),
          std::nextafter(patch.proxy_bbox.lower.z - proxy_error,
            -std::numeric_limits<double>::infinity())},
        {std::nextafter(patch.proxy_bbox.upper.x + proxy_error,
           std::numeric_limits<double>::infinity()),
          std::nextafter(patch.proxy_bbox.upper.y + proxy_error,
            std::numeric_limits<double>::infinity()),
          std::nextafter(patch.proxy_bbox.upper.z + proxy_error,
            std::numeric_limits<double>::infinity())}};
      patch.proxy_error_bound = proxy_error;
      const std::size_t previous_i =
        (patch_i + theta_patch_count - 1) % theta_patch_count;
      const std::size_t next_i = (patch_i + 1) % theta_patch_count;
      const std::size_t previous_j =
        (patch_j + phi_patch_count - 1) % phi_patch_count;
      const std::size_t next_j = (patch_j + 1) % phi_patch_count;
      patch.neighbors = {{
        static_cast<std::int32_t>(previous_i * phi_patch_count + patch_j),
        static_cast<std::int32_t>(next_i * phi_patch_count + patch_j),
        static_cast<std::int32_t>(patch_i * phi_patch_count + previous_j),
        static_cast<std::int32_t>(patch_i * phi_patch_count + next_j)}};
      patches_.push_back(patch);
    }
  }

  patch_indices_.resize(patches_.size());
  std::iota(patch_indices_.begin(), patch_indices_.end(), 0U);
  patch_bvh_.clear();
  patch_bvh_.reserve(2 * patches_.size());
  if (!patches_.empty()) {
    (void) build_patch_bvh_node(0U,
      static_cast<std::uint32_t>(patches_.size()));
  }
}

std::uint32_t CompiledPeriodicSplineSurface::build_patch_bvh_node(
  std::uint32_t first, std::uint32_t last)
{
  const std::uint32_t node_index = static_cast<std::uint32_t>(patch_bvh_.size());
  patch_bvh_.push_back({});
  BoundingBox bounds = empty_box();
  BoundingBox centroids = empty_box();
  for (std::uint32_t i = first; i < last; ++i) {
    const auto& box = patches_[patch_indices_[i]].conservative_bbox;
    extend(bounds, box);
    extend(centroids, box_centroid(box));
  }
  patch_bvh_[node_index].bbox = bounds;
  const std::uint32_t count = last - first;
  constexpr std::uint32_t leaf_size = 4;
  if (count <= leaf_size) {
    patch_bvh_[node_index].first = first;
    patch_bvh_[node_index].count = static_cast<std::uint16_t>(count);
    return node_index;
  }

  const Vec3 extent = centroids.upper - centroids.lower;
  const int axis = extent.y > extent.x ? (extent.z > extent.y ? 2 : 1)
                                      : (extent.z > extent.x ? 2 : 0);
  const std::uint32_t middle = first + count / 2;
  std::nth_element(patch_indices_.begin() + first,
    patch_indices_.begin() + middle, patch_indices_.begin() + last,
    [&](std::uint32_t lhs, std::uint32_t rhs) {
      return component(box_centroid(patches_[lhs].conservative_bbox), axis)
             < component(box_centroid(patches_[rhs].conservative_bbox), axis);
    });
  const std::uint32_t left = build_patch_bvh_node(first, middle);
  const std::uint32_t right = build_patch_bvh_node(middle, last);
  patch_bvh_[node_index].left = left;
  patch_bvh_[node_index].right = right;
  return node_index;
}

DistanceResult CompiledPeriodicSplineSurface::distance_general_periodic_interval_precursor(
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
  diagnostics.solver_path = SolverPath::general_periodic_certified;
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
    options.absolute_t_tolerance,
    16.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length);

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
    const double half_width = 0.5 * (interval.b - interval.a);
    const Vec3 midpoint_point = origin + midpoint * u;
    const auto local = surface_.local_coordinates(midpoint_point);
    ++diagnostics.function_evaluations;
    const double fm = local.rho - local.surface_radius.value;

    // R is one-Lipschitz along a unit ray. Away from R=0, |dphi/dt| <= 1/R.
    // The moving reference axis then gives a conservative Lipschitz bound on
    // q=(R-R_axis, z-Z_axis), rho=|q|, theta, and finally F=rho-r(theta,phi).
    const double R_lower = local.R - half_width;
    bool certified = false;
    bool regular_coordinates = false;
    if (R_lower > data_.coordinate_singularity_tolerance) {
      const double phi_variation_bound = half_width / R_lower;
      double axis_bound = axis_derivative_bound_;
      const double axis_cell_width = two_pi
        / static_cast<double>(data_.axis_r_coefficients.size()
          * static_cast<std::size_t>(data_.n_field_periods));
      if (phi_variation_bound <= axis_cell_width) {
        axis_bound = axis_local_derivative_bounds_[periodic_cell(
          local.phi, data_.axis_r_coefficients.size(),
          data_.n_field_periods)];
      }
      const double q_derivative_bound = 1.0 + axis_bound / R_lower;
      const double rho_lower = local.rho - q_derivative_bound * half_width;
      const double rho_upper = local.rho + q_derivative_bound * half_width;
      if (rho_upper < radius_coefficient_min_
                          - options.absolute_f_tolerance
          || rho_lower > radius_coefficient_max_
                           + options.absolute_f_tolerance) {
        ++diagnostics.certified_excluded_intervals;
        certified = true;
      }
      if (rho_lower > data_.coordinate_singularity_tolerance) {
        regular_coordinates = true;
        double theta_bound = radius_theta_derivative_bound_;
        double phi_bound = radius_phi_derivative_bound_;
        const double theta_variation_bound =
          q_derivative_bound * half_width / rho_lower;
        const double theta_cell_width = two_pi
          / static_cast<double>(data_.n_theta);
        const double phi_cell_width = two_pi
          / static_cast<double>(data_.n_phi
            * static_cast<std::size_t>(data_.n_field_periods));
        if (theta_variation_bound <= theta_cell_width
            && phi_variation_bound <= phi_cell_width) {
          const std::size_t theta_cell = periodic_cell(
            local.theta, data_.n_theta, 1);
          const std::size_t phi_cell = periodic_cell(
            local.phi, data_.n_phi, data_.n_field_periods);
          const std::size_t flat = theta_cell * data_.n_phi + phi_cell;
          theta_bound = radius_local_theta_derivative_bounds_[flat];
          phi_bound = radius_local_phi_derivative_bounds_[flat];
        }
        const double derivative_bound = q_derivative_bound
          + theta_bound * q_derivative_bound / rho_lower
          + phi_bound / R_lower;
        if (!certified
            && std::abs(fm) > derivative_bound * half_width
                              + options.absolute_f_tolerance) {
          ++diagnostics.certified_excluded_intervals;
          certified = true;
        }
      }
    }
    if (certified) continue;

    if (interval.b - interval.a <= isolation_width) {
      if (std::abs(interval.fa) <= options.absolute_f_tolerance) {
        return DistanceResult {true, interval.a, RootKind::sampled_zero,
          std::abs(interval.fa), diagnostics};
      }
      if (std::abs(interval.fb) <= options.absolute_f_tolerance) {
        return DistanceResult {true, interval.b, RootKind::sampled_zero,
          std::abs(interval.fb), diagnostics};
      }
      const bool midpoint_root = std::abs(fm) <= options.absolute_f_tolerance;
      const bool left_bracket = std::signbit(interval.fa) != std::signbit(fm);
      const bool right_bracket = std::signbit(fm) != std::signbit(interval.fb);
      if (midpoint_root && !left_bracket && !right_bracket) {
        return DistanceResult {true, midpoint, RootKind::stationary_tangent,
          std::abs(fm), diagnostics};
      }
      if (!left_bracket && !right_bracket) {
        // The leaf can sit immediately before a crossing, where a global
        // Lipschitz exclusion is inconclusive even though the leaf itself is
        // root-free. Adjudicate this tiny, regular-coordinate interval with a
        // focused reference scan; only singular leaves require the global
        // oracle.
        if (regular_coordinates) {
          RootSearchOptions local_options = options;
          local_options.initial_subdivisions = 8;
          local_options.max_refinement_levels = 2;
          local_options.require_refinement_stability = false;
          const auto derivative = [&](double t) {
            return surface_.directional_derivative(origin + t * u, u);
          };
          const auto local_oracle = find_nearest_root_reference(
            function, derivative, interval.a, interval.b, local_options);
          if (local_oracle.found) {
            return DistanceResult {true, local_oracle.root.t,
              local_oracle.root.kind, local_oracle.root.residual, diagnostics};
          }
          continue;
        }
        ++diagnostics.unresolved_intervals;
        return fallback(
          SolverFallbackReason::unresolved_tangent_or_degenerate_interval);
      }
      double a = left_bracket ? interval.a : midpoint;
      double b = left_bracket ? midpoint : interval.b;
      double fa = left_bracket ? interval.fa : fm;
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
      return DistanceResult {true, x, RootKind::sign_change,
        std::abs(fx), diagnostics};
    }

    ++diagnostics.subdivided_intervals;
    // LIFO order deliberately visits the nearer (left) interval first.
    stack.push_back({midpoint, interval.b, fm, interval.fb});
    stack.push_back({interval.a, midpoint, interval.fa, fm});
  }

  return DistanceResult {false, std::numeric_limits<double>::infinity(),
    RootKind::sign_change, std::numeric_limits<double>::infinity(),
    diagnostics};
}

DistanceResult CompiledPeriodicSplineSurface::distance_general_periodic(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0) || !std::isfinite(direction_norm)) {
    throw std::invalid_argument("Ray direction must be finite and non-zero");
  }
  const Vec3 ray_direction = direction / direction_norm;
  RootSearchDiagnostics diagnostics;
  diagnostics.solver_path = SolverPath::general_periodic_certified;
  diagnostics.fallback_reason = SolverFallbackReason::none;
  if (patch_bvh_.empty()) {
    return {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      diagnostics};
  }
  const std::array<double, 3> ray_origin {{origin.x, origin.y, origin.z}};
  const std::array<double, 3> ray_components {{
    ray_direction.x, ray_direction.y, ray_direction.z}};
  std::array<double, 3> inverse_direction {};
  for (std::size_t axis = 0; axis < 3; ++axis) {
    inverse_direction[axis] = std::abs(ray_components[axis]) > 1.0e-15
      ? 1.0 / ray_components[axis]
      : std::numeric_limits<double>::infinity();
  }
  const auto ray_box_interval = [&](const BoundingBox& box)
    -> std::optional<RayInterval> {
    const std::array<double, 3> lower {{
      box.lower.x, box.lower.y, box.lower.z}};
    const std::array<double, 3> upper {{
      box.upper.x, box.upper.y, box.upper.z}};
    double enter = -std::numeric_limits<double>::infinity();
    double exit = std::numeric_limits<double>::infinity();
    for (std::size_t axis = 0; axis < 3; ++axis) {
      if (!std::isfinite(inverse_direction[axis])) {
        if (ray_origin[axis] < lower[axis]
            || ray_origin[axis] > upper[axis]) return std::nullopt;
        continue;
      }
      double a = (lower[axis] - ray_origin[axis]) * inverse_direction[axis];
      double b = (upper[axis] - ray_origin[axis]) * inverse_direction[axis];
      if (a > b) std::swap(a, b);
      enter = std::max(enter, a);
      exit = std::min(exit, b);
      if (enter > exit) return std::nullopt;
    }
    return RayInterval {enter, exit};
  };
  const auto root_interval = ray_box_interval(patch_bvh_.front().bbox);
  if (!root_interval || root_interval->exit < 0.0) {
    return {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      diagnostics};
  }

  const double crossing_push = std::max({
    options.absolute_t_tolerance * 64.0,
    options.absolute_f_tolerance * 8.0,
    std::numeric_limits<double>::epsilon()
      * data_.characteristic_length * 64.0});
  const double minimum_t = coincident ? crossing_push : 0.0;
  Vec3 basis1;
  if (std::abs(ray_direction.z) < 0.9) {
    basis1 = normalized(cross(ray_direction, Vec3 {0.0, 0.0, 1.0}));
  } else {
    basis1 = normalized(cross(ray_direction, Vec3 {0.0, 1.0, 0.0}));
  }
  const Vec3 basis2 = cross(ray_direction, basis1);
  const double projected_tolerance = std::max(
    options.absolute_f_tolerance,
    64.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length);

  struct StackEntry {
    std::uint32_t node {0};
    double near_t {0.0};
  };
  std::array<StackEntry, 128> stack {};
  std::size_t stack_size = 0;
  stack[stack_size++] = {0U, root_interval->enter};
  double best_t = std::numeric_limits<double>::infinity();
  double best_residual = std::numeric_limits<double>::infinity();
  std::uint32_t best_patch = std::numeric_limits<std::uint32_t>::max();
  bool best_tangent = false;
  std::uint64_t candidate_count = 0;
  std::uint64_t ray_newton_iterations = 0;

  const auto solve_seed = [&](const PeriodicPatch& patch, std::uint32_t patch_id,
                            double theta_seed, double phi_seed,
                            bool& needs_subdivision) {
    double theta = std::clamp(
      theta_seed, patch.uv.theta_min, patch.uv.theta_max);
    double phi = std::clamp(phi_seed, patch.uv.phi_min, patch.uv.phi_max);
    const double theta_span = patch.uv.theta_max - patch.uv.theta_min;
    const double phi_span = patch.uv.phi_max - patch.uv.phi_min;
    double residual = std::numeric_limits<double>::infinity();
    double previous_residual = std::numeric_limits<double>::infinity();
    int stagnant_iterations = 0;
    constexpr int maximum_iterations = 10;
    int iterations = 0;
    for (; iterations < maximum_iterations; ++iterations) {
      const auto sample = sample_patch_parametric(patch, theta, phi);
      const Vec3 offset = sample.position - origin;
      const double h1 = dot(basis1, offset);
      const double h2 = dot(basis2, offset);
      residual = std::hypot(h1, h2);
      if (residual <= projected_tolerance) break;
      if (residual >= 0.999 * previous_residual) {
        ++stagnant_iterations;
        if (stagnant_iterations >= 1) break;
      } else {
        stagnant_iterations = 0;
      }
      previous_residual = residual;
      const double j11 = dot(basis1, sample.dtheta);
      const double j12 = dot(basis1, sample.dphi);
      const double j21 = dot(basis2, sample.dtheta);
      const double j22 = dot(basis2, sample.dphi);
      const double determinant = j11 * j22 - j12 * j21;
      const double jacobian_scale = std::max(
        1.0, std::hypot(j11, j21) * std::hypot(j12, j22));
      double delta_theta = 0.0;
      double delta_phi = 0.0;
      if (std::abs(determinant)
          <= 128.0 * std::numeric_limits<double>::epsilon()
               * jacobian_scale) {
        add_performance_counter(PerformanceCounter::tangent_or_grazing_cases);
        needs_subdivision = true;
        const double damping = 64.0
          * std::numeric_limits<double>::epsilon() * jacobian_scale;
        const double a11 = j11 * j11 + j21 * j21 + damping;
        const double a12 = j11 * j12 + j21 * j22;
        const double a22 = j12 * j12 + j22 * j22 + damping;
        const double rhs1 = -(j11 * h1 + j21 * h2);
        const double rhs2 = -(j12 * h1 + j22 * h2);
        const double normal_determinant = a11 * a22 - a12 * a12;
        if (!(std::abs(normal_determinant)
              > std::numeric_limits<double>::epsilon()
                  * std::max(1.0, a11 * a22))) break;
        delta_theta = (rhs1 * a22 - rhs2 * a12) / normal_determinant;
        delta_phi = (a11 * rhs2 - a12 * rhs1) / normal_determinant;
      } else {
        delta_theta = (-h1 * j22 + h2 * j12) / determinant;
        delta_phi = (-j11 * h2 + j21 * h1) / determinant;
      }
      const double scale = std::max({1.0,
        std::abs(delta_theta) / (0.5 * theta_span),
        std::abs(delta_phi) / (0.5 * phi_span)});
      delta_theta /= scale;
      delta_phi /= scale;
      theta = std::clamp(
        theta + delta_theta, patch.uv.theta_min, patch.uv.theta_max);
      phi = std::clamp(phi + delta_phi, patch.uv.phi_min, patch.uv.phi_max);
    }
    ray_newton_iterations += static_cast<std::uint64_t>(iterations);
    add_performance_counter(
      PerformanceCounter::newton_iterations,
      static_cast<std::uint64_t>(iterations));
    if (residual > projected_tolerance) {
      add_performance_counter(PerformanceCounter::newton_failures);
      return false;
    }
    const auto sample = sample_patch_parametric(patch, theta, phi);
    const double t = dot(ray_direction, sample.position - origin);
    if (!(t > minimum_t) || !(t < best_t + options.absolute_t_tolerance)) {
      add_performance_counter(PerformanceCounter::rejected_roots);
      return false;
    }
    const Vec3 unnormalized_normal = cross(sample.dtheta, sample.dphi);
    const double normal_magnitude = norm(unnormalized_normal);
    if (normal_magnitude > 0.0) {
      const double incidence = std::abs(
        dot(unnormalized_normal, ray_direction)) / normal_magnitude;
      record_incidence(incidence);
      if (incidence < 0.25) {
        needs_subdivision = true;
        add_performance_counter(PerformanceCounter::tangent_or_grazing_cases);
      }
      if (incidence < 1.0e-4) {
        return false;
      }
    }
    const double seam_tolerance = 32.0 * std::numeric_limits<double>::epsilon();
    if (theta < patch.uv.theta_min - seam_tolerance
        || theta > patch.uv.theta_max + seam_tolerance
        || phi < patch.uv.phi_min - seam_tolerance
        || phi > patch.uv.phi_max + seam_tolerance) {
      add_performance_counter(PerformanceCounter::rejected_roots);
      return false;
    }
    if (std::abs(t - best_t) <= options.duplicate_t_multiplier
                                  * options.absolute_t_tolerance) {
      add_performance_counter(PerformanceCounter::deduplicated_roots);
      if (patch_id >= best_patch) return true;
    }
    best_t = t;
    best_residual = residual;
    best_patch = patch_id;
    best_tangent = false;
    return true;
  };

  const auto solve_tangent_interval = [&](const PeriodicPatch& patch,
                                        std::uint32_t patch_id,
                                        double lower_t, double upper_t,
                                        bool& stationary_bracket,
                                        bool& possible_crossings) {
    if (!(upper_t > lower_t)) return false;
    double value_a = evaluate(origin + lower_t * ray_direction);
    const double value_b = evaluate(origin + upper_t * ray_direction);
    double bracket_a = lower_t;
    double bracket_b = upper_t;
    double bracket_value_a = value_a;
    bool crossing_bracket = false;
    if (std::isfinite(value_a) && std::isfinite(value_b)) {
      const double angular_span = std::max(
        patch.uv.theta_max - patch.uv.theta_min,
        patch.uv.phi_max - patch.uv.phi_min);
      const int local_scan_segments = std::clamp(
        8 * static_cast<int>(std::ceil(angular_span / 0.1)), 8, 64);
      double previous_t = lower_t;
      double previous_value = value_a;
      for (int segment = 1; segment <= local_scan_segments; ++segment) {
        const double current_t = lower_t
          + (upper_t - lower_t) * static_cast<double>(segment)
              / static_cast<double>(local_scan_segments);
        const double current_value = segment == local_scan_segments
          ? value_b : evaluate(origin + current_t * ray_direction);
        add_performance_counter(PerformanceCounter::local_subdivision_nodes);
        if (std::signbit(previous_value) != std::signbit(current_value)
            && std::abs(previous_value) > options.absolute_f_tolerance
            && std::abs(current_value) > options.absolute_f_tolerance) {
          bracket_a = previous_t;
          bracket_b = current_t;
          bracket_value_a = previous_value;
          crossing_bracket = true;
          break;
        }
        previous_t = current_t;
        previous_value = current_value;
      }
    }
    bool stationary_contact = false;
    if (crossing_bracket) {
      stationary_bracket = true;
      possible_crossings = true;
      double a = bracket_a;
      double b = bracket_b;
      value_a = bracket_value_a;
      for (int iteration = 0; iteration < 64; ++iteration) {
        add_performance_counter(PerformanceCounter::local_subdivision_nodes);
        const double midpoint = a + 0.5 * (b - a);
        const double value_mid = evaluate(origin + midpoint * ray_direction);
        if (b - a <= options.absolute_t_tolerance
                          + options.relative_t_tolerance
                            * std::max(std::abs(a), std::abs(b))) {
          a = midpoint;
          b = midpoint;
          break;
        }
        if (std::signbit(value_a) != std::signbit(value_mid)) {
          b = midpoint;
        } else {
          a = midpoint;
          value_a = value_mid;
        }
      }
      const double root_t = 0.5 * (a + b);
      lower_t = root_t;
      upper_t = root_t;
    } else {
      double derivative_a = surface_.directional_derivative(
        origin + lower_t * ray_direction, ray_direction);
      double derivative_b = surface_.directional_derivative(
        origin + upper_t * ray_direction, ray_direction);
      if (!(std::isfinite(derivative_a) && std::isfinite(derivative_b)
            && std::signbit(derivative_a) != std::signbit(derivative_b))) {
        return false;
      }
      stationary_contact = true;
      stationary_bracket = true;
      double a = lower_t;
      double b = upper_t;
      for (int iteration = 0; iteration < 20; ++iteration) {
        add_performance_counter(PerformanceCounter::local_subdivision_nodes);
        const double midpoint = a + 0.5 * (b - a);
        const double derivative_mid = surface_.directional_derivative(
          origin + midpoint * ray_direction, ray_direction);
        if (std::signbit(derivative_a) != std::signbit(derivative_mid)) {
          b = midpoint;
          derivative_b = derivative_mid;
        } else {
          a = midpoint;
          derivative_a = derivative_mid;
        }
      }
      const double provisional_t = 0.5 * (a + b);
      const double provisional_value =
        evaluate(origin + provisional_t * ray_direction);
      const double provisional_residual = std::abs(provisional_value);
      if (provisional_residual
          > 100.0 * options.tangent_residual_multiplier
                    * options.absolute_f_tolerance) {
        const double lower_value = evaluate(origin + lower_t * ray_direction);
        const double upper_value = evaluate(origin + upper_t * ray_direction);
        possible_crossings =
          std::signbit(lower_value) != std::signbit(provisional_value)
          || std::signbit(provisional_value) != std::signbit(upper_value);
        return false;
      }
      for (int iteration = 20; iteration < 64; ++iteration) {
        add_performance_counter(PerformanceCounter::local_subdivision_nodes);
        const double midpoint = a + 0.5 * (b - a);
        const double derivative_mid = surface_.directional_derivative(
          origin + midpoint * ray_direction, ray_direction);
        if (std::signbit(derivative_a) != std::signbit(derivative_mid)) {
          b = midpoint;
        } else {
          a = midpoint;
          derivative_a = derivative_mid;
        }
      }
      const double stationary_t = 0.5 * (a + b);
      lower_t = stationary_t;
      upper_t = stationary_t;
    }
    constexpr double golden = 0.6180339887498948482;
    double a = lower_t;
    double b = upper_t;
    double c = b - golden * (b - a);
    double d = a + golden * (b - a);
    double fc = std::abs(evaluate(origin + c * ray_direction));
    double fd = std::abs(evaluate(origin + d * ray_direction));
    constexpr int iterations = 64;
    for (int iteration = 0; iteration < iterations && b > a; ++iteration) {
      add_performance_counter(PerformanceCounter::local_subdivision_nodes);
      if (fc < fd) {
        b = d;
        d = c;
        fd = fc;
        c = b - golden * (b - a);
        fc = std::abs(evaluate(origin + c * ray_direction));
      } else {
        a = c;
        c = d;
        fc = fd;
        d = a + golden * (b - a);
        fd = std::abs(evaluate(origin + d * ray_direction));
      }
    }
    const double t = 0.5 * (a + b);
    const Vec3 point = origin + t * ray_direction;
    const double residual = std::abs(evaluate(point));
    if (residual > options.tangent_residual_multiplier
                     * options.absolute_f_tolerance
        || !(t > minimum_t) || !(t < best_t)) return false;
    const auto local = surface_.local_coordinates(point);
    const double parameter_tolerance = 1.0e-9;
    const auto contains = [&](double value, double lower, double upper) {
      double wrapped = std::fmod(value, two_pi);
      if (wrapped < 0.0) wrapped += two_pi;
      return (wrapped >= lower - parameter_tolerance
              && wrapped <= upper + parameter_tolerance)
             || (upper >= two_pi - parameter_tolerance
                 && wrapped <= parameter_tolerance);
    };
    if (!contains(local.theta, patch.uv.theta_min, patch.uv.theta_max)
        || !contains(local.phi, patch.uv.phi_min, patch.uv.phi_max)) {
      return false;
    }
    best_t = t;
    best_residual = residual;
    best_patch = patch_id;
    best_tangent = stationary_contact;
    add_performance_counter(PerformanceCounter::tangent_or_grazing_cases);
    add_performance_counter(PerformanceCounter::local_interval_certifications);
    return true;
  };

  while (stack_size != 0) {
    const StackEntry entry = stack[--stack_size];
    if (entry.near_t >= best_t) continue;
    const auto& node = patch_bvh_[entry.node];
    add_performance_counter(PerformanceCounter::candidate_bvh_nodes);
    if (node.leaf()) {
      for (std::uint32_t local = 0; local < node.count; ++local) {
        const std::uint32_t patch_id = patch_indices_[node.first + local];
        const auto& patch = patches_[patch_id];
        const auto patch_interval = ray_box_interval(patch.conservative_bbox);
        if (!patch_interval || patch_interval->exit <= minimum_t
            || patch_interval->enter >= best_t) continue;
        ++candidate_count;
        add_performance_counter(
          PerformanceCounter::candidate_patches_or_segments);

        std::array<std::array<double, 2>, 7> seeds {};
        std::size_t seed_count = 0;
        const double theta_span = patch.uv.theta_max - patch.uv.theta_min;
        const double phi_span = patch.uv.phi_max - patch.uv.phi_min;
        const auto first = intersect_triangle(origin, ray_direction,
          patch.proxy_corners[0], patch.proxy_corners[1],
          patch.proxy_corners[2]);
        add_performance_counter(PerformanceCounter::proxy_intersections);
        if (first.found && first.t > minimum_t
            && first.t >= patch_interval->enter - patch.proxy_error_bound
            && first.t <= patch_interval->exit + patch.proxy_error_bound) {
          seeds[seed_count++] = {{
            patch.uv.theta_min + (first.b1 + first.b2) * theta_span,
            patch.uv.phi_min + first.b2 * phi_span}};
        }
        const auto second = intersect_triangle(origin, ray_direction,
          patch.proxy_corners[0], patch.proxy_corners[2],
          patch.proxy_corners[3]);
        add_performance_counter(PerformanceCounter::proxy_intersections);
        if (second.found && second.t > minimum_t
            && second.t >= patch_interval->enter - patch.proxy_error_bound
            && second.t <= patch_interval->exit + patch.proxy_error_bound) {
          seeds[seed_count++] = {{
            patch.uv.theta_min + second.b1 * theta_span,
            patch.uv.phi_min + (second.b1 + second.b2) * phi_span}};
        }
        if (seed_count == 0) {
          const double segment_t0 = std::max(minimum_t, patch_interval->enter);
          const double segment_t1 = std::min(best_t, patch_interval->exit);
          const Vec3 segment_a = origin + segment_t0 * ray_direction;
          const Vec3 segment_b = origin + segment_t1 * ray_direction;
          const double first_distance = segment_triangle_distance_squared(
            segment_a, segment_b, patch.proxy_corners[0],
            patch.proxy_corners[1], patch.proxy_corners[2]);
          const double second_distance = segment_triangle_distance_squared(
            segment_a, segment_b, patch.proxy_corners[0],
            patch.proxy_corners[2], patch.proxy_corners[3]);
          if (std::min(first_distance, second_distance)
              > patch.proxy_error_bound * patch.proxy_error_bound) {
            add_performance_counter(
              PerformanceCounter::local_interval_certifications);
            continue;
          }
          seeds[seed_count++] = {{
            0.5 * (patch.uv.theta_min + patch.uv.theta_max),
            0.5 * (patch.uv.phi_min + patch.uv.phi_max)}};
        }
        add_performance_counter(
          PerformanceCounter::proxy_seeds, seed_count);
        bool solved = false;
        bool needs_subdivision = false;
        for (std::size_t seed = 0; seed < seed_count; ++seed) {
          solved = solve_seed(
            patch, patch_id, seeds[seed][0], seeds[seed][1],
            needs_subdivision) || solved;
        }
        bool stationary_bracket = false;
        bool possible_crossings = false;
        if (!solved || needs_subdivision) {
          const bool interval_solved = solve_tangent_interval(patch, patch_id,
            std::max(minimum_t, patch_interval->enter),
            patch_interval->exit, stationary_bracket,
            possible_crossings);
          solved = interval_solved || solved;
          if (interval_solved) needs_subdivision = false;
        }
        if ((!solved || needs_subdivision) && stationary_bracket
            && possible_crossings) {
          add_performance_counter(
            PerformanceCounter::local_subdivision_calls);
          constexpr std::array<double, 3> fractions {{0.125, 0.5, 0.875}};
          for (double theta_fraction : fractions) {
            for (double phi_fraction : fractions) {
              add_performance_counter(
                PerformanceCounter::local_subdivision_nodes);
              solved = solve_seed(patch, patch_id,
                patch.uv.theta_min + theta_fraction * theta_span,
                patch.uv.phi_min + phi_fraction * phi_span,
                needs_subdivision) || solved;
            }
          }
          record_subdivision_depth(1);
        }
      }
      continue;
    }

    const auto left_interval = ray_box_interval(patch_bvh_[node.left].bbox);
    const auto right_interval = ray_box_interval(patch_bvh_[node.right].bbox);
    const bool use_left = left_interval && left_interval->exit > minimum_t
                          && left_interval->enter < best_t;
    const bool use_right = right_interval && right_interval->exit > minimum_t
                           && right_interval->enter < best_t;
    if (use_left && use_right) {
      const bool left_near = left_interval->enter <= right_interval->enter;
      if (stack_size + 2 > stack.size()) {
        ++diagnostics.unresolved_intervals;
        break;
      }
      stack[stack_size++] = left_near
        ? StackEntry {node.right, right_interval->enter}
        : StackEntry {node.left, left_interval->enter};
      stack[stack_size++] = left_near
        ? StackEntry {node.left, left_interval->enter}
        : StackEntry {node.right, right_interval->enter};
    } else if (use_left || use_right) {
      if (stack_size + 1 > stack.size()) {
        ++diagnostics.unresolved_intervals;
        break;
      }
      stack[stack_size++] = use_left
        ? StackEntry {node.left, left_interval->enter}
        : StackEntry {node.right, right_interval->enter};
    }
  }

  record_candidate_count(candidate_count);
  record_newton_count(ray_newton_iterations);
  diagnostics.safeguarded_newton_iterations =
    static_cast<long>(ray_newton_iterations);
  diagnostics.certified_excluded_intervals =
    static_cast<long>(patches_.size()) - static_cast<long>(candidate_count);
  if (!std::isfinite(best_t)) {
    return {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      diagnostics};
  }
  add_performance_counter(PerformanceCounter::local_interval_certifications);
  return {true, best_t,
    best_tangent ? RootKind::stationary_tangent : RootKind::sign_change,
    best_residual, diagnostics};
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
