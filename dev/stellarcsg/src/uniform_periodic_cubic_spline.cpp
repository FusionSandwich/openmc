#include "stellarcsg/uniform_periodic_cubic_spline.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace stellarcsg {
namespace {

constexpr double two_pi = 2.0 * 3.141592653589793238462643383279502884;

struct Basis {
  std::array<double, 4> value {};
  std::array<double, 4> derivative {};
};

Basis cubic_basis(double u)
{
  const double u2 = u * u;
  const double u3 = u2 * u;
  const double one_minus_u = 1.0 - u;

  Basis basis;
  basis.value[0] = one_minus_u * one_minus_u * one_minus_u / 6.0;
  basis.value[1] = (3.0 * u3 - 6.0 * u2 + 4.0) / 6.0;
  basis.value[2] = (-3.0 * u3 + 3.0 * u2 + 3.0 * u + 1.0) / 6.0;
  basis.value[3] = u3 / 6.0;

  basis.derivative[0] = -0.5 * one_minus_u * one_minus_u;
  basis.derivative[1] = 1.5 * u2 - 2.0 * u;
  basis.derivative[2] = -1.5 * u2 + u + 0.5;
  basis.derivative[3] = 0.5 * u2;
  return basis;
}

double wrap_periodic(double angle)
{
  double wrapped = std::fmod(angle, two_pi);
  if (wrapped < 0.0) wrapped += two_pi;
  if (wrapped >= two_pi) wrapped = 0.0;
  return wrapped;
}

long wrap_index(long index, std::size_t size)
{
  const auto signed_size = static_cast<long>(size);
  long wrapped = index % signed_size;
  if (wrapped < 0) wrapped += signed_size;
  return wrapped;
}

} // namespace

UniformPeriodicCubicSpline::UniformPeriodicCubicSpline(
  std::size_t size, int periodic_multiplier, std::vector<double> coefficients)
  : size_ {size}
  , periodic_multiplier_ {periodic_multiplier}
  , coefficients_ {std::move(coefficients)}
{
  if (size_ < 4) {
    throw std::invalid_argument(
      "Periodic cubic B-spline requires at least four coefficients");
  }
  if (periodic_multiplier_ <= 0) {
    throw std::invalid_argument("Periodic multiplier must be positive");
  }
  if (coefficients_.size() != size_) {
    throw std::invalid_argument("Coefficient count does not match spline size");
  }
  for (const double coefficient_value : coefficients_) {
    if (!std::isfinite(coefficient_value)) {
      throw std::invalid_argument("Spline coefficients must be finite");
    }
  }
  const auto bounds = std::minmax_element(
    coefficients_.begin(), coefficients_.end());
  coefficient_min_ = *bounds.first;
  coefficient_max_ = *bounds.second;
}

double UniformPeriodicCubicSpline::coefficient(long index) const noexcept
{
  return coefficients_[static_cast<std::size_t>(wrap_index(index, size_))];
}

CubicSplineSample UniformPeriodicCubicSpline::sample(double angle) const
{
  if (!std::isfinite(angle)) {
    throw std::invalid_argument("Spline angle must be finite");
  }
  const double reduced = wrap_periodic(
    static_cast<double>(periodic_multiplier_) * angle);
  const double coordinate = reduced * static_cast<double>(size_) / two_pi;
  const auto cell = static_cast<long>(std::floor(coordinate));
  const double u = coordinate - static_cast<double>(cell);
  const Basis basis = cubic_basis(u);
  const double coordinate_scale =
    static_cast<double>(size_ * static_cast<std::size_t>(periodic_multiplier_))
    / two_pi;

  CubicSplineSample result;
  for (long a = 0; a < 4; ++a) {
    const double control = coefficient(cell + a - 1);
    const auto ai = static_cast<std::size_t>(a);
    result.value += control * basis.value[ai];
    result.derivative += control * basis.derivative[ai] * coordinate_scale;
  }
  return result;
}

} // namespace stellarcsg
