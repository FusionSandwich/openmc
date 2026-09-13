// Public-kernel regression for the bounded exact-rational monotone span solver.
#include "stellarcsg/compiled_swept_surface.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using stellarcsg::Vec3;
constexpr double pi = 3.1415926535897932384626433832795;
int failures = 0;

void check(bool condition, const std::string& label)
{
  if (!condition) {
    ++failures;
    std::cerr << "FAIL: " << label << '\n';
  }
}

stellarcsg::SweptSplineSurfaceData fixture(double amplitude = 0.4)
{
  stellarcsg::SweptSplineSurfaceData data;
  data.coil_id = 91;
  data.sample_count = 64;
  data.length = 10*pi;
  data.characteristic_length = 9;
  data.major_radius_coefficients.assign(data.sample_count, 0.25);
  data.minor_radius_coefficients.assign(data.sample_count, 0.25);
  for (std::size_t i = 0; i < data.sample_count; ++i) {
    const double q = 2*pi*static_cast<double>(i)/data.sample_count;
    for (double value : {5*std::cos(q), 5*std::sin(q), amplitude*std::sin(3*q)})
      data.centerline_coefficients.push_back(value);
    for (double value : {0.0, 0.0, 1.0}) data.normal_coefficients.push_back(value);
    for (double value : {1.0, 0.0, 0.0}) data.binormal_coefficients.push_back(value);
  }
  return data;
}

Vec3 knot(const stellarcsg::SweptSplineSurfaceData& data, std::size_t i)
{
  Vec3 result;
  for (int offset = -1; offset <= 1; ++offset) {
    const auto count = static_cast<long>(data.sample_count);
    const auto index = static_cast<std::size_t>(
      (static_cast<long>(i)+offset+count)%count);
    const double weight = offset == 0 ? 4.0/6.0 : 1.0/6.0;
    result += weight*Vec3 {data.centerline_coefficients[3*index],
      data.centerline_coefficients[3*index+1],
      data.centerline_coefficients[3*index+2]};
  }
  return result;
}

stellarcsg::RootSearchOptions options(int budget)
{
  stellarcsg::RootSearchOptions result;
  result.circular_filter_mode = 2;
  result.circular_local_node_budget = budget;
  return result;
}

void same_result(const stellarcsg::DistanceResult& expected,
  const stellarcsg::DistanceResult& actual, const std::string& label)
{
  check(expected.found == actual.found, label+" found disposition");
  if (!expected.found || !actual.found) return;
  check(expected.kind == actual.kind, label+" root kind");
  check(std::isfinite(actual.distance)
      && std::abs(expected.distance-actual.distance) <= 5.0e-10,
    label+" nearest distance");
}

void crossing_regression()
{
  const auto data = fixture();
  const stellarcsg::CompiledSweptSplineSurface surface(data, true);
  long resolved_default = 0;
  long attempted_one = 0;
  for (std::size_t index : {std::size_t(3), std::size_t(11), std::size_t(23),
       std::size_t(37), std::size_t(51)}) {
    const double q = 2*pi*static_cast<double>(index)/data.sample_count;
    const Vec3 radial {std::cos(q), std::sin(q), 0.0};
    const Vec3 tangent {-std::sin(q), std::cos(q), 0.0};
    const Vec3 origin = knot(data, index)+0.35*radial+0.03*tangent;
    // Physical distance increases while centerline parameter decreases. This
    // makes the earlier crossing the later root in local-u traversal.
    const Vec3 direction = stellarcsg::normalized(-radial-0.17*tangent+Vec3 {0,0,0.05});
    const auto sturm = surface.distance(origin, direction, false, options(0));
    const auto one = surface.distance(origin, direction, false, options(1));
    const auto bounded = surface.distance(origin, direction, false, options(64));
    same_result(sturm, one, "one-node crossing");
    same_result(sturm, bounded, "bounded crossing");
    check(sturm.found && sturm.distance < 0.2,
      "earlier entry retained instead of later exit");
    check(sturm.root_diagnostics.monotone_resolved_spans == 0,
      "zero-node control resolved a monotone span");
    check(sturm.root_diagnostics.sturm_fallback_spans > 0,
      "zero-node control did not use preserved solver");
    resolved_default += bounded.root_diagnostics.monotone_resolved_spans;
    attempted_one += one.root_diagnostics.monotone_attempted_spans;
  }
  check(resolved_default > 0, "default budget never exercised monotone resolution");
  check(attempted_one > 0, "one-node budget never exercised bounded attempt");
}

stellarcsg::SweptSplineSurfaceData dyadic_fixture()
{
  auto data = fixture(0.0);
  for (double& coordinate : data.centerline_coefficients)
    coordinate = 3*std::round(coordinate*1024)/1024;
  return data;
}

void tangent_and_singular_fallbacks()
{
  const auto data = dyadic_fixture();
  const stellarcsg::CompiledSweptSplineSurface surface(data, true);
  const Vec3 tangent_center {
    (data.centerline_coefficients[45]+4*data.centerline_coefficients[48]
      +data.centerline_coefficients[51])/6,
    (data.centerline_coefficients[46]+4*data.centerline_coefficients[49]
      +data.centerline_coefficients[52])/6,
    0};
  const Vec3 tangent_origin = tangent_center+Vec3 {-2,0.25,0};
  const auto tangent_sturm = surface.distance(tangent_origin, {1,0,0}, false, options(0));
  const auto tangent_default = surface.distance(tangent_origin, {1,0,0}, false, options(64));
  same_result(tangent_sturm, tangent_default, "stationary tangent fallback");
  check(tangent_default.found
      && tangent_default.kind == stellarcsg::RootKind::stationary_tangent,
    "stationary tangent kind preserved");
  check(tangent_default.root_diagnostics.sturm_fallback_spans > 0,
    "stationary tangent bypassed preserved solver");

  const Vec3 center = knot(data, 0);
  const Vec3 singular_origin = center+Vec3 {0.252,0,0};
  const auto singular_sturm = surface.distance(singular_origin, {-1,0,0}, false, options(0));
  const auto singular_default = surface.distance(singular_origin, {-1,0,0}, false, options(64));
  same_result(singular_sturm, singular_default, "A=B=0 fallback");
  check(singular_default.found && singular_default.distance < 0.01,
    "singular entry distance preserved");
  check(singular_default.root_diagnostics.sturm_fallback_spans > 0,
    "A=B=0 root bypassed preserved solver");

  const Vec3 rounded = singular_origin+singular_sturm.distance*Vec3 {-1,0,0};
  const auto coincident = surface.distance(rounded, {-1,0,0}, true, options(64));
  check(coincident.found, "coincident next crossing preserved");
  check(coincident.root_diagnostics.monotone_attempted_spans == 0
      && coincident.root_diagnostics.monotone_resolved_spans == 0,
    "coincident query entered monotone solver");
}
}

int main()
{
  try {
    crossing_regression();
    tangent_and_singular_fallbacks();
  } catch (const std::exception& error) {
    ++failures;
    std::cerr << "UNEXPECTED: " << error.what() << '\n';
  }
  if (failures) return 1;
  std::cout << "All swept monotone solver tests passed\n";
}
