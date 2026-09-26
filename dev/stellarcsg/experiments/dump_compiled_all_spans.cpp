// Dump every analytic shaped span from the actual compiled surface instance.
// Read-only diagnostic; not a root, floating-bound, or transport certificate.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
std::string bits(double value)
{
  std::ostringstream out;
  out << std::hexfloat << value;
  return out.str();
}

void inspect(const std::string& filename, int member)
{
  const auto dataset = "/coils/coil_00" + std::to_string(member);
  const auto data = stellarcsg::read_swept_spline_surface_hdf5(
    filename, dataset);
  const stellarcsg::CompiledSweptSplineSurface surface {data, true};
  const auto& spans = surface.spans();
  if (spans.size() != data.sample_count)
    throw std::runtime_error("unexpected compiled span count");
  for (std::size_t index = 0; index < spans.size(); ++index) {
    const auto& span = spans[index];
    std::cout << "{\"member\":" << member << ",\"sample_count\":"
              << data.sample_count << ",\"span\":" << index
              << ",\"angle_min_hex\":\"" << bits(span.angle_min)
              << "\",\"angle_max_hex\":\"" << bits(span.angle_max)
              << "\",\"power_hex\":[";
    for (std::size_t field = 0; field < 8; ++field) {
      if (field) std::cout << ',';
      std::cout << '[';
      for (std::size_t order = 0; order < 4; ++order) {
        if (order) std::cout << ',';
        std::cout << '"' << bits(span.power[4 * field + order]) << '"';
      }
      std::cout << ']';
    }
    std::cout << "]}\n";
  }
}
} // namespace

int main(int argc, char** argv)
{
  try {
    if (argc != 2)
      throw std::invalid_argument("Usage: dump_compiled_all_spans H5");
    inspect(argv[1], 2);
    inspect(argv[1], 3);
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
