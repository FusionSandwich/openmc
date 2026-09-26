#pragma once
#include "stellarcsg/compiled_swept_surface.hpp"
namespace stellarcsg {
inline SweptSplineSurfaceData read_swept_spline_surface_hdf5(
  const std::string& file,const std::string& group,const std::string& expected="") {
  return read_test_payload(file,group,expected);
}
}
