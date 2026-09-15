#ifndef STELLARCSG_SWEPT_SPAN_BOUNDS_HPP
#define STELLARCSG_SWEPT_SPAN_BOUNDS_HPP

// Conservative preprocessing bounds only. A retained interval is not a root proof.
#include "stellarcsg/vector.hpp"

#include <algorithm>
#include <array>
#include <cfenv>
#include <cmath>
#include <limits>
#include <optional>

namespace stellarcsg::swept_span_bounds {

constexpr double infinity = std::numeric_limits<double>::infinity();
using Cubic = std::array<double, 4>;

struct Interval {
  double lo;
  double hi;
};

using IntervalCubic = std::array<Interval, 4>;

struct CubicSpan {
  std::array<Cubic, 3> center;
  Cubic radius;
};

struct BoundsResult {
  BoundingBox box {{-infinity, -infinity, -infinity},
                   {infinity, infinity, infinity}};
  bool certain {false};
};

struct RayBoundsResult {
  std::optional<RayInterval> interval;
  bool certain {false}; // false means unknown, never an exclusion.
};

[[nodiscard]] inline bool supported_binary64() noexcept
{
#ifdef __FAST_MATH__
  return false;
#else
  if (!std::numeric_limits<double>::is_iec559
      || std::fegetround() != FE_TONEAREST) return false;
  volatile double tiny = std::numeric_limits<double>::min();
  volatile double denormal = std::numeric_limits<double>::denorm_min();
  volatile double half = tiny * 0.5;
  return half != 0.0 && half * 2.0 == tiny && denormal != 0.0;
#endif
}

[[nodiscard]] inline double down(double value) noexcept
{
  return std::nextafter(value, -infinity);
}

[[nodiscard]] inline double up(double value) noexcept
{
  return std::nextafter(value, infinity);
}

[[nodiscard]] inline bool finite(const Cubic& values) noexcept
{
  return std::all_of(values.begin(), values.end(), [](double value) {
    return std::isfinite(value);
  });
}

[[nodiscard]] inline Interval exact(double value) noexcept
{
  return {value, value};
}

[[nodiscard]] inline Interval add(Interval left, Interval right) noexcept
{
  return {down(left.lo + right.lo), up(left.hi + right.hi)};
}

[[nodiscard]] inline Interval multiply_positive(Interval value,
  double positive) noexcept
{
  return {down(value.lo * positive), up(value.hi * positive)};
}

[[nodiscard]] inline Interval divide_positive(Interval value,
  double positive) noexcept
{
  return {down(value.lo / positive), up(value.hi / positive)};
}

[[nodiscard]] inline IntervalCubic bspline_to_bezier(const Cubic& p) noexcept
{
  const std::array<Interval, 4> value {exact(p[0]), exact(p[1]),
    exact(p[2]), exact(p[3])};
  return {divide_positive(add(add(value[0], multiply_positive(value[1], 4.0)),
                              value[2]), 6.0),
          divide_positive(add(multiply_positive(value[1], 2.0), value[2]), 3.0),
          divide_positive(add(value[1], multiply_positive(value[2], 2.0)), 3.0),
          divide_positive(add(add(value[1], multiply_positive(value[2], 4.0)),
                              value[3]), 6.0)};
}

[[nodiscard]] inline IntervalCubic power_to_bezier(const Cubic& p) noexcept
{
  const std::array<Interval, 4> value {exact(p[0]), exact(p[1]),
    exact(p[2]), exact(p[3])};
  // p[0] + p[1]u + p[2]u^2 + p[3]u^3 on u in [0, 1].
  return {value[0], add(value[0], divide_positive(value[1], 3.0)),
          add(value[0], divide_positive(add(multiply_positive(value[1], 2.0),
                                            value[2]), 3.0)),
          add(add(add(value[0], value[1]), value[2]), value[3])};
}

[[nodiscard]] inline bool hull(const IntervalCubic& values, double& lower,
  double& upper) noexcept
{
  if (!std::all_of(values.begin(), values.end(), [](Interval value) {
        return std::isfinite(value.lo) && std::isfinite(value.hi)
          && value.lo <= value.hi;
      })) return false;
  const auto lo = std::min_element(values.begin(), values.end(),
    [](Interval left, Interval right) { return left.lo < right.lo; });
  const auto hi = std::max_element(values.begin(), values.end(),
    [](Interval left, Interval right) { return left.hi < right.hi; });
  lower = lo->lo;
  upper = hi->hi;
  return std::isfinite(lower) && std::isfinite(upper);
}

[[nodiscard]] inline BoundsResult union_bounds(const CubicSpan& authoritative,
  const CubicSpan& compiled) noexcept
{
  if (!supported_binary64()) return {};
  std::array<double, 3> lower {};
  std::array<double, 3> upper {};
  double radius_upper = -infinity;
  for (std::size_t axis = 0; axis < 3; ++axis) {
    if (!finite(authoritative.center[axis]) || !finite(compiled.center[axis])) return {};
    const IntervalCubic a = bspline_to_bezier(authoritative.center[axis]);
    const IntervalCubic b = power_to_bezier(compiled.center[axis]);
    double a_lo, a_hi, b_lo, b_hi;
    if (!hull(a, a_lo, a_hi) || !hull(b, b_lo, b_hi)) return {};
    lower[axis] = down(std::min(a_lo, b_lo));
    upper[axis] = up(std::max(a_hi, b_hi));
  }
  for (const Cubic* controls : {&authoritative.radius, &compiled.radius}) {
    if (!finite(*controls)) return {};
    const IntervalCubic bezier = controls == &authoritative.radius
      ? bspline_to_bezier(*controls) : power_to_bezier(*controls);
    double radius_lo, radius_hi;
    if (!hull(bezier, radius_lo, radius_hi) || radius_lo < 0.0) return {};
    radius_upper = std::max(radius_upper, radius_hi);
  }
  BoundingBox box {{down(lower[0] - radius_upper),
                    down(lower[1] - radius_upper),
                    down(lower[2] - radius_upper)},
                   {up(upper[0] + radius_upper),
                    up(upper[1] + radius_upper),
                    up(upper[2] + radius_upper)}};
  if (!box.valid() || !std::isfinite(radius_upper)
      || !std::isfinite(box.lower.x) || !std::isfinite(box.lower.y)
      || !std::isfinite(box.lower.z) || !std::isfinite(box.upper.x)
      || !std::isfinite(box.upper.y) || !std::isfinite(box.upper.z)) return {};
  return {box, true};
}

[[nodiscard]] inline RayBoundsResult ray_interval_outward(const BoundingBox& box,
  const Vec3& origin, const Vec3& direction) noexcept
{
  if (!supported_binary64() || !box.valid()) return {};
  const std::array<double, 3> lo {box.lower.x, box.lower.y, box.lower.z};
  const std::array<double, 3> hi {box.upper.x, box.upper.y, box.upper.z};
  const std::array<double, 3> point {origin.x, origin.y, origin.z};
  const std::array<double, 3> ray {direction.x, direction.y, direction.z};
  double enter = -infinity;
  double exit = infinity;
  for (std::size_t axis = 0; axis < 3; ++axis) {
    if (!std::isfinite(lo[axis]) || !std::isfinite(hi[axis])
        || !std::isfinite(point[axis]) || !std::isfinite(ray[axis])) return {};
    if (ray[axis] == 0.0) {
      if (point[axis] < lo[axis] || point[axis] > hi[axis]) return {{}, true};
      continue;
    }
    const double delta_lo = down(lo[axis] - point[axis]);
    const double delta_hi = up(hi[axis] - point[axis]);
    if (!std::isfinite(delta_lo) || !std::isfinite(delta_hi)) return {};
    const double axis_enter = ray[axis] > 0.0
      ? down(delta_lo / ray[axis]) : down(delta_hi / ray[axis]);
    const double axis_exit = ray[axis] > 0.0
      ? up(delta_hi / ray[axis]) : up(delta_lo / ray[axis]);
    if (!std::isfinite(axis_enter) || !std::isfinite(axis_exit)) return {};
    enter = std::max(enter, axis_enter);
    exit = std::min(exit, axis_exit);
    if (enter > exit) return {{}, true};
  }
  return {RayInterval {enter, exit}, true};
}

} // namespace stellarcsg::swept_span_bounds

#endif
