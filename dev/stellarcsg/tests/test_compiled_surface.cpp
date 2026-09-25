#include "stellarcsg/coefficient_file.hpp"
#include "stellarcsg/compiled_periodic_surface.hpp"
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/compiled_swept_surface_set.hpp"
#include "stellarcsg/performance_counters.hpp"
#include "stellarcsg/sha256.hpp"

#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool condition, const std::string& message)
{
  if (!condition) {
    ++failures;
    std::cerr << "FAIL: " << message << '\n';
  }
}

void check_near(double actual, double expected, double tolerance,
  const std::string& message)
{
  if (!std::isfinite(actual) || std::abs(actual - expected) > tolerance) {
    ++failures;
    std::cerr << std::setprecision(17)
              << "FAIL: " << message << " actual=" << actual
              << " expected=" << expected << " tolerance=" << tolerance
              << '\n';
  }
}

stellarcsg::PeriodicSplineSurfaceData make_torus_data()
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.content_id = "compiled-torus-v1";
  data.n_field_periods = 1;
  data.axis_r_coefficients.assign(8, 5.0);
  data.axis_z_coefficients.assign(8, 0.0);
  data.n_theta = 12;
  data.n_phi = 8;
  data.radius_coefficients.assign(data.n_theta * data.n_phi, 1.0);
  data.characteristic_length = 6.0;
  return data;
}

