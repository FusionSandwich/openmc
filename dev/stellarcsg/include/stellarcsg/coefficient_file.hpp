#ifndef STELLARCSG_COEFFICIENT_FILE_HPP
#define STELLARCSG_COEFFICIENT_FILE_HPP

#include "stellarcsg/compiled_periodic_surface.hpp"

#include <string>

namespace stellarcsg {

enum class CoefficientFileMode { truncate, append };

#ifdef STELLARCSG_HAS_HDF5
void write_periodic_spline_surface_hdf5(const std::string& filename,
  const std::string& dataset, const PeriodicSplineSurfaceData& data,
  bool overwrite = false,
  CoefficientFileMode mode = CoefficientFileMode::append);

[[nodiscard]] PeriodicSplineSurfaceData read_periodic_spline_surface_hdf5(
  const std::string& filename, const std::string& dataset,
  const std::string& expected_content_id = {});
#endif

} // namespace stellarcsg

#endif
