#include "stellarcsg/coefficient_file.hpp"
#include "stellarcsg/compiled_periodic_surface.hpp"

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
#ifndef STELLARCSG_HAS_HDF5
  std::cerr << "This tool requires STELLARCSG_ENABLE_HDF5=ON\n";
  return EXIT_FAILURE;
#else
  if (argc != 6 && argc != 7) {
    std::cerr << "usage: " << argv[0]
              << " FILE DATASET X_CM Y_CM Z_CM [EXPECTED_CONTENT_ID]\n";
    return EXIT_FAILURE;
  }
  try {
    const std::string expected = argc == 7 ? argv[6] : "";
    auto data = stellarcsg::read_periodic_spline_surface_hdf5(
      argv[1], argv[2], expected);
    const std::string content_id = data.content_id;
    const stellarcsg::CompiledPeriodicSplineSurface surface {std::move(data)};
    const stellarcsg::Vec3 point {
      std::stod(argv[3]), std::stod(argv[4]), std::stod(argv[5])};
    const double value = surface.evaluate(point);
    const auto local_box = surface.bounding_box();
    std::cout << std::setprecision(17)
              << "{\n"
              << "  \"schema_version\": 1,\n"
              << "  \"content_id\": \"" << content_id << "\",\n"
              << "  \"evaluate_cm\": " << value << ",\n"
              << "  \"bounding_box_cm\": [["
              << local_box.lower.x << ", " << local_box.lower.y << ", "
              << local_box.lower.z << "], [" << local_box.upper.x << ", "
              << local_box.upper.y << ", " << local_box.upper.z << "]]\n"
              << "}\n";
  } catch (const std::exception& error) {
    std::cerr << "stellarcsg_inspect_surface: " << error.what() << '\n';
    return EXIT_FAILURE;
  }
  return EXIT_SUCCESS;
#endif
}
