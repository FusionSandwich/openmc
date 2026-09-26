// Sample the compiled implicit evaluator's quarter-turn covariance.
// This is a diagnostic of one finite grid, not a continuous error bound.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using stellarcsg::Vec3;
using stellarcsg::SweptSpan;

Vec3 rotate(Vec3 value, int turns)
{
  for (int i = 0; i < turns; ++i) value = {-value.y, value.x, value.z};
  return value;
}

Vec3 point_on_section(const SweptSpan& span, double fraction,
  double alpha, double radial_scale)
{
  const double angle = span.angle_min
    + fraction * (span.angle_max - span.angle_min);
  const double coordinate_scale = 1.0 / (span.angle_max - span.angle_min);
  const double u = (angle - span.angle_min) * coordinate_scale;
  std::array<double, 8> value {};
  std::array<double, 3> derivative {};
  for (std::size_t field = 0; field < value.size(); ++field) {
    const double* c = span.power.data() + 4 * field;
    value[field] = ((c[3] * u + c[2]) * u + c[1]) * u + c[0];
    if (field < derivative.size())
      derivative[field] = ((3.0 * c[3] * u + 2.0 * c[2]) * u + c[1])
        * coordinate_scale;
  }
  const Vec3 center {value[0], value[1], value[2]};
  const Vec3 tangent = stellarcsg::normalized(
    {derivative[0], derivative[1], derivative[2]});
  Vec3 normal {value[3], value[4], value[5]};
  normal = stellarcsg::normalized(
    normal - stellarcsg::dot(normal, tangent) * tangent);
  const Vec3 binormal = stellarcsg::normalized(
    stellarcsg::cross(tangent, normal));
  normal = stellarcsg::cross(binormal, tangent);
  return center + radial_scale * value[6] * std::cos(alpha) * normal
    + radial_scale * value[7] * std::sin(alpha) * binormal;
}

std::string dataset(const std::string& member)
{
  if (member.rfind("coil_", 0) != 0)
    throw std::invalid_argument("Invalid member in pair file");
  return "/coils/" + member;
}

} // namespace

int main(int argc, char** argv)
{
  try {
    if (argc != 3)
      throw std::invalid_argument("usage: probe_native_period_symmetry H5 PAIRS_TXT");
    const std::string h5 = argv[1];
    std::ifstream pairs(argv[2]);
    if (!pairs) throw std::runtime_error("Unable to open pair file");
    std::cout << std::setprecision(17);
    int pair_count = 0;
    std::string canonical_name, image_name;
    int turns;
    while (pairs >> canonical_name >> image_name >> turns) {
      if (turns < 1 || turns > 3)
        throw std::invalid_argument("Quarter-turn count must be 1..3");
      const auto canonical_data = stellarcsg::read_swept_spline_surface_hdf5(
        h5, dataset(canonical_name));
      const auto image_data = stellarcsg::read_swept_spline_surface_hdf5(
        h5, dataset(image_name));
      const stellarcsg::CompiledSweptSplineSurface canonical(canonical_data);
      const stellarcsg::CompiledSweptSplineSurface image(image_data);
      if (canonical.spans().size() != 256 || image.spans().size() != 256)
        throw std::runtime_error("Expected 256 spans per member");
      std::array<double, 3> maxima {};
      std::array<int, 3> sign_disagreements {};
      std::array<int, 3> sample_counts {};
      constexpr std::array<std::size_t, 4> spans {0, 64, 128, 255};
      constexpr std::array<double, 4> fractions {0.0, 1.0e-8, 0.5,
        1.0 - 1.0e-8};
      constexpr std::array<double, 4> alphas {0.0, 1.57079632679489661923,
        3.14159265358979323846, 4.71238898038468985769};
      constexpr std::array<double, 3> scales {0.99, 1.0, 1.01};
      for (const std::size_t span_id : spans)
        for (const double fraction : fractions)
          for (const double alpha : alphas)
            for (std::size_t scale_id = 0; scale_id < scales.size(); ++scale_id) {
              const Vec3 point = point_on_section(
                canonical.spans()[span_id], fraction, alpha, scales[scale_id]);
              const double first = canonical.evaluate(point);
              const double second = image.evaluate(rotate(point, turns));
              if (!std::isfinite(first) || !std::isfinite(second))
                throw std::runtime_error("Nonfinite implicit evaluation");
              maxima[scale_id] = std::max(maxima[scale_id],
                std::abs(first - second));
              if (std::signbit(first) != std::signbit(second))
                ++sign_disagreements[scale_id];
              ++sample_counts[scale_id];
            }
      std::cout << "{\"canonical\":\"" << canonical_name
                << "\",\"image\":\"" << image_name
                << "\",\"turns\":" << turns << ",\"samples_per_scale\":["
                << sample_counts[0] << ',' << sample_counts[1] << ','
                << sample_counts[2] << "],\"max_abs_implicit_difference\":["
                << maxima[0] << ',' << maxima[1] << ',' << maxima[2]
                << "],\"sign_disagreements\":["
                << sign_disagreements[0] << ',' << sign_disagreements[1]
                << ',' << sign_disagreements[2] << "]}\n";
      ++pair_count;
    }
    if (!pairs.eof() || pair_count != 36)
      throw std::runtime_error("Expected exactly 36 complete rotational pairs");
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native period symmetry probe: " << error.what() << '\n';
    return 1;
  }
}
