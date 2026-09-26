// Reproduce a finite, periodic cubic whose nearest-centerline span is missed.
#include "stellarcsg/compiled_swept_surface.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main()
{
  try {
    stellarcsg::SweptSplineSurfaceData data;
    data.coil_id = 9001;
    data.content_id = "diagnostic-nonunimodal-span";
    data.sample_count = 8;
    data.length = 8.0;
    data.characteristic_length = 30.0;
    data.centerline_coefficients = {
       0.6829578857775811,   0.4558376479511903, -0.24574062740129754,
       1.3166620668636353,  -0.6659930105554357, -0.3817898110933077,
      -9.058890596848563,   10.948100204060806,   3.1376619635957796,
     -20.0,                 20.0,                 0.0,
     -20.0,                  0.0,                 0.0,
     -20.0,                -20.0,                 0.0,
     -10.0,                -15.0,                 0.0,
      -3.6241791045456067,  -3.3552421145334383,  3.2594525742483245};
    for (int i = 0; i < 8; ++i) {
      data.normal_coefficients.insert(data.normal_coefficients.end(),
        {0.0, 0.0, 1.0});
      data.binormal_coefficients.insert(data.binormal_coefficients.end(),
        {0.0, 1.0, 0.0});
    }
    data.major_radius_coefficients.assign(8, 1.0);
    data.minor_radius_coefficients.assign(8, 1.0);
    const stellarcsg::CompiledSweptSplineSurface surface(data);
    const stellarcsg::Vec3 query {0.0, 0.0, 0.0};
    const auto chosen = surface.local_coordinates(query);
    const double chosen_distance_squared = stellarcsg::norm_squared(chosen.center);
    const auto& first_span = surface.spans().front();
    constexpr double witness_u = 0.08048901989047327;
    stellarcsg::Vec3 witness_center;
    for (int axis = 0; axis < 3; ++axis) {
      const double* c = first_span.power.data() + 4 * axis;
      const double value = ((c[3] * witness_u + c[2]) * witness_u
        + c[1]) * witness_u + c[0];
      if (axis == 0) witness_center.x = value;
      else if (axis == 1) witness_center.y = value;
      else witness_center.z = value;
    }
    const double witness_distance_squared =
      stellarcsg::norm_squared(witness_center);
    std::cout << std::setprecision(17)
              << "{\"chosen_arc_coordinate\":" << chosen.arc_coordinate
              << ",\"chosen_distance_squared\":" << chosen_distance_squared
              << ",\"witness_span\":0,\"witness_u\":" << witness_u
              << ",\"witness_distance_squared\":" << witness_distance_squared
              << ",\"missed_nearer_point\":"
              << (chosen_distance_squared > witness_distance_squared + 0.01
                    ? "true" : "false") << "}\n";
    return chosen_distance_squared > witness_distance_squared + 0.01 ? 0 : 2;
  } catch (const std::exception& error) {
    std::cerr << "nearest-centerline probe: " << error.what() << '\n';
    return 1;
  }
}
