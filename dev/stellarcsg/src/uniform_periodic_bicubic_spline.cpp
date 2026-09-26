#include "stellarcsg/uniform_periodic_bicubic_spline.hpp"

#include <array>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace stellarcsg {
namespace {

constexpr double two_pi = 2.0 * 3.141592653589793238462643383279502884;

double wrap_periodic(double angle)
{
  double wrapped = std::fmod(angle, two_pi);
  if (wrapped < 0.0) {
    wrapped += two_pi;
  }
  if (wrapped >= two_pi) {
    wrapped = 0.0;
  }
  return wrapped;
}

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

long wrap_index(long index, std::size_t size)
{
  const auto signed_size = static_cast<long>(size);
  long wrapped = index % signed_size;
  if (wrapped < 0) {
    wrapped += signed_size;
  }
  return wrapped;
}

} // namespace

UniformPeriodicBicubicSpline::UniformPeriodicBicubicSpline(
  std::size_t n_theta, std::size_t n_phi, int n_field_periods,
  std::vector<double> coefficients)
  : n_theta_ {n_theta}
  , n_phi_ {n_phi}
  , n_field_periods_ {n_field_periods}
  , coefficients_ {std::move(coefficients)}
{
  if (n_theta_ < 4 || n_phi_ < 4) {
    throw std::invalid_argument(
      "Periodic cubic B-splines require at least four coefficients per dimension");
  }
  if (n_field_periods_ <= 0) {
    throw std::invalid_argument("Field-period count must be positive");
  }
  if (coefficients_.size() != n_theta_ * n_phi_) {
    throw std::invalid_argument("Coefficient array size does not match spline dimensions");
  }
  for (const double coefficient : coefficients_) {
    if (!std::isfinite(coefficient)) {
      throw std::invalid_argument("Spline coefficients must be finite");
    }
  }
}

double UniformPeriodicBicubicSpline::coefficient(
  long theta_index, long phi_index) const
{
  const auto i = static_cast<std::size_t>(wrap_index(theta_index, n_theta_));
  const auto j = static_cast<std::size_t>(wrap_index(phi_index, n_phi_));
  return coefficients_[i * n_phi_ + j];
}

SplineSample UniformPeriodicBicubicSpline::sample(double theta, double phi) const
{
  const double wrapped_theta = wrap_periodic(theta);
  const double reduced_phi = wrap_periodic(static_cast<double>(n_field_periods_) * phi);

  const double theta_coordinate =
    wrapped_theta * static_cast<double>(n_theta_) / two_pi;
  const double phi_coordinate = reduced_phi * static_cast<double>(n_phi_) / two_pi;

  const auto theta_cell = static_cast<long>(std::floor(theta_coordinate));
  const auto phi_cell = static_cast<long>(std::floor(phi_coordinate));
  const double u = theta_coordinate - static_cast<double>(theta_cell);
  const double v = phi_coordinate - static_cast<double>(phi_cell);

  const Basis theta_basis = cubic_basis(u);
  const Basis phi_basis = cubic_basis(v);
  const double dtheta_coordinate_dtheta = static_cast<double>(n_theta_) / two_pi;
  const double dphi_coordinate_dphi =
    static_cast<double>(n_phi_ * static_cast<std::size_t>(n_field_periods_)) / two_pi;

  SplineSample result;
  for (long a = 0; a < 4; ++a) {
    for (long b = 0; b < 4; ++b) {
      const double control = coefficient(theta_cell + a - 1, phi_cell + b - 1);
      const auto ai = static_cast<std::size_t>(a);
      const auto bi = static_cast<std::size_t>(b);
      result.value += control * theta_basis.value[ai] * phi_basis.value[bi];
      result.dtheta += control * theta_basis.derivative[ai]
                       * dtheta_coordinate_dtheta * phi_basis.value[bi];
      result.dphi += control * theta_basis.value[ai]
                     * phi_basis.derivative[bi] * dphi_coordinate_dphi;
    }
  }
  return result;
}

} // namespace stellarcsg
