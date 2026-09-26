// Export the exact binary64 bounding box of a selected swept-coil set.
#include "stellarcsg/compiled_swept_surface_set.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
std::string hex(double value)
{
  std::ostringstream out;
  out << std::hexfloat << value;
  return out.str();
}
}

int main(int argc, char** argv)
{
  try {
    if (argc < 3)
      throw std::invalid_argument("Usage: dump_compiled_set_box H5 ID [ID...]");
    std::vector<stellarcsg::SweptSplineSurfaceData> members;
    members.reserve(static_cast<std::size_t>(argc - 2));
    for (int index = 2; index < argc; ++index) {
      std::size_t consumed = 0;
      const int id = std::stoi(argv[index], &consumed);
      if (consumed != std::string(argv[index]).size() || id < 0)
        throw std::invalid_argument("invalid member ID");
      members.push_back(stellarcsg::read_swept_spline_surface_hdf5(
        argv[1], "/coils/coil_" + [&] {
          std::ostringstream padded;
          padded.width(3);
          padded.fill('0');
          padded << id;
          return padded.str();
        }()));
    }
    const stellarcsg::CompiledSweptSplineSurfaceSet surface {
      std::move(members)};
    const auto& box = surface.bounding_box();
    std::cout << "{\"member_count\":" << surface.size()
              << ",\"lower_hex\":[\"" << hex(box.lower.x) << "\",\""
              << hex(box.lower.y) << "\",\"" << hex(box.lower.z)
              << "\"],\"upper_hex\":[\"" << hex(box.upper.x)
              << "\",\"" << hex(box.upper.y) << "\",\""
              << hex(box.upper.z) << "\"]}\n";
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
