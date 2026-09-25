#ifndef STELLARCSG_SWEPT_COEFFICIENT_FILE_HPP
#define STELLARCSG_SWEPT_COEFFICIENT_FILE_HPP

#include "stellarcsg/compiled_swept_surface.hpp"

#include <string>

namespace stellarcsg {

[[nodiscard]] std::string swept_spline_content_id(
  const SweptSplineSurfaceData& data);
[[nodiscard]] SweptSplineSurfaceData read_swept_spline_surface_hdf5(
  const std::string& filename, const std::string& dataset,
  const std::string& expected_content_id = {});

} // namespace stellarcsg

#endif
