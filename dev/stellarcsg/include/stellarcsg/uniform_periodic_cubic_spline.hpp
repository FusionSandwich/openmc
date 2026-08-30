#ifndef STELLARCSG_UNIFORM_PERIODIC_CUBIC_SPLINE_HPP
#define STELLARCSG_UNIFORM_PERIODIC_CUBIC_SPLINE_HPP

#include <cstddef>
#include <utility>
#include <vector>

namespace stellarcsg {

struct CubicSplineSample {
  double value {0.0};
  double derivative {0.0};
};

// Uniform cardinal cubic B-spline with periodic control coefficients.
// The input angle is multiplied by periodic_multiplier before it is mapped to
// the spline's 0..2pi reduced phase. The returned derivative is with respect
// to the physical input angle.
class UniformPeriodicCubicSpline {
public:
  UniformPeriodicCubicSpline(std::size_t size, int periodic_multiplier,
    std::vector<double> coefficients);

  [[nodiscard]] CubicSplineSample sample(double angle) const;
  [[nodiscard]] double value(double angle) const { return sample(angle).value; }

  [[nodiscard]] std::size_t size() const noexcept { return size_; }
  [[nodiscard]] int periodic_multiplier() const noexcept
  {
    return periodic_multiplier_;
  }
  [[nodiscard]] const std::vector<double>& coefficients() const noexcept
  {
    return coefficients_;
  }
  [[nodiscard]] std::pair<double, double> coefficient_bounds() const noexcept
  {
    return {coefficient_min_, coefficient_max_};
  }

private:
  std::size_t size_;
  int periodic_multiplier_;
  std::vector<double> coefficients_;
  double coefficient_min_ {0.0};
  double coefficient_max_ {0.0};

  [[nodiscard]] double coefficient(long index) const noexcept;
};

} // namespace stellarcsg

#endif
