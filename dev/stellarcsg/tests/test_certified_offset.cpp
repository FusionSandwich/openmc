#include "../src/exact_dyadic.hpp"
#include "stellarcsg/certified_spline_offset.hpp"
#include "stellarcsg/compiled_swept_surface.hpp"

#include <cfenv>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
void require(bool condition, const char* message)
{
  if (!condition)
    throw std::runtime_error(message);
}
stellarcsg::SweptSplineSurfaceData fixture()
{
  stellarcsg::SweptSplineSurfaceData d;
  d.sample_count = 16;
  d.length = 8;
  d.characteristic_length = 1.5;
  d.centerline_coefficients = {1, 0, 0, 1, .5, 0, 1, 1, 0, .5, 1, 0, 0, 1, 0,
    -.5, 1, 0, -1, 1, 0, -1, .5, 0, -1, 0, 0, -1, -.5, 0, -1, -1, 0, -.5, -1, 0,
    0, -1, 0, .5, -1, 0, 1, -1, 0, 1, -.5, 0};
  for (int i = 0; i < 16; ++i) {
    d.normal_coefficients.insert(d.normal_coefficients.end(), {0, 0, 1});
    d.binormal_coefficients.insert(d.binormal_coefficients.end(), {1, 0, 0});
  }
  d.major_radius_coefficients.assign(16, 0.25);
  d.minor_radius_coefficients.assign(16, 0.25);
  return d;
}

stellarcsg::SweptSplineSurfaceData support_fixture(bool swap_axes = false)
{
  auto d = fixture();
  d.sample_count = 8;
  d.characteristic_length = 5;
  d.centerline_coefficients = {5, 0, 0, 2, 3, 0, 0, 5, 0, -2, 3, 0, -5, 0, 0,
    -2, -3, 0, 0, -5, 0, 2, -3, 0};
  if (swap_axes)
    for (std::size_t i = 0; i < 8; ++i)
      std::swap(
        d.centerline_coefficients[3 * i], d.centerline_coefficients[3 * i + 1]);
  d.normal_coefficients.resize(24);
  d.binormal_coefficients.resize(24);
  d.major_radius_coefficients.resize(8);
  d.minor_radius_coefficients.resize(8);
  return d;
}

void support_contacts()
{
  const auto data = support_fixture();
  const stellarcsg::CertifiedSplineOffset s(data);
  // Exact seam support is (2+4*5+2)/6=4. All cubic Bezier x
  // coefficients are <=4, with a strict coefficient on every chart.
  for (const double sign : {-1., 1.}) {
    const auto side = s.distance({sign * 4.25, -1.25, 0}, {0, 1, 0}, false);
    const auto top =
      s.distance({sign * 4, -1.25, sign * .25}, {0, 1, 0}, false);
    const auto reverse =
      s.distance({sign * 4, 1.25, sign * .25}, {0, -1, 0}, false);
    for (const auto& result : {side, top, reverse}) {
      require(result.disposition() == stellarcsg::DistanceDisposition::hit &&
                result.kind == stellarcsg::RootKind::stationary_tangent &&
                std::abs(result.distance - 1.25) < 1e-11,
        "exact support contact certificate failed");
    }
  }
  require(s.distance({4, 1, .25}, {0, 1, 0}, false).disposition() ==
            stellarcsg::DistanceDisposition::no_hit,
    "contact behind ray was admitted");
  require(s.distance({4, 0, .25}, {0, 1, 0}, false).terminal_unresolved,
    "unsuppressed zero contact policy changed");
  require(s.distance({4, 0, .25}, {0, 1, 0}, true).disposition() ==
            stellarcsg::DistanceDisposition::no_hit,
    "coincident support contact not suppressed");
  stellarcsg::RootSearchOptions exhausted;
  exhausted.initial_subdivisions = 0;
  require(s.distance({4, -1.25, .25}, {0, 1, 0}, false, exhausted)
            .terminal_unresolved,
    "support certificate bypassed invalid budget");
  const stellarcsg::CertifiedSplineOffset swapped(support_fixture(true));
  const auto rotated = swapped.distance({-1.25, 4, .25}, {1, 0, 0}, false);
  require(rotated.found && std::abs(rotated.distance - 1.25) < 1e-11,
    "support contact depends on hardcoded x axis");
  auto shifted = data;
  shifted.centerline_coefficients[1] = std::ldexp(3., -60);
  const stellarcsg::CertifiedSplineOffset tiny(shifted);
  const auto positive = tiny.distance({4.25, 0, 0}, {0, 1, 0}, false);
  require(positive.found && positive.distance == std::ldexp(1., -59),
    "tiny exact positive contact collapsed to zero");
}

