#ifndef OPENMC_SURFACE_PERIODIC_SPLINE_H
#define OPENMC_SURFACE_PERIODIC_SPLINE_H

#include "openmc/surface.h"
#include "stellarcsg/compiled_periodic_surface.hpp"

#include <memory>
#include <string>

namespace openmc {

// Experimental, opt-in OpenMC wrapper around the independently testable
// StellarCSG kernel. Ordinary OpenMC builds do not contain this surface.
class SurfacePeriodicSpline final : public Surface {
public:
  explicit SurfacePeriodicSpline(pugi::xml_node surf_node);

  double evaluate(Position r) const override;
  double distance(Position r, Direction u, bool coincident) const override;
  Direction normal(Position r) const override;
  BoundingBox bounding_box(bool pos_side) const override;
  void to_hdf5_inner(hid_t group_id) const override;

private:
  std::string data_file_;
  std::string resolved_data_file_;
  std::string dataset_;
  std::string content_id_;
  std::string solver_ {"fast"};
  std::unique_ptr<stellarcsg::CompiledPeriodicSplineSurface> surface_;
};

} // namespace openmc

#endif
