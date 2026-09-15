#include "../src/swept_span_bounds.hpp"

#include <cassert>
#include <cmath>
#include <limits>

using stellarcsg::BoundingBox;
using stellarcsg::Vec3;
using namespace stellarcsg::swept_span_bounds;

int main()
{
  // These controls have exact rational Bernstein conversion values 6, 8, 10, 12.
  CubicSpan authoritative {};
  authoritative.center[0] = {0., 6., 12., 18.};
  authoritative.center[1] = {0., 0., 0., 0.};
  authoritative.center[2] = {0., 0., 0., 0.};
  authoritative.radius = {1., 1., 1., 1.};
  CubicSpan compiled {};
  compiled.center[0] = {6., 6., 0., 0.};
  compiled.center[1] = {0., 0., 0., 0.};
  compiled.center[2] = {0., 0., 0., 0.};
  compiled.radius = {1., 0., 0., 0.};
  const auto bounds = union_bounds(authoritative, compiled);
  assert(bounds.certain);
  assert(bounds.box.lower.x <= 5.0 && bounds.box.upper.x >= 13.0);
  assert(bounds.box.lower.y <= -1.0 && bounds.box.upper.y >= 1.0);

  const auto positive = ray_interval_outward(
    bounds.box, Vec3 {0., 0., 0.}, Vec3 {1., 0., 0.});
  const auto negative = ray_interval_outward(
    bounds.box, Vec3 {20., 0., 0.}, Vec3 {-1., 0., 0.});
  assert(positive.certain && positive.interval && positive.interval->enter <= 5.0);
  assert(negative.certain && negative.interval && negative.interval->enter <= 7.0);

  const BoundingBox huge {{1.e300, -1., -1.},
                           {1.e300, 1., 1.}};
  const auto translated = ray_interval_outward(
    huge, Vec3 {1.e300, 0., 0.}, Vec3 {0., 1., 0.});
  assert(translated.certain && translated.interval);

  const auto parallel_miss = ray_interval_outward(
    bounds.box, Vec3 {0., 2., 0.}, Vec3 {1., 0., 0.});
  assert(parallel_miss.certain && !parallel_miss.interval);

  const auto subnormal = ray_interval_outward(bounds.box, Vec3 {},
    Vec3 {std::numeric_limits<double>::denorm_min(), 0., 0.});
  assert(!subnormal.certain);

  CubicSpan overflowing = authoritative;
  overflowing.center[0][0] = std::numeric_limits<double>::max();
  assert(!union_bounds(overflowing, compiled).certain);
  return 0;
}
