#ifndef STELLARCSG_VECTOR_HPP
#define STELLARCSG_VECTOR_HPP

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <optional>
#include <stdexcept>

namespace stellarcsg {

struct Vec3 {
  double x {0.0};
  double y {0.0};
  double z {0.0};

  constexpr Vec3() = default;
  constexpr Vec3(double x_, double y_, double z_) : x {x_}, y {y_}, z {z_} {}

  constexpr Vec3& operator+=(const Vec3& other)
  {
    x += other.x;
    y += other.y;
    z += other.z;
    return *this;
  }

  constexpr Vec3& operator-=(const Vec3& other)
  {
    x -= other.x;
    y -= other.y;
    z -= other.z;
    return *this;
  }

  constexpr Vec3& operator*=(double scalar)
  {
    x *= scalar;
    y *= scalar;
    z *= scalar;
    return *this;
  }
};

constexpr Vec3 operator+(Vec3 lhs, const Vec3& rhs)
{
  lhs += rhs;
  return lhs;
}

constexpr Vec3 operator-(Vec3 lhs, const Vec3& rhs)
{
  lhs -= rhs;
  return lhs;
}

constexpr Vec3 operator-(const Vec3& value)
{
  return {-value.x, -value.y, -value.z};
}

constexpr Vec3 operator*(Vec3 value, double scalar)
{
  value *= scalar;
  return value;
}

constexpr Vec3 operator*(double scalar, Vec3 value)
{
  value *= scalar;
  return value;
}

constexpr Vec3 operator/(Vec3 value, double scalar)
{
  if ((scalar >= 1.0e-300 && scalar <= 1.0e300)
      || (scalar <= -1.0e-300 && scalar >= -1.0e300)) {
    value *= 1.0 / scalar;
  } else {
    value.x /= scalar;
    value.y /= scalar;
    value.z /= scalar;
  }
  return value;
}

constexpr double dot(const Vec3& lhs, const Vec3& rhs)
{
  return lhs.x * rhs.x + lhs.y * rhs.y + lhs.z * rhs.z;
}

constexpr Vec3 cross(const Vec3& lhs, const Vec3& rhs)
{
  return {lhs.y * rhs.z - lhs.z * rhs.y,
    lhs.z * rhs.x - lhs.x * rhs.z,
    lhs.x * rhs.y - lhs.y * rhs.x};
}

constexpr double norm_squared(const Vec3& value)
{
  return dot(value, value);
}

inline double norm(const Vec3& value)
{
  const double scale = std::max({
    std::abs(value.x), std::abs(value.y), std::abs(value.z)});
  if (scale < 1.0e-150 || scale > 1.0e150)
    return std::hypot(value.x, value.y, value.z);
  return std::sqrt(norm_squared(value));
}

inline Vec3 normalized(const Vec3& value)
{
  const double magnitude = norm(value);
  if (!(magnitude > 0.0) || !std::isfinite(magnitude)) {
    throw std::domain_error("Cannot normalize a zero or non-finite vector");
  }
  if (magnitude < 1.0e-150 || magnitude > 1.0e150)
    return {value.x / magnitude, value.y / magnitude,
      value.z / magnitude};
  return value / magnitude;
}

struct RayInterval {
  double enter {0.0};
  double exit {0.0};
};

struct BoundingBox {
  Vec3 lower {};
  Vec3 upper {};

  [[nodiscard]] bool valid() const noexcept
  {
    return lower.x <= upper.x && lower.y <= upper.y && lower.z <= upper.z;
  }

  [[nodiscard]] std::optional<RayInterval> ray_interval(
    const Vec3& origin, const Vec3& direction) const
  {
    if (!valid()) {
      throw std::invalid_argument("Bounding box lower corner exceeds upper corner");
    }
    if (!std::isfinite(origin.x) || !std::isfinite(origin.y)
        || !std::isfinite(origin.z) || !std::isfinite(direction.x)
        || !std::isfinite(direction.y) || !std::isfinite(direction.z)) {
      throw std::invalid_argument("Ray origin and direction must be finite");
    }

    double t_enter = -std::numeric_limits<double>::infinity();
    double t_exit = std::numeric_limits<double>::infinity();

    const std::array<double, 3> o {origin.x, origin.y, origin.z};
    const std::array<double, 3> d {direction.x, direction.y, direction.z};
    const std::array<double, 3> lo {lower.x, lower.y, lower.z};
    const std::array<double, 3> hi {upper.x, upper.y, upper.z};

    for (std::size_t i = 0; i < 3; ++i) {
      if (d[i] == 0.0) {
        if (o[i] < lo[i] || o[i] > hi[i]) {
          return std::nullopt;
        }
        continue;
      }
      // Bound both rounded subtractions before division, then widen the
      // rounded quotients. If an intermediate overflows, retain the entire
      // axis instead of risking a false ray-box exclusion.
      if (!std::isfinite(lo[i]) || !std::isfinite(hi[i])) continue;
      const double lower_difference = lo[i] - o[i];
      const double upper_difference = hi[i] - o[i];
      if (!std::isfinite(lower_difference)
          || !std::isfinite(upper_difference)) continue;
      const double lower_difference_down = std::nextafter(
        lower_difference, -std::numeric_limits<double>::infinity());
      const double upper_difference_up = std::nextafter(
        upper_difference, std::numeric_limits<double>::infinity());
      const double raw_enter = d[i] > 0.0
        ? lower_difference_down / d[i] : upper_difference_up / d[i];
      const double raw_exit = d[i] > 0.0
        ? upper_difference_up / d[i] : lower_difference_down / d[i];
      if (!std::isfinite(raw_enter) || !std::isfinite(raw_exit)) continue;
      const double a = std::nextafter(
        raw_enter, -std::numeric_limits<double>::infinity());
      const double b = std::nextafter(
        raw_exit, std::numeric_limits<double>::infinity());
      if (a > b) {
        throw std::logic_error("Invalid widened ray-box slab interval");
      }
      t_enter = std::max(t_enter, a);
      t_exit = std::min(t_exit, b);
      if (t_enter > t_exit) {
        return std::nullopt;
      }
    }

    return RayInterval {t_enter, t_exit};
  }
};

} // namespace stellarcsg

#endif
