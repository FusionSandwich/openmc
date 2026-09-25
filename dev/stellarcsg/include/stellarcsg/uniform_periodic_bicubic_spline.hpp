#ifndef STELLARCSG_UNIFORM_PERIODIC_BICUBIC_SPLINE_HPP
#define STELLARCSG_UNIFORM_PERIODIC_BICUBIC_SPLINE_HPP

#include <cstddef>
#include <vector>

namespace stellarcsg {

struct SplineSample {
  double value {0.0};
  double dtheta {0.0};
  double dphi {0.0};
};

// Uniform, tensor-product, periodic cubic B-spline coefficient field.
// The second parameter is the reduced toroidal phase psi = nfp * phi.
class UniformPeriodicBicubicSpline {
public:
  UniformPeriodicBicubicSpline(std::size_t n_theta, std::size_t n_phi,
    int n_field_periods, std::vector<double> coefficients);

  [[nodiscard]] SplineSample sample(double theta, double phi) const;

  [[nodiscard]] std::size_t n_theta() const noexcept { return n_theta_; }
  [[nodiscard]] std::size_t n_phi() const noexcept { return n_phi_; }
  [[nodiscard]] int n_field_periods() const noexcept { return n_field_periods_; }
  [[nodiscard]] const std::vector<double>& coefficients() const noexcept
  {
    return coefficients_;
  }

private:
  std::size_t n_theta_;
  std::size_t n_phi_;
  int n_field_periods_;
  std::vector<double> coefficients_;

  [[nodiscard]] double coefficient(long theta_index, long phi_index) const;
};

} // namespace stellarcsg

#endif
