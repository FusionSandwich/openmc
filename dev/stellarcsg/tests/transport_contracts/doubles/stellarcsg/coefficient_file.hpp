#pragma once
#include "stellarcsg/compiled_periodic_surface.hpp"
namespace stellarcsg {
inline PeriodicSplineSurfaceData read_periodic_spline_surface_hdf5(
  const std::string& file,const std::string& group,const std::string& expected="") {
  return read_test_payload(file,group,expected);
}
}
