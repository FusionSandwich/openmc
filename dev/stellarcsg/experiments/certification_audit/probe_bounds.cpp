// Focused proof-boundary tests only: no replacement solver and no timing claims.
// Include byte-verified pinned production headers. Frame statements below mirror
// compiled_swept_surface.cpp: frame_in_span, not the full production class.
#include "swept_span_bounds.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace stellarcsg;
namespace sb = stellarcsg::swept_span_bounds;
void require(bool condition, const char* message)
{
  if (!condition) throw std::runtime_error(message);
}
int main()
{
  std::cout << std::setprecision(17) << std::boolalpha;
  require(sb::supported_binary64(), "unsupported floating environment");
  // A regular straight span. Exact derivative and supplied normal are independent.
  // Exact ||D||^2 = 5*2^-1076; binary64 rounds it to 2^-1074.
  const double delta = std::ldexp(1.0, -537);
  const Vec3 derivative {delta, 0.5 * delta, 0.0};
  Vec3 tangent = normalized(derivative);
  Vec3 n {0.0, 0.0, 1.0};
  n = normalized(n - dot(n, tangent) * tangent);
  Vec3 b = normalized(cross(tangent, n));
  n = cross(b, tangent);
  sb::CubicSpan authoritative {}, compiled {};
  authoritative.center[0] = {-delta, 0.0, delta, 2.0 * delta};
  authoritative.center[1] = {-0.5 * delta, 0.0, 0.5 * delta, delta};
  authoritative.radius = {1.0, 1.0, 1.0, 1.0};
  compiled.center[0] = {0.0, delta, 0.0, 0.0};
  compiled.center[1] = {0.0, 0.5 * delta, 0.0, 0.0};
  compiled.radius = {1.0, 0.0, 0.0, 0.0};
  const auto bounds = sb::union_bounds(authoritative, compiled);
  require(bounds.certain, "fixture did not produce a certain ideal-span bound");
  // alpha=0, major radius=1; minor radius may be .5 to avoid a circular case.
  const double evaluated_z = n.z;
  require(evaluated_z > bounds.box.upper.z,
          "expected evaluated-frame enclosure counterexample did not reproduce");
  std::cout << "{\"case\":\"frame_underflow_enclosure\",\"outcome\":\"COUNTEREXAMPLE_CONFIRMED\","
            << "\"supported_binary64\":" << sb::supported_binary64()
            << ",\"bounds_certain\":" << bounds.certain
            << ",\"derivative_x\":" << delta
            << ",\"rounded_speed_squared\":" << norm_squared(derivative)
            << ",\"tangent_squared_norm\":" << norm_squared(tangent)
            << ",\"evaluated_surface_z\":" << evaluated_z
            << ",\"box_upper_z\":" << bounds.box.upper.z << "}\n";
  // Actual helper behavior under finite, nonzero direction rescaling.
  for (int exponent : {-600, 600}) {
    bool rejected = false;
    try { (void) normalized({std::ldexp(1.0, exponent), 0.0, 0.0}); }
    catch (const std::domain_error&) { rejected = true; }
    require(rejected, "extreme-scale fixture changed");
    std::cout << "{\"case\":\"finite_direction_scale\",\"exponent\":"
              << exponent << ",\"outcome\":\"REJECTED_AS_OBSERVED\"}\n";
  }
  // Ordinary exact-arithmetic enclosure examples remain successful.
  const auto cancel = sb::power_to_bezier({1.e16, 1., -1.e16, 1.});
  require(cancel[3].lo <= 2.0 && cancel[3].hi >= 2.0, "cancellation enclosure");
  const BoundingBox box {{0.,0.,0.},{1.,1.,1.}};
  const auto outward = sb::ray_interval_outward(box, {-1., .5, .5}, {1.,0.,0.});
  require(outward.certain && outward.interval && outward.interval->enter <= 1.
          && outward.interval->exit >= 2., "outward slab example");
  const auto miss = sb::ray_interval_outward(box, {-1., 2., .5}, {1.,0.,0.});
  require(miss.certain && !miss.interval, "parallel miss example");
  const auto unknown = sb::ray_interval_outward(box, {-1.,.5,.5},
                    {std::numeric_limits<double>::denorm_min(),0.,0.});
  require(!unknown.certain, "overflow must remain unknown");
  require(!sb::excludes_ray_segment(box,1.,{-2.,2.,.5},{1.,0.,0.},0.,6.),
          "tangent interval must remain retained");
  require(sb::excludes_ray_segment(box,1.,{-2.,2.1,.5},{1.,0.,0.},0.,6.),
          "strict separated interval should exclude");
  std::cout << "{\"case\":\"ideal_bounds_examples\",\"checks\":6,\"outcome\":\"EXAMPLES_CONFIRMED\"}\n";
  // Rounded normalization is not an exact unit-ray identity. The endpoint
  // proxy uses qa=1 in qb^2-4qc; this can lose a central sphere intersection.
  const Vec3 direction = normalized(Vec3 {-1., -1., 0.});
  const Vec3 origin {std::ldexp(1.,30), std::ldexp(1.,30), 0.};
  const double qb = 2. * dot(origin,direction);
  const double qc = norm_squared(origin) - 1.;
  const double disc = qb*qb - 4.*qc;
  require(disc < 0., "endpoint discriminant counterexample did not reproduce");
  std::cout << "{\"case\":\"endpoint_sphere_proxy\",\"outcome\":\"COUNTEREXAMPLE_CONFIRMED\","
            << "\"computed_discriminant\":" << disc
            << ",\"direction_component\":" << direction.x
            << ",\"geometry\":\"exact stored direction passes through sphere center\"}\n";
  return 0;
}
