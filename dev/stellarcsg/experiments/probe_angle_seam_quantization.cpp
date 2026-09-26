// Reproduce the angle-to-local-u arithmetic used by build_spans/frame_in_span.
// This tests representable inputs, not a swept-surface hit or root certificate.
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>

namespace {
std::string bits(double value)
{
  std::ostringstream out;
  out << std::hexfloat << value;
  return out.str();
}

void inspect(int member, int count)
{
  constexpr double two_pi =
    2.0 * 3.141592653589793238462643383279502884;
  const double step = two_pi / static_cast<double>(count);
  const int span = count - 1;
  const double angle_min = step * static_cast<double>(span);
  const double angle_max = angle_min + step;
  const double scale = 1.0 / (angle_max - angle_min);
  const double predecessor = std::nextafter(angle_max,
    -std::numeric_limits<double>::infinity());
  const double two_below = std::nextafter(predecessor,
    -std::numeric_limits<double>::infinity());
  const double successor = std::nextafter(angle_max,
    std::numeric_limits<double>::infinity());
  const double angles[] {two_below, predecessor, angle_max, successor};
  const char* labels[] {"two_below", "predecessor", "endpoint", "successor"};
  std::cout << std::setprecision(17)
            << "{\"member\":" << member << ",\"count\":" << count
            << ",\"span\":" << span << ",\"two_pi_hex\":\""
            << bits(two_pi) << "\",\"angle_min_hex\":\""
            << bits(angle_min) << "\",\"angle_max_hex\":\""
            << bits(angle_max) << "\",\"scale_hex\":\""
            << bits(scale) << "\",\"samples\":[";
  for (int k = 0; k < 4; ++k) {
    const double u = (angles[k] - angle_min) * scale;
    if (k) std::cout << ',';
    std::cout << "{\"label\":\"" << labels[k]
              << "\",\"angle_hex\":\"" << bits(angles[k])
              << "\",\"u_hex\":\"" << bits(u)
              << "\",\"u\":" << u << '}';
  }
  std::cout << "]}\n";
}
} // namespace

int main()
{
  inspect(2, 256);
  inspect(3, 384);
}
