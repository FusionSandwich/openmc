#ifndef OPENMC_SURFACE_SWEPT_SPLINE_H
#define OPENMC_SURFACE_SWEPT_SPLINE_H

#include "openmc/surface.h"
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/compiled_swept_surface_set.hpp"

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
  [[nodiscard]] bool uses_native_exact_torus() const noexcept
  {
    return use_native_exact_torus_;
  }
  [[nodiscard]] const std::string& solver() const noexcept { return solver_; }

private:
  std::string data_file_;
  std::string dataset_;
  std::string dataset_prefix_;
  std::string content_id_;
  std::string solver_ {"auto"};
  int dataset_start_ {0};
  int dataset_count_ {0};
  bool use_native_exact_torus_ {false};
  stellarcsg::ExactCircularTorusParameters exact_torus_ {};
  stellarcsg::RootSearchOptions root_options_ {};
  std::unique_ptr<stellarcsg::CompiledSweptSplineSurface> surface_;
  std::unique_ptr<stellarcsg::CompiledSweptSplineSurfaceSet> surface_set_;
};

} // namespace openmc

#endif
