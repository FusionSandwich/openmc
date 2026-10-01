#ifndef STELLARCSG_CERTIFIED_SPLINE_OFFSET_HPP
#define STELLARCSG_CERTIFIED_SPLINE_OFFSET_HPP

#include "stellarcsg/periodic_radial_surface.hpp"

#include <memory>

namespace stellarcsg {
struct SweptSplineSurfaceData;
struct OffsetSquaredDistanceEnclosure {
  long double lower {0};
  long double upper {0};
  bool complete {false};
};

// Explicit exact-control offset-union representation. This is not the legacy
// rounded-angle/frame evaluator. Query budgets fail closed.
class CertifiedSplineOffset {
public:
  explicit CertifiedSplineOffset(const SweptSplineSurfaceData& data);
  ~CertifiedSplineOffset();
  CertifiedSplineOffset(const CertifiedSplineOffset&) = delete;
  CertifiedSplineOffset& operator=(const CertifiedSplineOffset&) = delete;
  [[nodiscard]] double evaluate(const Vec3& point) const;
  [[nodiscard]] Vec3 normal(const Vec3& point) const;
  [[nodiscard]] DistanceResult distance(const Vec3& origin,
    const Vec3& direction, bool coincident,
    const RootSearchOptions& options = {}) const;
  [[nodiscard]] const BoundingBox& bounding_box() const noexcept;
  // Test/review surface: bounds remain conservative even when the finite
  // minimum-search tolerance was not achieved.
  [[nodiscard]] OffsetSquaredDistanceEnclosure squared_distance_enclosure(
    const Vec3& point) const;

private:
  struct Implementation;
  std::unique_ptr<Implementation> implementation_;
};
} // namespace stellarcsg
#endif