void exact_linear_arithmetic()
{
  using stellarcsg::offset_detail::ExactDyadic;
  ExactDyadic one;
  one.add_double(1);
  for (const int exponent : {-1074, -100, 100, 1000}) {
    const double value = std::ldexp(1., exponent);
    ExactDyadic cancelled;
    cancelled.add_double(value, 16);
    cancelled.add_double(1);
    cancelled.add_double(value, -16);
    require(cancelled.valid() && cancelled.compare(one) == 0,
      "exact dyadic carry/cancellation corrupted tiny term");
    long double lower, upper;
    require(cancelled.interval(lower, upper) && lower <= 1 && upper >= 1,
      "exact dyadic conversion lost containment");
  }
  ExactDyadic zero;
  zero.add_double(-0.);
  require(zero.compare(ExactDyadic {}) == 0, "signed zero changed exact order");
  ExactDyadic invalid;
  invalid.add_double(std::numeric_limits<double>::infinity());
  long double lower, upper;
  require(!invalid.valid() && !invalid.interval(lower, upper),
    "invalid dyadic value admitted");
  ExactDyadic maximum;
  maximum.add_double(std::numeric_limits<double>::max(), 16);
  maximum.add_double(1, -1);
  maximum.add_double(std::numeric_limits<double>::max(), -16);
  one.negate();
  require(maximum.valid() && maximum.compare(one) == 0,
    "maximum binary64 weighted cancellation corrupted carry/borrow");
  maximum.add_double(-123, 0);
  require(maximum.compare(one) == 0, "zero weight changed exact sum");
  invalid = ExactDyadic {};
  invalid.add_double(1, 17);
  require(!invalid.valid(), "unsupported exact weight admitted");
}
} // namespace

int main()
{
  try {
    const auto d = fixture();
    const stellarcsg::CertifiedSplineOffset s(d);
    // Exact cardinal identity C(0)=(1,0,0). Every Bezier x control <=1,
    // so the global closest point to (2,0,0) is exactly C(0).
    const auto q = s.squared_distance_enclosure({2, 0, 0});
    require(q.lower <= 16 && q.upper >= 16,
      "exact rational minimum escaped enclosure");
    require(
      s.evaluate({1.25, 0, 0}) == 0, "exact origin contact lost boundary band");
    const auto hit = s.distance({2, 0, 0}, {-1, 0, 0}, false);
    require(hit.disposition() == stellarcsg::DistanceDisposition::hit &&
              std::abs(hit.distance - 0.75) < 1e-11,
      "first curved seam hit wrong");
    const auto contact = s.distance({1.25, 0, 0}, {-1, 0, 0}, false);
    require(
      contact.disposition() == stellarcsg::DistanceDisposition::unresolved,
      "unsuppressed exact origin contact silently removed");
    const auto inward = s.distance({1.25, 0, 0}, {-1, 0, 0}, true);
    require(inward.disposition() == stellarcsg::DistanceDisposition::hit &&
              std::abs(inward.distance - 0.5) < 1e-11,
      "inward contact suppression skipped exit");
    const auto outward = s.distance({1.25, 0, 0}, {1, 0, 0}, true);
    require(outward.disposition() == stellarcsg::DistanceDisposition::no_hit,
      "outward contact suppression failed");
    stellarcsg::RootSearchOptions budget;
    budget.initial_subdivisions = 8;
    budget.max_refinement_levels = 0;
    const auto tangent = s.distance({1, -2, 0.25}, {0, 1, 0}, false, budget);
    require(
      tangent.disposition() == stellarcsg::DistanceDisposition::unresolved,
      "even root turned into no-hit");
    require(s.distance({2, 0, 0}, {1, 0, 0}, false).disposition() ==
              stellarcsg::DistanceDisposition::no_hit,
      "behind-ray roots not excluded");
    const auto tiny = s.distance({2, 0, 0}, {-1e-300, 0, 0}, false);
    require(tiny.disposition() == stellarcsg::DistanceDisposition::hit &&
              std::abs(tiny.distance - hit.distance) < 1e-11,
      "tiny direction changed ray");
    budget.absolute_t_tolerance = std::numeric_limits<double>::infinity();
    require(
      s.distance({2, 0, 0}, {-1, 0, 0}, false, budget).terminal_unresolved,
      "nonfinite option admitted");
    bool rejected = false;
    try {
      (void)s.normal({1, 0, 0});
    } catch (const std::runtime_error&) {
      rejected = true;
    }
    require(rejected, "zero gradient produced normal");
    rejected = false;
    try {
      (void)s.normal({0, 0, 0});
    } catch (const std::runtime_error&) {
      rejected = true;
    }
    require(rejected, "competing nearest centers produced normal");
    rejected = false;
    std::fesetround(FE_UPWARD);
    try {
      (void)s.evaluate({2, 0, 0});
    } catch (const std::runtime_error&) {
      rejected = true;
    }
    std::fesetround(FE_TONEAREST);
    require(rejected, "unsupported rounding mode admitted");
    auto degenerate = d;
    degenerate.centerline_coefficients.assign(48, 0);
    rejected = false;
    try {
      const stellarcsg::CertifiedSplineOffset bad(degenerate);
    } catch (const std::invalid_argument&) {
      rejected = true;
    }
    require(rejected, "degenerate tangent admitted");
    support_contacts();
    exact_linear_arithmetic();
    std::cout << "certified_offset_adversarial_controls PASS\n";
    return 0;
  } catch (const std::exception& error) {
    std::fesetround(FE_TONEAREST);
    std::cerr << error.what() << '\n';
    return 1;
  }
}