void test_compiled_torus()
{
  const stellarcsg::CompiledPeriodicSplineSurface surface {make_torus_data()};
  check(surface.specialization()
      == stellarcsg::PeriodicSurfaceSpecialization::exact_circular_torus,
    "constant coefficients select exact circular-torus specialization");
  check_near(surface.evaluate({6.0, 0.0, 0.0}), 0.0, 1.0e-12,
    "compiled torus surface value");
  check(surface.evaluate({5.0, 0.0, 0.0}) < 0.0,
    "reference axis is inside the radial half-space");
  check(surface.evaluate({7.0, 0.0, 0.0}) > 0.0,
    "point outside torus is positive");

  const auto normal = surface.normal({6.0, 0.0, 0.0});
  check_near(normal.x, 1.0, 1.0e-12, "compiled torus outward normal x");
  check_near(normal.y, 0.0, 1.0e-12, "compiled torus outward normal y");
  check_near(normal.z, 0.0, 1.0e-12, "compiled torus outward normal z");

  stellarcsg::RootSearchOptions options;
  options.initial_subdivisions = 96;
  options.max_refinement_levels = 6;
  const auto crossing = surface.distance(
    {7.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false, options);
  check(crossing.found, "compiled torus radial crossing is found");
  if (crossing.found) {
    check_near(crossing.distance, 1.0, 3.0e-8,
      "compiled torus radial crossing distance");
  }
  check(crossing.root_diagnostics.solver_path
      == stellarcsg::SolverPath::exact_circular_torus,
    "exact torus reports its analytic specialization");

  const auto four_root = surface.distance(
    {-7.0, 0.0, 0.0}, {1.0, 0.0, 0.0}, false, options);
  check(four_root.found, "four-root torus ray is found");
  if (four_root.found) {
    check_near(four_root.distance, 1.0, 2.0e-10,
      "nearest of four torus roots");
  }

  const auto tangent = surface.distance(
    {6.0, -2.0, 0.0}, {0.0, 3.0, 0.0}, false, options);
  check(tangent.found, "exact torus tangent ray is found");
  if (tangent.found) {
    check_near(tangent.distance, 2.0, 2.0e-9,
      "exact torus tangent distance with non-unit direction");
  }

  const auto box = surface.bounding_box();
  check(box.lower.x <= -6.0 && box.upper.x >= 6.0,
    "compiled torus conservative xy bounds");
  check(box.lower.z <= -1.0 && box.upper.z >= 1.0,
    "compiled torus conservative z bounds");
}

void test_torus_forced_through_general_patch_solver()
{
  auto data = make_torus_data();
  data.content_id = "compiled-torus-forced-general-v1";
  data.force_general_solver = true;
  const stellarcsg::CompiledPeriodicSplineSurface surface {std::move(data)};
  check(surface.specialization()
      == stellarcsg::PeriodicSurfaceSpecialization::general_periodic,
    "forced-general torus disables the exact specialization");
  check(!surface.patches().empty() && !surface.patch_bvh().empty(),
    "forced-general torus compiles parametric patches and a BVH");

  const std::vector<stellarcsg::Vec3> origins {
    {7.0, 0.0, 0.0}, {-7.0, 0.0, 0.0}, {0.0, 7.0, 0.25},
    {4.5, -4.8, 0.4}, {-4.7, -4.4, -0.35}};
  const std::vector<stellarcsg::Vec3> directions {
    {-1.0, 0.0, 0.0}, {1.0, 0.0, 0.0}, {0.0, -1.0, -0.03},
    {-0.8, 0.6, -0.1}, {0.7, 0.7, 0.08}};
  stellarcsg::RootSearchOptions options;
  options.initial_subdivisions = 128;
  options.max_refinement_levels = 8;
  stellarcsg::reset_performance_counters();
  for (std::size_t i = 0; i < origins.size(); ++i) {
    const auto fast = surface.distance(origins[i], directions[i], false, options);
    const auto oracle = surface.distance_reference(
      origins[i], directions[i], false, options);
    check(fast.found == oracle.found,
      "forced-general torus patch path agrees with oracle existence");
    if (fast.found && oracle.found) {
      check_near(fast.distance, oracle.distance, 2.0e-8,
        "forced-general torus patch path agrees with oracle distance");
    }
    check(fast.root_diagnostics.reference_fallback_calls == 0,
      "forced-general torus never calls the global reference fallback");
  }
  stellarcsg::reset_performance_counters();
  (void) surface.distance(
    {7.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false, options);
  const auto counters = stellarcsg::performance_counters_snapshot();
  check(counters.global_reference_calls == 0,
    "production forced-general torus records zero global reference calls");
  const auto tangent = surface.distance(
    {6.0, -1.23456789, 0.0}, {0.0, 3.0, 0.0}, false, options);
  check(tangent.found, "forced-general torus finds an exact tangent");
  if (tangent.found) {
    check_near(tangent.distance, 1.23456789, 2.0e-8,
      "forced-general torus exact tangent distance");
  }
  const auto coincident_out = surface.distance(
    {6.0, 0.0, 0.0}, {4.0, 0.0, 0.0}, true, options);
  check(!coincident_out.found,
    "forced-general torus coincident outward ray has no later crossing");
  if (coincident_out.found) {
    std::cerr << std::setprecision(17)
              << "coincident outward distance=" << coincident_out.distance
              << " residual=" << coincident_out.residual << '\n';
  }
  const auto coincident_in = surface.distance(
    {6.0, 0.0, 0.0}, {-4.0, 0.0, 0.0}, true, options);
  check(coincident_in.found,
    "forced-general torus coincident inward ray finds the next crossing");
  if (coincident_in.found) {
    check_near(coincident_in.distance, 2.0, 2.0e-8,
      "forced-general torus coincident inward distance");
  }
}

void test_moving_axis_and_helical_radius()
{
  auto data = make_torus_data();
  data.content_id = "compiled-helical-v1";
  data.n_field_periods = 5;
  const std::size_t n_axis = 16;
  data.axis_r_coefficients.resize(n_axis);
  data.axis_z_coefficients.resize(n_axis);
  for (std::size_t i = 0; i < n_axis; ++i) {
    const double phase = 2.0 * 3.141592653589793238462643383279502884
                         * static_cast<double>(i) / static_cast<double>(n_axis);
    data.axis_r_coefficients[i] = 5.0 + 0.08 * std::cos(phase);
    data.axis_z_coefficients[i] = 0.05 * std::sin(phase);
  }
  data.n_theta = 24;
  data.n_phi = 20;
  data.radius_coefficients.resize(data.n_theta * data.n_phi);
  for (std::size_t i = 0; i < data.n_theta; ++i) {
    const double theta = 2.0 * 3.141592653589793238462643383279502884
                         * static_cast<double>(i) / static_cast<double>(data.n_theta);
    for (std::size_t j = 0; j < data.n_phi; ++j) {
      const double psi = 2.0 * 3.141592653589793238462643383279502884
                         * static_cast<double>(j) / static_cast<double>(data.n_phi);
      data.radius_coefficients[i * data.n_phi + j] =
        1.0 + 0.10 * std::cos(2.0 * theta - psi);
    }
  }

  const stellarcsg::CompiledPeriodicSplineSurface surface {std::move(data)};
  check(surface.specialization()
      == stellarcsg::PeriodicSurfaceSpecialization::general_periodic,
    "helical coefficients select the general periodic path");
  for (int k = 0; k < 20; ++k) {
    const double phi = 2.0 * 3.141592653589793238462643383279502884
                       * static_cast<double>(k) / 20.0;
    const stellarcsg::Vec3 outside {6.5 * std::cos(phi),
      6.5 * std::sin(phi), 0.0};
    check(surface.evaluate(outside) > 0.0,
      "moving-axis test point remains outside");
  }

  const std::vector<stellarcsg::Vec3> origins {
    {7.0, 0.0, 0.0}, {-7.0, 0.0, 0.0}, {0.0, 7.0, 0.2},
    {4.2, -4.8, 0.7}, {-4.5, -4.7, -0.6}, {0.2, 0.1, 0.0}};
  const std::vector<stellarcsg::Vec3> directions {
    {-1.0, 0.0, 0.0}, {1.0, 0.0, 0.0}, {0.0, -1.0, -0.03},
    {-0.7, 0.6, -0.2}, {0.5, 0.8, 0.1}, {1.0, 0.2, 0.03}};
  auto options = stellarcsg::RootSearchOptions {};
  options.initial_subdivisions = 128;
  options.max_refinement_levels = 8;
  for (std::size_t i = 0; i < origins.size(); ++i) {
    const auto fast = surface.distance(origins[i], directions[i], false, options);
    const auto oracle = surface.distance_reference(
      origins[i], directions[i], false, options);
    check(fast.found == oracle.found,
      "general-periodic certified path agrees with oracle existence");
    if (fast.found && oracle.found) {
      check_near(fast.distance, oracle.distance, 2.0e-8,
        "general-periodic certified path agrees with oracle distance");
    }
    check(fast.root_diagnostics.solver_path
        == stellarcsg::SolverPath::general_periodic_certified
        || fast.root_diagnostics.solver_path
          == stellarcsg::SolverPath::reference_fallback,
      "general-periodic path records certified solve or explicit fallback");
  }
}

void test_scale_aware_axisymmetric_detection()
{
  auto shaped = make_torus_data();
  for (std::size_t i = 0; i < shaped.n_theta; ++i) {
    const double value = 1.0 + 0.15 * std::cos(
      2.0 * 3.141592653589793238462643383279502884
      * static_cast<double>(i) / static_cast<double>(shaped.n_theta));
    for (std::size_t j = 0; j < shaped.n_phi; ++j) {
      shaped.radius_coefficients[i * shaped.n_phi + j] = value;
    }
  }
  shaped.axis_r_coefficients.back() += 1.0e-14;
  const stellarcsg::CompiledPeriodicSplineSurface surface {std::move(shaped)};
  check(surface.specialization()
      == stellarcsg::PeriodicSurfaceSpecialization::shaped_axisymmetric,
    "scale-aware constancy detects shaped axisymmetry");
  const auto crossing = surface.distance(
    {7.0, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false);
  check(crossing.found, "shaped-axisymmetric path finds radial crossing");
  check(crossing.root_diagnostics.solver_path
      == stellarcsg::SolverPath::shaped_axisymmetric_certified,
    "shaped-axisymmetric path is recorded in diagnostics");
  check(crossing.root_diagnostics.reference_fallback_calls == 0,
    "well-conditioned shaped crossing does not use the oracle fallback");
}

void test_close_root_pair_regressions()
{
  const stellarcsg::CompiledPeriodicSplineSurface surface {make_torus_data()};
  struct Fixture { stellarcsg::Vec3 origin; stellarcsg::Vec3 direction; };
  const std::vector<Fixture> fixtures {
    {{5.7388633334130201, 0.00056429199550223075, -1.0075336982387282},
      {-0.32707973244673211, 0.20756893579428687, 0.003228224149003481}},
    {{-1.9735389719494858, -7.8905941652595448, -1.2194512625386107},
      {1.9856556970652377, 3.4305195261866888, 0.25655687348087075}},
    {{5.5611249013463357, -6.1748211618025977, 1.2388668479062903},
      {-1.635175088157226, 0.50814934632868147, -0.088892115048631842}},
    {{-7.5654802373329169, -2.7066240646838118, 1.4925058779195925},
      {5.8450226938084944, 4.7731259362252461, -1.0750166369363239}},
  };
  auto options = stellarcsg::RootSearchOptions {};
  options.initial_subdivisions = 128;
  options.max_refinement_levels = 8;
  options.absolute_f_tolerance = 2.0e-12;
  options.derivative_tolerance = 2.0e-12;
  for (const auto& fixture : fixtures) {
    const auto exact = surface.distance(
      fixture.origin, fixture.direction, false, options);
    const auto oracle = surface.distance_reference(
      fixture.origin, fixture.direction, false, options);
    check(exact.found && oracle.found,
      "close-root-pair regression is found by both solvers");
    if (exact.found && oracle.found) {
      check_near(oracle.distance, exact.distance, 2.0e-8,
        "oracle splits a same-sign interval at its stationary point");
    }
  }
}

void test_exact_circular_swept_coil()
{
  constexpr std::size_t count = 256;
  constexpr double major = 5.0;
  constexpr double minor = 0.25;
  constexpr double pi = 3.141592653589793238462643383279502884;
  const double eigenvalue = (4.0 + 2.0 * std::cos(2.0 * pi / count)) / 6.0;
  stellarcsg::SweptSplineSurfaceData data;
  data.coil_id = 17;
  data.sample_count = count;
  data.length = 2.0 * pi * major;
  data.characteristic_length = major + minor;
  data.centerline_coefficients.resize(3 * count);
  data.normal_coefficients.resize(3 * count);
  data.binormal_coefficients.resize(3 * count);
  data.major_radius_coefficients.assign(count, minor);
  data.minor_radius_coefficients.assign(count, minor);
  for (std::size_t i = 0; i < count; ++i) {
    const double angle = 2.0 * pi * static_cast<double>(i)
                         / static_cast<double>(count);
    data.centerline_coefficients[3 * i] = major * std::cos(angle) / eigenvalue;
    data.centerline_coefficients[3 * i + 1] = major * std::sin(angle) / eigenvalue;
    data.centerline_coefficients[3 * i + 2] = 0.0;
    data.normal_coefficients[3 * i] = 0.0;
    data.normal_coefficients[3 * i + 1] = 0.0;
    data.normal_coefficients[3 * i + 2] = 1.0;
    data.binormal_coefficients[3 * i] = std::cos(angle) / eigenvalue;
    data.binormal_coefficients[3 * i + 1] = std::sin(angle) / eigenvalue;
    data.binormal_coefficients[3 * i + 2] = 0.0;
  }
  auto forced_data = data;
  auto near_torus_data = data;
  auto varying_radius_data = data;
  varying_radius_data.characteristic_length = 1.0e8;
  varying_radius_data.major_radius_coefficients[0] += 5.0e-5;
  const stellarcsg::CompiledSweptSplineSurface varying_radius {
    std::move(varying_radius_data)};
  const auto varying_crossing = varying_radius.distance(
    {major, 0.0, 1.0}, {0.0, 0.0, -1.0}, false);
  check(varying_crossing.found,
    "varying swept radius produces an axial crossing candidate");
  if (varying_crossing.found) {
    check_near(varying_crossing.distance,
      1.0 - (minor + (2.0 / 3.0) * 5.0e-5), 5.0e-6,
      "varying swept radius uses the faithful spline crossing");
  }
  const stellarcsg::CompiledSweptSplineSurface coil {std::move(data), false,
    stellarcsg::SweptTorusMode::approximate_torus_surrogate};
  const stellarcsg::CompiledSweptSplineSurface forced_coil {
    std::move(forced_data), true};
  check(coil.approximate_torus_surrogate(),
    "analytic control explicitly selects approximate torus surrogate");
  check(!forced_coil.approximate_torus_surrogate(),
    "faithful swept spline does not select torus surrogate");
  check_near(coil.evaluate({major + minor, 0.0, 0.0}), 0.0, 1.0e-12,
    "swept circular coil evaluates as exact torus");
  const auto crossing = coil.distance_reference(
    {major + 2.0 * minor, 0.0, 0.0}, {-2.0, 0.0, 0.0}, false);
  check(crossing.found, "swept circular coil finds radial crossing");
  if (crossing.found) {
    check_near(crossing.distance, minor, 2.0e-10,
      "swept circular coil exact torus distance");
  }
  constexpr std::size_t ray_count = 100;
  constexpr double golden_angle = 2.3999632297286533222;
  const stellarcsg::Vec3 origin {major + 2.0 * minor, 0.0, 0.0};
  for (std::size_t i = 0; i < ray_count; ++i) {
    const double z = 1.0 - 2.0 * (static_cast<double>(i) + 0.5)
                             / static_cast<double>(ray_count);
    const double radial = std::sqrt(std::max(0.0, 1.0 - z * z));
    const double azimuth = golden_angle * static_cast<double>(i);
    const stellarcsg::Vec3 direction {
      radial * std::cos(azimuth), radial * std::sin(azimuth), z};
    const auto exact = coil.distance(origin, direction, false);
    const auto general = forced_coil.distance(origin, direction, false);
    check(exact.found == general.found,
      "forced-general circular coil preserves hit classification");
    if (exact.found && general.found) {
      check_near(general.distance, exact.distance, 1.0e-7,
        "forced-general circular coil preserves nearest root");
    }
  }
  near_torus_data.major_radius_coefficients[0] += 2.0e-6;
  near_torus_data.minor_radius_coefficients[0] += 2.0e-6;
  const auto rejects_invalid = [&](const auto& mutate) {
    auto invalid = near_torus_data;
    mutate(invalid);
    try {
      const stellarcsg::CompiledSweptSplineSurface rejected {std::move(invalid)};
      return false;
    } catch (const std::invalid_argument&) {
      return true;
    }
  };
  check(rejects_invalid([](auto& invalid) {
    invalid.centerline_coefficients[0] =
      std::numeric_limits<double>::quiet_NaN();
  }), "nonfinite centerline coefficient is rejected before compilation");
  check(rejects_invalid([](auto& invalid) {
    invalid.normal_coefficients[0] =
      std::numeric_limits<double>::infinity();
  }), "nonfinite frame coefficient is rejected before compilation");
  check(rejects_invalid([](auto& invalid) {
    invalid.major_radius_coefficients[0] =
      std::numeric_limits<double>::infinity();
  }), "nonfinite radius coefficient is rejected before compilation");
  check(rejects_invalid([](auto& invalid) {
    invalid.length = std::numeric_limits<double>::infinity();
  }), "nonfinite sweep length is rejected before compilation");
  auto surrogate_data = near_torus_data;
  auto set_data = near_torus_data;
  const stellarcsg::CompiledSweptSplineSurface near_torus {
    std::move(near_torus_data)};
  const stellarcsg::CompiledSweptSplineSurface near_surrogate {
    std::move(surrogate_data), false,
    stellarcsg::SweptTorusMode::approximate_torus_surrogate};
  check(!near_torus.approximate_torus_surrogate()
      && near_surrogate.approximate_torus_surrogate(),
    "near-torus coefficient payload defaults to faithful spline");
  check(std::abs(near_torus.evaluate({major + minor, 0.0, 0.0})
        - near_surrogate.evaluate({major + minor, 0.0, 0.0})) > 5.0e-7,
    "sample-tolerance torus surrogate changes near-torus surface value");
  const stellarcsg::CompiledSweptSplineSurfaceSet faithful_set {
    {std::move(set_data)}};
  check_near(faithful_set.evaluate({major + minor, 0.0, 0.0}),
    near_torus.evaluate({major + minor, 0.0, 0.0}), 1.0e-12,
    "default coil set retains its member's faithful spline value");
}

void test_swept_coil_set_bvh()
{
  constexpr std::size_t count = 64;
  constexpr double major = 5.0;
  constexpr double minor = 0.25;
  constexpr double pi = 3.141592653589793238462643383279502884;
  const double eigenvalue = (4.0 + 2.0 * std::cos(2.0 * pi / count)) / 6.0;
  const auto make_coil = [&](int coil_id, double z_offset) {
    stellarcsg::SweptSplineSurfaceData data;
    data.coil_id = coil_id;
    data.sample_count = count;
    data.length = 2.0 * pi * major;
    data.characteristic_length = major + std::abs(z_offset) + minor;
    data.centerline_coefficients.resize(3 * count);
    data.normal_coefficients.resize(3 * count);
    data.binormal_coefficients.resize(3 * count);
    data.major_radius_coefficients.assign(count, minor);
    data.minor_radius_coefficients.assign(count, minor);
    for (std::size_t i = 0; i < count; ++i) {
      const double angle = 2.0 * pi * static_cast<double>(i)
                           / static_cast<double>(count);
      data.centerline_coefficients[3 * i] =
        major * std::cos(angle) / eigenvalue;
      data.centerline_coefficients[3 * i + 1] =
        major * std::sin(angle) / eigenvalue;
      data.centerline_coefficients[3 * i + 2] = z_offset;
      data.normal_coefficients[3 * i] = 0.0;
      data.normal_coefficients[3 * i + 1] = 0.0;
      data.normal_coefficients[3 * i + 2] = 1.0;
      data.binormal_coefficients[3 * i] = std::cos(angle) / eigenvalue;
      data.binormal_coefficients[3 * i + 1] = std::sin(angle) / eigenvalue;
      data.binormal_coefficients[3 * i + 2] = 0.0;
    }
    return data;
  };
  std::vector<stellarcsg::SweptSplineSurfaceData> data;
  data.push_back(make_coil(10, -2.0));
  data.push_back(make_coil(20, 0.0));
  data.push_back(make_coil(30, 2.0));
  const stellarcsg::CompiledSweptSplineSurfaceSet set {std::move(data),
    stellarcsg::SweptTorusMode::approximate_torus_surrogate};
  check(set.size() == 3, "coil-set BVH retains every coil");
  check(set.coil_bvh().size() == 3, "three-coil set builds a top-level BVH");
  check(set.evaluate({major, 0.0, 0.0}) < 0.0,
    "coil-set union classifies a point inside one coil");
  check(set.evaluate({0.0, 0.0, 0.0}) > 0.0,
    "coil-set union classifies a point outside every coil");
  const auto crossing = set.distance(
    {major + 2.0 * minor, 0.0, 0.0}, {-1.0, 0.0, 0.0}, false);
  check(crossing.root.found, "coil-set BVH finds the nearest crossing");
  check(crossing.coil_id == 20, "coil-set BVH returns the stable coil ID");
  if (crossing.root.found) {
    check_near(crossing.root.distance, minor, 2.0e-9,
      "coil-set BVH returns the nearest coil distance");
  }

  // A later root of the same member can be the first exterior union
  // boundary: the entering root is inside the first torus, and that torus's
  // exit is inside the second.  Exercise the actual swept compiler here.
  std::vector<stellarcsg::SweptSplineSurfaceData> overlapping;
  overlapping.push_back(make_coil(40, 0.0));
  overlapping.push_back(make_coil(50, 0.3));
  const stellarcsg::CompiledSweptSplineSurfaceSet overlapping_set {
    std::move(overlapping),
    stellarcsg::SweptTorusMode::approximate_torus_surrogate};
  const auto union_exit = overlapping_set.distance(
    {major, 0.0, 0.0}, {0.0, 0.0, 1.0}, false);
  check(union_exit.root.found, "overlapping swept tori find union exit");
  if (union_exit.root.found) {
    check_near(union_exit.root.distance, 0.3 + minor, 2.0e-9,
      "overlapping swept tori skip both interior member crossings");
    check(union_exit.coil_id == 50,
      "overlapping swept tori attribute exterior exit to final member");
  }
}

#ifdef STELLARCSG_HAS_HDF5
void test_hdf5_round_trip()
{
  const std::string filename = "stellarcsg_compiled_surface_test.h5";
  auto source = make_torus_data();
  source.canonical_metadata_json = "{\"case\":\"torus\"}";
  source.content_id = stellarcsg::periodic_spline_content_id(source);
  stellarcsg::write_periodic_spline_surface_hdf5(filename,
    "/surfaces/torus", source, true,
    stellarcsg::CoefficientFileMode::truncate);
  const auto loaded = stellarcsg::read_periodic_spline_surface_hdf5(
    filename, "/surfaces/torus", source.content_id);
  check(loaded.content_id == source.content_id, "HDF5 content ID round trip");
  check(loaded.n_field_periods == source.n_field_periods,
    "HDF5 field-period round trip");
  check(loaded.axis_r_coefficients == source.axis_r_coefficients,
    "HDF5 axis R round trip");
  check(loaded.radius_coefficients == source.radius_coefficients,
    "HDF5 radius coefficient round trip");

  bool mismatch_rejected = false;
  try {
    (void) stellarcsg::read_periodic_spline_surface_hdf5(
      filename, "/surfaces/torus", "wrong-content-id");
  } catch (const std::runtime_error&) {
    mismatch_rejected = true;
  }
  check(mismatch_rejected, "HDF5 content-ID mismatch is rejected");
  std::remove(filename.c_str());
}
#endif

void test_near_parallel_ray_box_interval()
{
  const stellarcsg::BoundingBox box {
    {1.0e16, 1.0, -1.0}, {1.0e16 + 100.0, 2.0, 1.0}};
  const auto nearly_parallel = box.ray_interval(
    {0.0, 0.0, 0.0}, {1.0, 1.0e-16, 0.0});
  check(nearly_parallel.has_value()
      && nearly_parallel->enter <= 1.0e16
      && nearly_parallel->exit >= 1.0e16,
    "nonzero near-parallel ray component reaches a distant box");
  check(!box.ray_interval({0.0, 0.0, 0.0}, {1.0, 0.0, 0.0}),
    "exactly parallel ray outside the slab still misses");
  bool invalid_rejected = false;
  try {
    (void) box.ray_interval(
      {std::numeric_limits<double>::quiet_NaN(), 0.0, 0.0},
      {1.0, 0.0, 0.0});
  } catch (const std::invalid_argument&) {
    invalid_rejected = true;
  }
  check(invalid_rejected, "nonfinite ray origin is rejected before slab pruning");
}

void test_swept_span_horner_bounds()
{
  stellarcsg::SweptSplineSurfaceData data;
  data.coil_id = 91;
  data.sample_count = 8;
  data.length = 8.0;
  data.characteristic_length = 1.0;
  data.centerline_coefficients.assign(24, 0.0);
  data.normal_coefficients.assign(24, 0.0);
  data.binormal_coefficients.assign(24, 0.0);
  data.major_radius_coefficients.assign(8, 0.25);
  data.minor_radius_coefficients.assign(8, 0.25);
  const std::array<double, 4> controls {
    2617843008604128.0, 9630992893998072.0,
    -8370907897845388.0, 7252534354622564.0};
  for (std::size_t i = 0; i < 8; ++i) {
    data.centerline_coefficients[3 * i + 1] = static_cast<double>(i);
    data.normal_coefficients[3 * i + 2] = 1.0;
    data.binormal_coefficients[3 * i + 1] = 1.0;
  }
  for (std::size_t i = 0; i < controls.size(); ++i)
    data.centerline_coefficients[3 * ((i + 7) % 8)] = controls[i];
  const stellarcsg::CompiledSweptSplineSurface surface {std::move(data)};
  const auto& span = surface.spans().front();
  const double angle = std::nextafter(span.angle_max, span.angle_min);
  const double u = (angle - span.angle_min)
    * (1.0 / (span.angle_max - span.angle_min));
  const double* power = span.power.data();
  const double x = ((power[3] * u + power[2]) * u + power[1]) * u + power[0];
  check(span.centerline_bbox.lower.x <= x && x <= span.centerline_bbox.upper.x,
    "swept span box encloses stored-power Horner center near its endpoint");
  check(span.conservative_bbox.lower.x <= x
      && x <= span.conservative_bbox.upper.x,
    "swept surface box encloses the same center despite small tube radius");
}

void test_sha256_known_vector()
{
  stellarcsg::Sha256 digest;
  const std::string input = "abc";
  digest.update(input.data(), input.size());
  check(digest.hex_digest() ==
      "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    "SHA-256 known vector");
}

} // namespace

int main()
{
  try {
    stellarcsg::reset_performance_counters();
    stellarcsg::add_performance_counter(
      stellarcsg::PerformanceCounter::distance_calls, 3);
    const auto counters = stellarcsg::performance_counters_snapshot();
    check(counters.distance_calls
          == (stellarcsg::performance_counters_enabled() ? 3U : 0U),
      "thread-local performance counters honor their compile-time switch");
    test_compiled_torus();
    test_torus_forced_through_general_patch_solver();
    test_moving_axis_and_helical_radius();
    test_scale_aware_axisymmetric_detection();
    test_close_root_pair_regressions();
    test_exact_circular_swept_coil();
    test_swept_coil_set_bvh();
    test_near_parallel_ray_box_interval();
    test_swept_span_horner_bounds();
    test_sha256_known_vector();
#ifdef STELLARCSG_HAS_HDF5
    test_hdf5_round_trip();
#endif
  } catch (const std::exception& error) {
    ++failures;
    std::cerr << "UNCAUGHT EXCEPTION: " << error.what() << '\n';
  }

  if (failures != 0) {
    std::cerr << failures << " compiled-surface test assertion(s) failed\n";
    return EXIT_FAILURE;
  }
  std::cout << "All StellarCSG compiled-surface tests passed\n";
  return EXIT_SUCCESS;
}
