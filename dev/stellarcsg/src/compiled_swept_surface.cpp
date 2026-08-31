#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/performance_counters.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <utility>

namespace stellarcsg {
namespace {

constexpr double two_pi =
  2.0 * 3.141592653589793238462643383279502884;

constexpr std::array<std::array<double, 4>, 4> bspline_to_power {{
  {{1.0 / 6.0, 4.0 / 6.0, 1.0 / 6.0, 0.0}},
  {{-0.5, 0.0, 0.5, 0.0}},
  {{0.5, -1.0, 0.5, 0.0}},
  {{-1.0 / 6.0, 0.5, -0.5, 1.0 / 6.0}}}};

std::atomic<std::uint64_t> next_swept_surface_instance {1};

struct SweptEvaluationCache {
  std::uint64_t instance_id {0};
  Vec3 point {};
  double value {0.0};
  bool valid {false};
};

thread_local SweptEvaluationCache swept_evaluation_cache;

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

std::size_t wrap_index(long index, std::size_t size)
{
  const long signed_size = static_cast<long>(size);
  long wrapped = index % signed_size;
  if (wrapped < 0) wrapped += signed_size;
  return static_cast<std::size_t>(wrapped);
}

BoundingBox empty_box()
{
  return {{std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity()},
          {-std::numeric_limits<double>::infinity(),
            -std::numeric_limits<double>::infinity(),
            -std::numeric_limits<double>::infinity()}};
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

Vec3 centroid(const BoundingBox& box)
{
  return 0.5 * (box.lower + box.upper);
}

double point_box_distance_squared(const Vec3& point, const BoundingBox& box)
{
  const auto axis_distance = [](double value, double lower, double upper) {
    if (value < lower) return lower - value;
    if (value > upper) return value - upper;
    return 0.0;
  };
  const double dx = axis_distance(point.x, box.lower.x, box.upper.x);
  const double dy = axis_distance(point.y, box.lower.y, box.upper.y);
  const double dz = axis_distance(point.z, box.lower.z, box.upper.z);
  return dx * dx + dy * dy + dz * dz;
}

} // namespace

CompiledSweptSplineSurface::CompiledSweptSplineSurface(
  SweptSplineSurfaceData data, bool force_general_solver)
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
  instance_id_ = next_swept_surface_instance.fetch_add(
    1, std::memory_order_relaxed);
  circular_radius_ = data_.major_radius_coefficients.front();
  const double circular_tolerance = std::max(
    64.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length,
    1.0e-12 * data_.characteristic_length);
  circular_cross_section_ = std::all_of(
    data_.major_radius_coefficients.begin(),
    data_.major_radius_coefficients.end(), [&](double value) {
      return std::abs(value - circular_radius_) <= circular_tolerance;
    }) && std::all_of(data_.minor_radius_coefficients.begin(),
      data_.minor_radius_coefficients.end(), [&](double value) {
        return std::abs(value - circular_radius_) <= circular_tolerance;
      });
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
  build_spans();

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
  if (circular && !force_general_solver) {
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

SweptLocalCoordinates CompiledSweptSplineSurface::frame_in_span(
  const SweptSpan& span, double angle) const
{
  const double coordinate_scale = 1.0 / (span.angle_max - span.angle_min);
  const double u = (angle - span.angle_min) * coordinate_scale;
  std::array<double, 8> value {};
  std::array<double, 3> derivative {};
  for (std::size_t field = 0; field < value.size(); ++field) {
    const double c0 = span.power[4 * field];
    const double c1 = span.power[4 * field + 1];
    const double c2 = span.power[4 * field + 2];
    const double c3 = span.power[4 * field + 3];
    value[field] = ((c3 * u + c2) * u + c1) * u + c0;
    if (field < derivative.size()) {
      derivative[field] = ((3.0 * c3 * u + 2.0 * c2) * u + c1)
                          * coordinate_scale;
    }
  }
  Vec3 tangent = normalized({derivative[0], derivative[1], derivative[2]});
  Vec3 normal_value {value[3], value[4], value[5]};
  normal_value = normalized(normal_value - dot(normal_value, tangent) * tangent);
  Vec3 binormal_value = normalized(cross(tangent, normal_value));
  normal_value = cross(binormal_value, tangent);
  return {data_.coil_id, wrap(angle) * data_.length / two_pi, 0.0, 0.0,
    {value[0], value[1], value[2]}, tangent, normal_value, binormal_value,
    value[6], value[7]};
}

double CompiledSweptSplineSurface::squared_distance(
  const Vec3& point, double angle) const
{
  const auto value = frame(angle);
  return norm_squared(point - value.center);
}

Vec3 CompiledSweptSplineSurface::surface_point(
  const SweptSpan& span, double angle, double alpha) const
{
  const auto value = frame_in_span(span, angle);
  return value.center
    + value.major_radius * std::cos(alpha) * value.normal
    + value.minor_radius * std::sin(alpha) * value.binormal;
}

void CompiledSweptSplineSurface::center_derivatives(const SweptSpan& span,
  double angle, Vec3& center, Vec3& first, Vec3& second) const
{
  const double scale = 1.0 / (span.angle_max - span.angle_min);
  const double u = (angle - span.angle_min) * scale;
  for (std::size_t axis = 0; axis < 3; ++axis) {
    const double* coefficient = span.power.data() + 4 * axis;
    const double value = ((coefficient[3] * u + coefficient[2]) * u
      + coefficient[1]) * u + coefficient[0];
    const double derivative = (coefficient[1]
      + 2.0 * coefficient[2] * u + 3.0 * coefficient[3] * u * u)
      * scale;
    const double second_derivative = (2.0 * coefficient[2]
      + 6.0 * coefficient[3] * u) * scale * scale;
    if (axis == 0) {
      center.x = value;
      first.x = derivative;
      second.x = second_derivative;
    } else if (axis == 1) {
      center.y = value;
      first.y = derivative;
      second.y = second_derivative;
    } else {
      center.z = value;
      first.z = derivative;
      second.z = second_derivative;
    }
  }
}

void CompiledSweptSplineSurface::surface_derivatives(const SweptSpan& span,
  double angle, double alpha, Vec3& position, Vec3& dangle,
  Vec3& dalpha) const
{
  const double scale = 1.0 / (span.angle_max - span.angle_min);
  const double u = (angle - span.angle_min) * scale;
  std::array<double, 8> value {};
  std::array<double, 8> derivative {};
  std::array<double, 3> second_derivative {};
  for (std::size_t field = 0; field < value.size(); ++field) {
    const double* coefficient = span.power.data() + 4 * field;
    value[field] = ((coefficient[3] * u + coefficient[2]) * u
                     + coefficient[1]) * u + coefficient[0];
    derivative[field] = (coefficient[1] + 2.0 * coefficient[2] * u
                          + 3.0 * coefficient[3] * u * u) * scale;
    if (field < second_derivative.size()) {
      second_derivative[field] = (2.0 * coefficient[2]
        + 6.0 * coefficient[3] * u) * scale * scale;
    }
  }
  const Vec3 center {value[0], value[1], value[2]};
  const Vec3 center_d {derivative[0], derivative[1], derivative[2]};
  const Vec3 center_dd {
    second_derivative[0], second_derivative[1], second_derivative[2]};
  const double speed = norm(center_d);
  const Vec3 tangent = center_d / speed;
  const Vec3 tangent_d = (center_dd - tangent * dot(tangent, center_dd))
                         / speed;
  const Vec3 supplied_normal {value[3], value[4], value[5]};
  const Vec3 supplied_normal_d {
    derivative[3], derivative[4], derivative[5]};
  const double projection = dot(supplied_normal, tangent);
  const double projection_d = dot(supplied_normal_d, tangent)
                              + dot(supplied_normal, tangent_d);
  const Vec3 normal_raw = supplied_normal - projection * tangent;
  const Vec3 normal_raw_d = supplied_normal_d - projection_d * tangent
                            - projection * tangent_d;
  const double normal_length = norm(normal_raw);
  Vec3 normal_value = normal_raw / normal_length;
  Vec3 normal_d = (normal_raw_d
    - normal_value * dot(normal_value, normal_raw_d)) / normal_length;
  const Vec3 binormal_raw = cross(tangent, normal_value);
  const Vec3 binormal_raw_d = cross(tangent_d, normal_value)
                              + cross(tangent, normal_d);
  const double binormal_length = norm(binormal_raw);
  const Vec3 binormal_value = binormal_raw / binormal_length;
  const Vec3 binormal_d = (binormal_raw_d
    - binormal_value * dot(binormal_value, binormal_raw_d))
    / binormal_length;
  normal_value = cross(binormal_value, tangent);
  normal_d = cross(binormal_d, tangent) + cross(binormal_value, tangent_d);
  const double cosine = std::cos(alpha);
  const double sine = std::sin(alpha);
  const double major = value[6];
  const double minor = value[7];
  position = center + major * cosine * normal_value
             + minor * sine * binormal_value;
  dangle = center_d
           + cosine * (derivative[6] * normal_value + major * normal_d)
           + sine * (derivative[7] * binormal_value + minor * binormal_d);
  dalpha = -major * sine * normal_value
           + minor * cosine * binormal_value;
}

void CompiledSweptSplineSurface::build_spans()
{
  const double step = two_pi / static_cast<double>(data_.sample_count);
  const double rounding = std::max(
    64.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length,
    1.0e-12 * data_.characteristic_length);
  constexpr std::size_t subdivisions = 1;
  spans_.clear();
  spans_.reserve(subdivisions * data_.sample_count);
  for (std::size_t i = 0; i < data_.sample_count; ++i) {
    std::array<double, 32> base_power {};
    const auto coefficient_value = [&](std::size_t field,
                                      std::size_t control) {
      if (field < 3) return data_.centerline_coefficients[3 * control + field];
      if (field < 6) return data_.normal_coefficients[
        3 * control + (field - 3)];
      return field == 6 ? data_.major_radius_coefficients[control]
                        : data_.minor_radius_coefficients[control];
    };
    for (std::size_t field = 0; field < 8; ++field) {
      for (std::size_t power = 0; power < 4; ++power) {
        double coefficient = 0.0;
        for (std::size_t a = 0; a < 4; ++a) {
          const std::size_t control = wrap_index(
            static_cast<long>(i) + static_cast<long>(a) - 1,
            data_.sample_count);
          coefficient += bspline_to_power[power][a]
                         * coefficient_value(field, control);
        }
        base_power[4 * field + power] = coefficient;
      }
    }
    for (std::size_t subdivision = 0;
         subdivision < subdivisions; ++subdivision) {
      SweptSpan span;
      const double a = static_cast<double>(subdivision)
                       / static_cast<double>(subdivisions);
      const double h = 1.0 / static_cast<double>(subdivisions);
      span.angle_min = step * (static_cast<double>(i) + a);
      span.angle_max = span.angle_min + step * h;
      for (std::size_t field = 0; field < 8; ++field) {
        const double* source = base_power.data() + 4 * field;
        double* target = span.power.data() + 4 * field;
        target[0] = ((source[3] * a + source[2]) * a + source[1]) * a
                    + source[0];
        target[1] = h * (source[1] + 2.0 * source[2] * a
                         + 3.0 * source[3] * a * a);
        target[2] = h * h * (source[2] + 3.0 * source[3] * a);
        target[3] = h * h * h * source[3];
      }
      span.proxy_start = frame_in_span(span, span.angle_min).center;
      span.proxy_end = frame_in_span(span, span.angle_max).center;
      BoundingBox center_bounds = empty_box();
      double radius_bound = 0.0;
      for (std::size_t bezier = 0; bezier < 4; ++bezier) {
        Vec3 center_control;
        for (std::size_t field = 0; field < 8; ++field) {
          const double* power = span.power.data() + 4 * field;
          const double value = bezier == 0 ? power[0]
            : bezier == 1 ? power[0] + power[1] / 3.0
            : bezier == 2 ? power[0] + 2.0 * power[1] / 3.0
                            + power[2] / 3.0
            : power[0] + power[1] + power[2] + power[3];
          if (field == 0) center_control.x = value;
          else if (field == 1) center_control.y = value;
          else if (field == 2) center_control.z = value;
          else if (field >= 6) radius_bound = std::max(radius_bound, value);
        }
        extend(center_bounds, center_control);
      }
      span.radius_bound = radius_bound;
      const Vec3 second_start {
        2.0 * span.power[2], 2.0 * span.power[6],
        2.0 * span.power[10]};
      const Vec3 second_end {
        2.0 * span.power[2] + 6.0 * span.power[3],
        2.0 * span.power[6] + 6.0 * span.power[7],
        2.0 * span.power[10] + 6.0 * span.power[11]};
      const double centerline_error = std::max(
        norm(second_start), norm(second_end)) / 8.0;
      span.proxy_radius = radius_bound + centerline_error + rounding;
      const double inflation = radius_bound + rounding;
      span.centerline_bbox = center_bounds;
      span.conservative_bbox = {
        center_bounds.lower - Vec3 {inflation, inflation, inflation},
        center_bounds.upper + Vec3 {inflation, inflation, inflation}};
      spans_.push_back(span);
    }
  }
  span_indices_.resize(spans_.size());
  std::iota(span_indices_.begin(), span_indices_.end(), 0U);
  span_bvh_.clear();
  span_bvh_.reserve(2 * spans_.size());
  if (!spans_.empty()) {
    (void) build_span_bvh_node(0U,
      static_cast<std::uint32_t>(spans_.size()));
    bounds_ = span_bvh_.front().bbox;
  }
}

std::uint32_t CompiledSweptSplineSurface::build_span_bvh_node(
  std::uint32_t first, std::uint32_t last)
{
  const std::uint32_t node_index = static_cast<std::uint32_t>(span_bvh_.size());
  span_bvh_.push_back({});
  BoundingBox bounds = empty_box();
  BoundingBox centerline_bounds = empty_box();
  BoundingBox centroids = empty_box();
  for (std::uint32_t i = first; i < last; ++i) {
    const auto& span = spans_[span_indices_[i]];
    const auto& box = span.conservative_bbox;
    extend(bounds, box);
    extend(centerline_bounds, span.centerline_bbox);
    extend(centroids, centroid(box));
  }
  span_bvh_[node_index].centerline_bbox = centerline_bounds;
  span_bvh_[node_index].bbox = bounds;
  const std::uint32_t count = last - first;
  constexpr std::uint32_t leaf_size = 4;
  if (count <= leaf_size) {
    span_bvh_[node_index].first = first;
    span_bvh_[node_index].count = static_cast<std::uint16_t>(count);
    return node_index;
  }
  const Vec3 extent = centroids.upper - centroids.lower;
  const int axis = extent.y > extent.x ? (extent.z > extent.y ? 2 : 1)
                                      : (extent.z > extent.x ? 2 : 0);
  const auto component_value = [](const Vec3& value, int selected) {
    return selected == 0 ? value.x : (selected == 1 ? value.y : value.z);
  };
  const std::uint32_t middle = first + count / 2;
  std::nth_element(span_indices_.begin() + first,
    span_indices_.begin() + middle, span_indices_.begin() + last,
    [&](std::uint32_t lhs, std::uint32_t rhs) {
      return component_value(centroid(spans_[lhs].conservative_bbox), axis)
             < component_value(centroid(spans_[rhs].conservative_bbox), axis);
    });
  span_bvh_[node_index].left = build_span_bvh_node(first, middle);
  span_bvh_[node_index].right = build_span_bvh_node(middle, last);
  return node_index;
}

double CompiledSweptSplineSurface::evaluate_in_span(
  const Vec3& point, const SweptSpan& span, double* angle) const
{
  const auto local_squared_distance = [&](double candidate) {
    const double coordinate_scale = 1.0
      / (span.angle_max - span.angle_min);
    const double u = (candidate - span.angle_min) * coordinate_scale;
    Vec3 center;
    for (std::size_t axis = 0; axis < 3; ++axis) {
      const double* coefficient = span.power.data() + 4 * axis;
      const double value = ((coefficient[3] * u + coefficient[2]) * u
                             + coefficient[1]) * u + coefficient[0];
      if (axis == 0) center.x = value;
      else if (axis == 1) center.y = value;
      else center.z = value;
    }
    return norm_squared(point - center);
  };
  double left = span.angle_min;
  double right = span.angle_max;
  constexpr double ratio = 0.6180339887498948482;
  double c = right - ratio * (right - left);
  double d = left + ratio * (right - left);
  double fc = local_squared_distance(c);
  double fd = local_squared_distance(d);
  for (int iteration = 0; iteration < 8; ++iteration) {
    if (fc < fd) {
      right = d;
      d = c;
      fd = fc;
      c = right - ratio * (right - left);
      fc = local_squared_distance(c);
    } else {
      left = c;
      c = d;
      fc = fd;
      d = left + ratio * (right - left);
      fd = local_squared_distance(d);
    }
  }
  double q = 0.5 * (left + right);
  for (int iteration = 0; iteration < 5; ++iteration) {
    Vec3 center;
    Vec3 first;
    Vec3 second;
    center_derivatives(span, q, center, first, second);
    const Vec3 offset = center - point;
    const double gradient = dot(offset, first);
    const double hessian = norm_squared(first) + dot(offset, second);
    if (!(hessian > 0.0) || !std::isfinite(hessian)) break;
    const double next = std::clamp(q - gradient / hessian, left, right);
    if (std::abs(next - q) <= 1.0e-14) {
      q = next;
      break;
    }
    q = next;
  }
  if (angle) *angle = q;
  const auto value = frame_in_span(span, q);
  const Vec3 offset = point - value.center;
  const double u = dot(offset, value.normal) / value.major_radius;
  const double v = dot(offset, value.binormal) / value.minor_radius;
  return u * u + v * v - 1.0;
}

SweptLocalCoordinates CompiledSweptSplineSurface::local_coordinates(
  const Vec3& point) const
{
  struct StackEntry { std::uint32_t node; double lower_bound; };
  std::array<StackEntry, 64> stack {};
  std::size_t stack_size = 0;
  double best_angle = 0.0;
  std::size_t refined_span = 0;
  double refined_distance = std::numeric_limits<double>::infinity();
  if (!span_bvh_.empty()) {
    stack[stack_size++] = {
      0U, point_box_distance_squared(point, span_bvh_[0].centerline_bbox)};
  }
  while (stack_size != 0) {
    const auto entry = stack[--stack_size];
    if (entry.lower_bound >= refined_distance) continue;
    const auto& node = span_bvh_[entry.node];
    if (node.leaf()) {
      for (std::uint32_t local = 0; local < node.count; ++local) {
        const std::size_t candidate = span_indices_[node.first + local];
        const auto& span = spans_[candidate];
        if (point_box_distance_squared(point, span.centerline_bbox)
            >= refined_distance) continue;
        double angle = 0.0;
        (void) evaluate_in_span(point, span, &angle);
        const double distance = norm_squared(
          point - frame_in_span(span, angle).center);
        if (distance < refined_distance) {
          refined_distance = distance;
          best_angle = angle;
          refined_span = candidate;
        }
      }
      continue;
    }
    const double left_bound = point_box_distance_squared(
      point, span_bvh_[node.left].centerline_bbox);
    const double right_bound = point_box_distance_squared(
      point, span_bvh_[node.right].centerline_bbox);
    const bool left_first = left_bound <= right_bound;
    const StackEntry near_entry = left_first
      ? StackEntry {node.left, left_bound}
      : StackEntry {node.right, right_bound};
    const StackEntry far_entry = left_first
      ? StackEntry {node.right, right_bound}
      : StackEntry {node.left, left_bound};
    if (far_entry.lower_bound < refined_distance)
      stack[stack_size++] = far_entry;
    if (near_entry.lower_bound < refined_distance)
      stack[stack_size++] = near_entry;
  }
  auto result = frame_in_span(spans_[refined_span], best_angle);
  const Vec3 offset = point - result.center;
  result.u = dot(offset, result.normal);
  result.v = dot(offset, result.binormal);
  return result;
}

double CompiledSweptSplineSurface::evaluate(const Vec3& point) const
{
  add_performance_counter(PerformanceCounter::evaluate_calls);
  auto& cache = swept_evaluation_cache;
  if (cache.valid && cache.instance_id == instance_id_
      && cache.point.x == point.x && cache.point.y == point.y
      && cache.point.z == point.z) {
    add_performance_counter(PerformanceCounter::cache_hits);
    return cache.value;
  }
  add_performance_counter(PerformanceCounter::cache_misses);
  double value;
  if (exact_torus_) {
    value = exact_torus_->evaluate(point);
  } else {
    const auto local = local_coordinates(point);
    const double u = local.u / local.major_radius;
    const double v = local.v / local.minor_radius;
    value = u * u + v * v - 1.0;
  }
  cache = {instance_id_, point, value, true};
  return value;
}

Vec3 CompiledSweptSplineSurface::normal(const Vec3& point) const
{
  add_performance_counter(PerformanceCounter::normal_calls);
  if (exact_torus_) return exact_torus_->normal(point);
  const auto local = local_coordinates(point);
  const double angle = wrap(local.arc_coordinate * two_pi / data_.length);
  const double step = two_pi / static_cast<double>(spans_.size());
  const std::size_t span_id = std::min(
    static_cast<std::size_t>(angle / step), spans_.size() - 1);
  const auto& span = spans_[span_id];
  const double alpha = std::atan2(
    local.v / local.minor_radius, local.u / local.major_radius);
  Vec3 position;
  Vec3 dangle;
  Vec3 dalpha;
  surface_derivatives(span, angle, alpha, position, dangle, dalpha);
  Vec3 result = normalized(cross(dangle, dalpha));
  if (dot(result, point - local.center) < 0.0)
    result = -1.0 * result;
  return result;
}

DistanceResult CompiledSweptSplineSurface::distance_reference(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  add_performance_counter(PerformanceCounter::distance_calls);
  add_performance_counter(PerformanceCounter::global_reference_calls);
  if (coincident) add_performance_counter(PerformanceCounter::coincident_cases);
  [[maybe_unused]] ScopedDistanceTimer timer;
  if (exact_torus_) {
    const auto result = exact_torus_->distance(origin, direction, coincident, options);
    add_performance_counter(result.found ? PerformanceCounter::accepted_roots
                                         : PerformanceCounter::no_hit_returns);
    if (result.found) record_residual(result.residual, data_.characteristic_length);
    return result;
  }
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0)) {
    throw std::invalid_argument("Ray direction must be non-zero");
  }
  const Vec3 u = direction / direction_norm;
  const auto interval = bounds_.ray_interval(origin, u);
  if (!interval) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {};
  }
  double t_min = std::max(0.0, interval->enter);
  const double push = 8.0 * options.absolute_t_tolerance;
  if (coincident || std::abs(evaluate(origin)) <= options.absolute_f_tolerance)
    t_min = std::max(t_min, push);
  if (!(interval->exit > t_min)) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {};
  }
  const auto function = [&](double t) { return evaluate(origin + t * u); };
  const auto derivative = [&](double t) {
    const double h = std::sqrt(std::numeric_limits<double>::epsilon())
                     * data_.characteristic_length;
    return (function(t + h) - function(t - h)) / (2.0 * h);
  };
  const auto root = find_nearest_root_reference(
    function, derivative, t_min, interval->exit, options);
  if (!root.found) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      root.diagnostics};
  }
  add_performance_counter(PerformanceCounter::accepted_roots);
  record_residual(root.root.residual, data_.characteristic_length);
  return {true, root.root.t, root.root.kind, root.root.residual,
    root.diagnostics};
}

