#ifndef OPENMC_SURFACE_FACET_SET_H
#define OPENMC_SURFACE_FACET_SET_H

#include "openmc/surface.h"
#include "stellarcsg/compiled_facet_surface_set.hpp"

#include <memory>
#include <string>

namespace openmc {

class SurfaceFacetSet final : public Surface {
public:
  explicit SurfaceFacetSet(pugi::xml_node surf_node);
  double evaluate(Position r) const override;
  double distance(Position r, Direction u, bool coincident) const override;
  Direction normal(Position r) const override;
  BoundingBox bounding_box(bool pos_side) const override;
  void to_hdf5_inner(hid_t group_id) const override;

private:
  std::string data_file_;
  std::string dataset_;
  std::string content_id_;
  std::string periodic_caps_;
  bool skip_x_cap_ {false};
  bool skip_y_cap_ {false};
  std::unique_ptr<stellarcsg::CompiledFacetSurfaceSet> surface_;
};

} // namespace openmc

#endif
