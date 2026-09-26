// Read-only point probes of the actual compiled implicit swept evaluator.
// The output is diagnostic only and does not certify an earlier-root interval.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
  try {
    if (argc < 4) {
      throw std::invalid_argument(
        "Usage: probe_compiled_seam_implicit H5 MEMBER T_CM [T_CM ...]");
    }
    const int member = std::stoi(argv[2]);
    if (member != 2 && member != 3)
      throw std::invalid_argument("member must be 2 or 3");
    const auto dataset = "/coils/coil_00" + std::to_string(member);
    const auto data = stellarcsg::read_swept_spline_surface_hdf5(
      argv[1], dataset);
    const stellarcsg::CompiledSweptSplineSurface surface {data, true};
    std::cout << std::setprecision(17);
    for (int index = 3; index < argc; ++index) {
      const double t = std::stod(argv[index]);
      if (!std::isfinite(t))
        throw std::invalid_argument("nonfinite distance");
      const stellarcsg::Vec3 point {550.0 - t, 0.0, 0.0};
      const auto local = surface.local_coordinates(point);
      const double value = surface.evaluate(point);
      std::cout << "{\"member\":" << member << ",\"t_cm\":" << t
                << ",\"point_x_cm\":" << point.x
                << ",\"implicit_value\":" << value
                << ",\"arc_coordinate_cm\":" << local.arc_coordinate
                << ",\"center_cm\":[" << local.center.x << ','
                << local.center.y << ',' << local.center.z << ']'
                << ",\"normal\":[" << local.normal.x << ','
                << local.normal.y << ',' << local.normal.z << ']'
                << ",\"binormal\":[" << local.binormal.x << ','
                << local.binormal.y << ',' << local.binormal.z << ']'
                << ",\"major_radius_cm\":" << local.major_radius
                << ",\"minor_radius_cm\":" << local.minor_radius
                << ",\"local_u_cm\":" << local.u
                << ",\"local_v_cm\":" << local.v << "}\n";
    }
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