DistanceResult CompiledSweptSplineSurface::distance(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  add_performance_counter(PerformanceCounter::distance_calls);
  if (coincident) add_performance_counter(PerformanceCounter::coincident_cases);
  [[maybe_unused]] ScopedDistanceTimer timer;
  if (exact_torus_) {
    return exact_torus_->distance(origin, direction, coincident, options);
  }
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0) || !std::isfinite(direction_norm)) {
    throw std::invalid_argument("Ray direction must be finite and non-zero");
  }
  const Vec3 ray_direction = direction / direction_norm;
  RootSearchDiagnostics diagnostics;
  diagnostics.solver_path = SolverPath::general_swept_certified;
  if (span_bvh_.empty()) return {};
  const auto root_interval = span_bvh_.front().bbox.ray_interval(
    origin, ray_direction);
  if (!root_interval || root_interval->exit < 0.0) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {};
  }
  const double crossing_push = std::max({
    64.0 * options.absolute_t_tolerance,
    8.0 * options.absolute_f_tolerance * data_.characteristic_length,
    64.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length});
  const double minimum_t = coincident ? crossing_push : 0.0;
  Vec3 basis1 = std::abs(ray_direction.z) < 0.9
    ? normalized(cross(ray_direction, Vec3 {0.0, 0.0, 1.0}))
    : normalized(cross(ray_direction, Vec3 {0.0, 1.0, 0.0}));
  const Vec3 basis2 = cross(ray_direction, basis1);
  const double projected_tolerance = std::max(
    options.absolute_f_tolerance * data_.characteristic_length,
    64.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length);
  double best_t = std::numeric_limits<double>::infinity();
  double best_residual = std::numeric_limits<double>::infinity();
  std::uint32_t best_span = std::numeric_limits<std::uint32_t>::max();
  std::uint64_t candidates = 0;
  std::uint64_t iterations_total = 0;

  const auto solve_seed = [&](const SweptSpan& span, std::uint32_t span_id,
                            double ray_seed, double angle_seed,
                            double alpha_seed) {
    double angle = std::clamp(angle_seed, span.angle_min, span.angle_max);
    const double span_width = span.angle_max - span.angle_min;
    if (circular_cross_section_) {
      double t = ray_seed;
      double residual = std::numeric_limits<double>::infinity();
      const double circular_tolerance = std::max(
        options.absolute_f_tolerance * std::max(1.0, circular_radius_),
        64.0 * std::numeric_limits<double>::epsilon()
          * data_.characteristic_length);
      int iterations = 0;
      for (; iterations < 8; ++iterations) {
        Vec3 center;
        Vec3 center_d;
        Vec3 center_dd;
        center_derivatives(span, angle, center, center_d, center_dd);
        const double speed = norm(center_d);
        const Vec3 tangent = center_d / speed;
        const Vec3 tangent_d = (center_dd
          - tangent * dot(tangent, center_dd)) / speed;
        const Vec3 radial = origin + t * ray_direction - center;
        const double radial_length = norm(radial);
        if (!(radial_length > 0.0)) break;
        const double h1 = dot(radial, tangent);
        const double h2 = radial_length - circular_radius_;
        residual = std::hypot(h1, h2);
        if (residual <= circular_tolerance) break;
        const double j11 = -speed + dot(radial, tangent_d);
        const double j12 = dot(ray_direction, tangent);
        const double j21 = -dot(radial, center_d) / radial_length;
        const double j22 = dot(radial, ray_direction) / radial_length;
        const double determinant = j11 * j22 - j12 * j21;
        const double scale = std::max(
          1.0, std::hypot(j11, j21) * std::hypot(j12, j22));
        if (std::abs(determinant)
            <= 128.0 * std::numeric_limits<double>::epsilon() * scale) break;
        double delta_angle = (-h1 * j22 + h2 * j12) / determinant;
        double delta_t = (-j11 * h2 + j21 * h1) / determinant;
        const double trust = std::max({1.0,
          std::abs(delta_angle) / (0.5 * span_width),
          std::abs(delta_t) / (2.0 * span.proxy_radius)});
        delta_angle /= trust;
        delta_t /= trust;
        angle = std::clamp(
          angle + delta_angle, span.angle_min, span.angle_max);
        t = std::max(minimum_t, t + delta_t);
      }
      iterations_total += static_cast<std::uint64_t>(iterations);
      add_performance_counter(PerformanceCounter::newton_iterations,
        static_cast<std::uint64_t>(iterations));
      if (residual > circular_tolerance) {
        add_performance_counter(PerformanceCounter::newton_failures);
        return false;
      }
      if (!(t > minimum_t) || !(t < best_t + options.absolute_t_tolerance)) {
        add_performance_counter(PerformanceCounter::rejected_roots);
        return false;
      }
      if (std::abs(t - best_t) <= options.duplicate_t_multiplier
                                    * options.absolute_t_tolerance
          && span_id >= best_span) {
        add_performance_counter(PerformanceCounter::deduplicated_roots);
        return true;
      }
      best_t = t;
      best_residual = residual;
      best_span = span_id;
      return true;
    }
    double alpha = alpha_seed;
    double residual = std::numeric_limits<double>::infinity();
    int iterations = 0;
    for (; iterations < 12; ++iterations) {
      Vec3 position;
      Vec3 dangle;
      Vec3 dalpha;
      surface_derivatives(
        span, angle, alpha, position, dangle, dalpha);
      const Vec3 offset = position - origin;
      const double h1 = dot(basis1, offset);
      const double h2 = dot(basis2, offset);
      residual = std::hypot(h1, h2);
      if (residual <= projected_tolerance) break;
      const double j11 = dot(basis1, dangle);
      const double j12 = dot(basis1, dalpha);
      const double j21 = dot(basis2, dangle);
      const double j22 = dot(basis2, dalpha);
      const double determinant = j11 * j22 - j12 * j21;
      const double scale = std::max(
        1.0, std::hypot(j11, j21) * std::hypot(j12, j22));
      if (std::abs(determinant)
          <= 128.0 * std::numeric_limits<double>::epsilon() * scale) break;
      double delta_angle = (-h1 * j22 + h2 * j12) / determinant;
      double delta_alpha = (-j11 * h2 + j21 * h1) / determinant;
      const double trust = std::max({1.0,
        std::abs(delta_angle) / (0.5 * span_width),
        std::abs(delta_alpha) / (0.5 * 3.14159265358979323846)});
      delta_angle /= trust;
      delta_alpha /= trust;
      angle = std::clamp(
        angle + delta_angle, span.angle_min, span.angle_max);
      alpha = wrap(alpha + delta_alpha);
    }
    if (residual > projected_tolerance) {
      const Vec3 position = surface_point(span, angle, alpha);
      const Vec3 offset = position - origin;
      residual = std::hypot(dot(basis1, offset), dot(basis2, offset));
    }
    iterations_total += static_cast<std::uint64_t>(iterations);
    add_performance_counter(PerformanceCounter::newton_iterations,
      static_cast<std::uint64_t>(iterations));
    if (residual > projected_tolerance) {
      add_performance_counter(PerformanceCounter::newton_failures);
      return false;
    }
    const Vec3 position = surface_point(span, angle, alpha);
    const double t = dot(ray_direction, position - origin);
    if (!(t > minimum_t) || !(t < best_t + options.absolute_t_tolerance)) {
      add_performance_counter(PerformanceCounter::rejected_roots);
      return false;
    }
    if (std::abs(t - best_t) <= options.duplicate_t_multiplier
                                  * options.absolute_t_tolerance
        && span_id >= best_span) {
      add_performance_counter(PerformanceCounter::deduplicated_roots);
      return true;
    }
    best_t = t;
    best_residual = residual;
    best_span = span_id;
    return true;
  };

  struct StackEntry { std::uint32_t node; double near_t; };
  struct UnresolvedSpan {
    std::uint32_t span;
    double enter;
    double exit;
  };
  std::array<StackEntry, 64> stack {};
  std::array<UnresolvedSpan, 64> unresolved {};
  std::size_t unresolved_count = 0;
  std::size_t stack_size = 0;
  stack[stack_size++] = {0U, root_interval->enter};
  while (stack_size != 0) {
    const auto entry = stack[--stack_size];
    if (entry.near_t >= best_t) continue;
    const auto& node = span_bvh_[entry.node];
    add_performance_counter(PerformanceCounter::candidate_bvh_nodes);
    if (node.leaf()) {
      for (std::uint32_t local = 0; local < node.count; ++local) {
        const std::uint32_t span_id = span_indices_[node.first + local];
        const auto& span = spans_[span_id];
        const auto interval = span.conservative_bbox.ray_interval(
          origin, ray_direction);
        if (!interval || interval->exit <= minimum_t
            || interval->enter >= best_t) continue;
        ++candidates;
        add_performance_counter(PerformanceCounter::candidate_patches_or_segments);
        const Vec3 segment = span.proxy_end - span.proxy_start;
        const Vec3 w0 = origin - span.proxy_start;
        const double b = dot(ray_direction, segment);
        const double c = norm_squared(segment);
        const double e = dot(segment, w0);
        std::array<double, 6> proxy_t {};
        std::size_t proxy_count = 0;
        const auto add_proxy_t = [&](double t) {
          if (!(t > minimum_t) || !(t < best_t) || !std::isfinite(t)) return;
          for (std::size_t existing = 0; existing < proxy_count; ++existing) {
            if (std::abs(proxy_t[existing] - t)
                <= 1.0e-9 * data_.characteristic_length) return;
          }
          if (proxy_count < proxy_t.size()) proxy_t[proxy_count++] = t;
        };
        if (c > 0.0) {
          const double f0 = e / c;
          const double f1 = b / c;
          const Vec3 radial_origin = w0 - f0 * segment;
          const Vec3 radial_direction = ray_direction - f1 * segment;
          const double qa = norm_squared(radial_direction);
          const double qb = 2.0 * dot(radial_origin, radial_direction);
          const double qc = norm_squared(radial_origin)
                            - span.proxy_radius * span.proxy_radius;
          const double discriminant = qb * qb - 4.0 * qa * qc;
          if (qa > 0.0 && discriminant >= 0.0) {
            const double root = std::sqrt(discriminant);
            for (double t : {(-qb - root) / (2.0 * qa),
                             (-qb + root) / (2.0 * qa)}) {
              const double fraction = f0 + f1 * t;
              if (fraction >= 0.0 && fraction <= 1.0) add_proxy_t(t);
            }
          }
        }
        for (const Vec3 endpoint : {span.proxy_start, span.proxy_end}) {
          const Vec3 sphere_offset = origin - endpoint;
          const double qb = 2.0 * dot(sphere_offset, ray_direction);
          const double qc = norm_squared(sphere_offset)
                            - span.proxy_radius * span.proxy_radius;
          const double discriminant = qb * qb - 4.0 * qc;
          if (discriminant >= 0.0) {
            const double root = std::sqrt(discriminant);
            add_proxy_t(0.5 * (-qb - root));
            add_proxy_t(0.5 * (-qb + root));
          }
        }
        for (std::size_t insertion = 1; insertion < proxy_count; ++insertion) {
          const double value = proxy_t[insertion];
          std::size_t position = insertion;
          while (position > 0 && proxy_t[position - 1] > value) {
            proxy_t[position] = proxy_t[position - 1];
            --position;
          }
          proxy_t[position] = value;
        }
        add_performance_counter(PerformanceCounter::proxy_intersections);
        add_performance_counter(PerformanceCounter::proxy_seeds, proxy_count);
        bool solved = false;
        for (std::size_t seed = 0; seed < proxy_count; ++seed) {
          if (proxy_t[seed] >= best_t) break;
          const Vec3 proxy_point = origin + proxy_t[seed] * ray_direction;
          const double fraction = c > 0.0
            ? std::clamp(dot(proxy_point - span.proxy_start, segment) / c,
                0.0, 1.0)
            : 0.5;
          const double angle = span.angle_min
            + fraction * (span.angle_max - span.angle_min);
          const auto frame_value = frame_in_span(span, angle);
          const Vec3 transverse = proxy_point - frame_value.center;
          const double alpha = std::atan2(
            dot(transverse, frame_value.binormal) / frame_value.minor_radius,
            dot(transverse, frame_value.normal) / frame_value.major_radius);
          solved = solve_seed(
            span, span_id, proxy_t[seed], angle, alpha) || solved;
        }

        if (!solved && proxy_count != 0
            && unresolved_count < unresolved.size()) {
          unresolved[unresolved_count++] = {
            span_id, std::max(minimum_t, interval->enter), interval->exit};
        }
      }
      continue;
    }
    const auto left = span_bvh_[node.left].bbox.ray_interval(origin, ray_direction);
    const auto right = span_bvh_[node.right].bbox.ray_interval(origin, ray_direction);
    const bool use_left = left && left->exit > minimum_t && left->enter < best_t;
    const bool use_right = right && right->exit > minimum_t && right->enter < best_t;
    if (use_left && use_right) {
      const bool left_first = left->enter <= right->enter;
      if (stack_size + 2 > stack.size()) break;
      stack[stack_size++] = left_first
        ? StackEntry {node.right, right->enter}
        : StackEntry {node.left, left->enter};
      stack[stack_size++] = left_first
        ? StackEntry {node.left, left->enter}
        : StackEntry {node.right, right->enter};
    } else if (use_left || use_right) {
      if (stack_size + 1 > stack.size()) break;
      stack[stack_size++] = use_left
        ? StackEntry {node.left, left->enter}
        : StackEntry {node.right, right->enter};
    }
  }
  if (!std::isfinite(best_t)) {
    for (std::size_t unresolved_index = 0;
         unresolved_index < unresolved_count; ++unresolved_index) {
      const auto item = unresolved[unresolved_index];
      const auto& span = spans_[item.span];
      add_performance_counter(PerformanceCounter::local_subdivision_calls);
      constexpr int scan_segments = 8;
      double previous_t = item.enter;
      double previous_value = evaluate_in_span(
        origin + previous_t * ray_direction, span);
      for (int segment_index = 1;
           segment_index <= scan_segments; ++segment_index) {
        const double current_t = item.enter + (item.exit - item.enter)
          * static_cast<double>(segment_index)
            / static_cast<double>(scan_segments);
        const double current_value = evaluate_in_span(
          origin + current_t * ray_direction, span);
        add_performance_counter(PerformanceCounter::local_subdivision_nodes);
        if (std::signbit(previous_value) != std::signbit(current_value)) {
          double a = previous_t;
          double right = current_t;
          double fa = previous_value;
          for (int iteration = 0; iteration < 40; ++iteration) {
            const double midpoint = 0.5 * (a + right);
            const double fm = evaluate_in_span(
              origin + midpoint * ray_direction, span);
            if (std::signbit(fa) != std::signbit(fm)) right = midpoint;
            else { a = midpoint; fa = fm; }
          }
          const double t = 0.5 * (a + right);
          const double authoritative_residual = std::abs(
            evaluate(origin + t * ray_direction));
          if (t > minimum_t && t < best_t
              && authoritative_residual
                <= 100.0 * options.absolute_f_tolerance) {
            best_t = t;
            best_residual = authoritative_residual;
            best_span = item.span;
          }
          break;
        }
        previous_t = current_t;
        previous_value = current_value;
      }
      if (std::isfinite(best_t)) break;
    }
  }
  record_candidate_count(candidates);
  record_newton_count(iterations_total);
  diagnostics.safeguarded_newton_iterations =
    static_cast<long>(iterations_total);
  diagnostics.certified_excluded_intervals =
    static_cast<long>(spans_.size()) - static_cast<long>(candidates);
  if (!std::isfinite(best_t)) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      diagnostics};
  }
  add_performance_counter(PerformanceCounter::accepted_roots);
  record_residual(best_residual, data_.characteristic_length);
  return {true, best_t, RootKind::sign_change, best_residual, diagnostics};
}

} // namespace stellarcsg
