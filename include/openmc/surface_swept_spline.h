#ifndef OPENMC_SURFACE_SWEPT_SPLINE_H
#define OPENMC_SURFACE_SWEPT_SPLINE_H

#include "openmc/surface.h"
#include "stellarcsg/compiled_swept_surface.hpp"

#include <memory>
#include <string>

namespace openmc {

class SurfaceSweptSpline final : public Surface {
public:
  explicit SurfaceSweptSpline(pugi::xml_node surf_node);
  ~SurfaceSweptSpline() override;
  double evaluate(Position r) const override;
  double distance(Position r, Direction u, bool coincident) const override;
  Direction normal(Position r) const override;
  BoundingBox bounding_box(bool pos_side) const override;
  void to_hdf5_inner(hid_t group_id) const override;

private:
  std::string data_file_;
  std::string dataset_;
  std::string content_id_;
  std::unique_ptr<stellarcsg::CompiledSweptSplineSurface> surface_;
};

} // namespace openmc

#endif
