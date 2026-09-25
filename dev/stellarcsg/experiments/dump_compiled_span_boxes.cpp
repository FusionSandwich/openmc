// Export actual compiled span powers and centerline boxes for an exact audit.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
std::string hex(double value)
{
  std::ostringstream out;
  out << std::hexfloat << value;
  return out.str();
}

void member(const std::string& path, int id)
{
  const auto data = stellarcsg::read_swept_spline_surface_hdf5(
    path, "/coils/coil_00" + std::to_string(id));
  const stellarcsg::CompiledSweptSplineSurface surface {data, true};
  if (surface.spans().size() != data.sample_count)
    throw std::runtime_error("unexpected span count");
  for (std::size_t index = 0; index < surface.spans().size(); ++index) {
    const auto& span = surface.spans()[index];
    const auto& box = span.centerline_bbox;
    std::cout << "{\"member\":" << id << ",\"span\":" << index
              << ",\"angle_min_hex\":\"" << hex(span.angle_min)
              << "\",\"angle_max_hex\":\"" << hex(span.angle_max)
              << "\",\"lower_hex\":[\"" << hex(box.lower.x)
              << "\",\"" << hex(box.lower.y) << "\",\""
              << hex(box.lower.z) << "\"],\"upper_hex\":[\""
              << hex(box.upper.x) << "\",\"" << hex(box.upper.y)
              << "\",\"" << hex(box.upper.z) << "\"],\"power_hex\":[";
    for (std::size_t axis = 0; axis < 3; ++axis) {
      if (axis) std::cout << ',';
      std::cout << '[';
      for (std::size_t order = 0; order < 4; ++order) {
        if (order) std::cout << ',';
        std::cout << '\"' << hex(span.power[4 * axis + order]) << '\"';
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
      throw std::invalid_argument("Usage: dump_compiled_span_boxes H5");
    member(argv[1], 2);
    member(argv[1], 3);
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
