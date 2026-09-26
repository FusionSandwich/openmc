// Diagnostic copy of the last-span stationary/Newton arithmetic in the
// compiled swept evaluator. It is not a certificate of root completeness.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
using stellarcsg::SweptSpan;

std::string hex(double value)
{
  std::ostringstream out;
  out << std::hexfloat << value;
  return out.str();
}

long double polynomial_value(
  const std::array<long double, 6>& coefficients, int degree, long double u)
{
  long double value = coefficients[static_cast<std::size_t>(degree)];
  for (int term = degree - 1; term >= 0; --term)
    value = value * u + coefficients[static_cast<std::size_t>(term)];
  return value;
}

void probe(const stellarcsg::CompiledSweptSplineSurface& surface,
           const SweptSpan& span, int member, double t)
{
  const stellarcsg::Vec3 point {550.0 - t, 0.0, 0.0};
  const std::array<long double, 3> query {
    static_cast<long double>(point.x), static_cast<long double>(point.y),
    static_cast<long double>(point.z)};
  std::array<std::array<long double, 4>, 3> center {};
  std::array<long double, 6> stationary {};
  for (std::size_t axis = 0; axis < 3; ++axis) {
    for (std::size_t term = 0; term < 4; ++term)
      center[axis][term] = static_cast<long double>(
        span.power[4 * axis + term]);
    std::array<long double, 4> offset = center[axis];
    offset[0] -= query[axis];
    for (std::size_t i = 0; i < offset.size(); ++i)
      for (std::size_t j = 0; j < 3; ++j)
        stationary[i + j] += offset[i] * static_cast<long double>(j + 1)
          * center[axis][j + 1];
  }
  const auto distance_squared = [&](long double u) {
    long double result = 0.0L;
    for (std::size_t axis = 0; axis < 3; ++axis) {
      const auto& c = center[axis];
      const long double difference = ((c[3] * u + c[2]) * u + c[1]) * u
        + c[0] - query[axis];
      result += difference * difference;
    }
    return result;
  };
  long double best_u = 0.0L;
  long double best_distance = distance_squared(best_u);
  const auto consider = [&](long double u) {
    const long double distance = distance_squared(u);
    if (distance < best_distance) {
      best_distance = distance;
      best_u = u;
    }
  };
  const std::array<long double, 5> slope {
    stationary[1], 2.0L * stationary[2], 3.0L * stationary[3],
    4.0L * stationary[4], 5.0L * stationary[5]};
  const std::array<long double, 5> bernstein {
    slope[0], slope[0] + slope[1] / 4.0L,
    slope[0] + slope[1] / 2.0L + slope[2] / 6.0L,
    slope[0] + 3.0L * slope[1] / 4.0L + slope[2] / 2.0L
      + slope[3] / 4.0L,
    slope[0] + slope[1] + slope[2] + slope[3] + slope[4]};
  long double slope_scale = 0.0L;
  for (const long double value : slope) slope_scale += std::abs(value);
  const long double margin = 64.0L
    * std::numeric_limits<long double>::epsilon() * slope_scale;
  const bool strictly_convex = std::all_of(bernstein.begin(), bernstein.end(),
    [&](long double value) { return value > margin; });
  const long double first = polynomial_value(stationary, 5, 0.0L);
  const long double last = polynomial_value(stationary, 5, 1.0L);
  if (!strictly_convex || !(first < 0.0L && last > 0.0L))
    throw std::runtime_error("last seam span did not take convex root branch");
  std::array<long double, 6> slope_power {};
  std::copy(slope.begin(), slope.end(), slope_power.begin());
  long double left = 0.0L, right = 1.0L, u = 0.5L;
  int midpoint_steps = 0, newton_steps = 0;
  int first_small_iteration = -1;
  int iterations = 0;
  std::string stop = "iteration_cap";
  for (int iteration = 0; iteration < 80; ++iteration) {
    iterations = iteration + 1;
    const long double value = polynomial_value(stationary, 5, u);
    if (std::abs(value) < 1.0e-14L && first_small_iteration < 0)
      first_small_iteration = iteration;
    if (value == 0.0L) { stop = "zero_value"; break; }
    if (value < 0.0L) left = u;
    else right = u;
    const long double derivative = polynomial_value(slope_power, 4, u);
    long double next = derivative > 0.0L
      ? u - value / derivative : left + 0.5L * (right - left);
    bool used_newton = derivative > 0.0L && next > left && next < right;
    if (!used_newton)
      next = left + 0.5L * (right - left);
    if (used_newton) ++newton_steps;
    else ++midpoint_steps;
    if (next == u) { stop = "stagnant"; break; }
    u = next;
  }
  consider(u);
  consider(1.0L);
  const double q = span.angle_min
    + static_cast<double>(best_u) * (span.angle_max - span.angle_min);
  const auto local = surface.local_coordinates(point);
  std::cout << std::setprecision(21)
            << "{\"member\":" << member << ",\"t_cm\":"
            << std::setprecision(17) << t
            << ",\"point_x_hex\":\"" << hex(point.x) << '\"'
            << ",\"iterations\":" << iterations
            << ",\"midpoint_steps\":" << midpoint_steps
            << ",\"newton_steps\":" << newton_steps
            << ",\"first_small_iteration\":" << first_small_iteration
            << ",\"stop\":\"" << stop << '\"'
            << ",\"loop_u\":" << std::setprecision(21) << u
            << ",\"loop_residual\":"
            << polynomial_value(stationary, 5, u)
            << ",\"best_u\":" << best_u
            << ",\"q_hex\":\"" << hex(q) << '\"'
            << ",\"compiled_arc_coordinate_cm\":"
            << std::setprecision(17) << local.arc_coordinate
            << ",\"compiled_center_cm\":[" << local.center.x << ','
            << local.center.y << ',' << local.center.z << "]}\n";
}
} // namespace

int main(int argc, char** argv)
{
  try {
    if (argc < 4)
      throw std::invalid_argument("Usage: probe_compiled_seam_newton H5 MEMBER T...");
    const int member = std::stoi(argv[2]);
    if (member != 2 && member != 3)
      throw std::invalid_argument("member must be 2 or 3");
    const auto data = stellarcsg::read_swept_spline_surface_hdf5(
      argv[1], "/coils/coil_00" + std::to_string(member));
    const stellarcsg::CompiledSweptSplineSurface surface {data, true};
    const auto& span = surface.spans().back();
    for (int index = 3; index < argc; ++index) {
      const double t = std::stod(argv[index]);
      if (!std::isfinite(t))
        throw std::invalid_argument("distance must be finite");
      probe(surface, span, member, t);
    }
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
