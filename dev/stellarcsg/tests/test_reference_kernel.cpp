#include "stellarcsg/periodic_radial_surface.hpp"
#include "stellarcsg/root_solver.hpp"
#include "stellarcsg/uniform_periodic_bicubic_spline.hpp"

#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using stellarcsg::BoundingBox;
using stellarcsg::PeriodicRadialSurface;
using stellarcsg::RadiusSample;
using stellarcsg::RootSearchOptions;
using stellarcsg::UniformPeriodicBicubicSpline;
using stellarcsg::Vec3;

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
    std::cerr << std::setprecision(17) << "FAIL: " << message
              << " actual=" << actual << " expected=" << expected
              << " tolerance=" << tolerance << '\n';
  }
}

RootSearchOptions root_options()
{
  RootSearchOptions options;
  options.initial_subdivisions = 64;
  options.max_refinement_levels = 6;
  options.absolute_t_tolerance = 1.0e-12;
  options.relative_t_tolerance = 1.0e-12;
  options.absolute_f_tolerance = 1.0e-14;
  options.derivative_tolerance = 1.0e-13;
  return options;
}

void test_root_solver()
{
  const auto options = root_options();

  auto linear = stellarcsg::find_nearest_root_reference(
    [](double t) { return t - 2.0; }, [](double) { return 1.0; }, 0.0, 5.0,
    options);
  check(linear.found, "linear root should be found");
  check_near(linear.root.t, 2.0, 1.0e-10, "linear root location");

  auto multiple = stellarcsg::find_nearest_root_reference(
    [](double t) { return (t - 1.0) * (t - 3.0); },
    [](double t) { return 2.0 * t - 4.0; }, 0.0, 4.0, options);
  check(multiple.found, "multiple-root function should be found");
  check_near(multiple.root.t, 1.0, 1.0e-10, "nearest of multiple roots");

  auto tangent = stellarcsg::find_nearest_root_reference(
    [](double t) { return (t - 2.0) * (t - 2.0); },
    [](double t) { return 2.0 * (t - 2.0); }, 0.0, 4.0, options);
  check(tangent.found, "tangent root should be found");
  check_near(tangent.root.t, 2.0, 1.0e-10, "tangent root location");

  auto close_pair = stellarcsg::find_nearest_root_reference(
    [](double t) { return (t - 1.001) * (t - 1.002); },
    [](double t) { return 2.0 * t - 2.003; }, 0.0, 2.0, options);
  check(close_pair.found, "closely separated roots should be resolved by refinement");
  check_near(close_pair.root.t, 1.001, 2.0e-9, "nearest closely separated root");

  auto near_boundary = stellarcsg::find_nearest_root_reference(
    [](double t) { return t - 1.0e-5; }, [](double) { return 1.0; },
    0.0, 1.0, options);
  check(near_boundary.found, "near-boundary root should be found");
  check_near(near_boundary.root.t, 1.0e-5, 1.0e-10, "near-boundary root location");

  auto none = stellarcsg::find_nearest_root_reference(
    [](double t) { return t * t + 1.0; }, [](double t) { return 2.0 * t; },
    -2.0, 2.0, options);
  check(!none.found, "root-free interval should remain root-free");
}

void test_periodic_bicubic_spline()
{
  constexpr std::size_t n_theta = 8;
  constexpr std::size_t n_phi = 10;
  constexpr int nfp = 5;
  std::vector<double> constant(n_theta * n_phi, 3.25);
  UniformPeriodicBicubicSpline spline(n_theta, n_phi, nfp, constant);

  for (double theta : {-7.0, -0.2, 0.0, 1.1, 8.9}) {
    for (double phi : {-3.0, 0.0, 0.77, 4.4}) {
      const auto sample = spline.sample(theta, phi);
      check_near(sample.value, 3.25, 1.0e-13, "constant spline value");
      check_near(sample.dtheta, 0.0, 1.0e-12, "constant spline theta derivative");
      check_near(sample.dphi, 0.0, 1.0e-12, "constant spline phi derivative");
      const auto periodic = spline.sample(
        theta + 2.0 * 3.141592653589793238462643383279502884,
        phi + 2.0 * 3.141592653589793238462643383279502884 / static_cast<double>(nfp));
      check_near(periodic.value, sample.value, 1.0e-12, "spline periodic value");
    }
  }

  std::vector<double> coefficients(n_theta * n_phi);
  for (std::size_t i = 0; i < n_theta; ++i) {
    for (std::size_t j = 0; j < n_phi; ++j) {
      coefficients[i * n_phi + j] = 2.0 + 0.1 * std::sin(0.7 * static_cast<double>(i))
                                    + 0.05 * std::cos(0.4 * static_cast<double>(j));
    }
  }
  UniformPeriodicBicubicSpline varying(n_theta, n_phi, nfp, coefficients);
  const double theta = 1.234;
  const double phi = 0.321;
  const double h = 1.0e-6;
  const auto sample = varying.sample(theta, phi);
  const double fd_theta =
    (varying.sample(theta + h, phi).value - varying.sample(theta - h, phi).value)
    / (2.0 * h);
  const double fd_phi =
    (varying.sample(theta, phi + h).value - varying.sample(theta, phi - h).value)
    / (2.0 * h);
  check_near(sample.dtheta, fd_theta, 2.0e-8, "spline analytic theta derivative");
  check_near(sample.dphi, fd_phi, 2.0e-8, "spline analytic phi derivative");
}

PeriodicRadialSurface make_torus(double major_radius, double minor_radius)
{
  const double outer = major_radius + minor_radius;
  return PeriodicRadialSurface(stellarcsg::circular_axis(major_radius),
    stellarcsg::constant_radius(minor_radius),
    BoundingBox {{-outer, -outer, -minor_radius}, {outer, outer, minor_radius}},
    outer);
}

void test_exact_torus()
{
  auto torus = make_torus(5.0, 1.0);
  check_near(torus.evaluate({6.0, 0.0, 0.0}), 0.0, 1.0e-13,
    "outer torus surface evaluation");
  check_near(torus.evaluate({5.0, 0.0, 0.0}), -1.0, 1.0e-13,
    "inside torus evaluation");
  check_near(torus.evaluate({7.0, 0.0, 0.0}), 1.0, 1.0e-13,
    "outside torus evaluation");

  const Vec3 outer_normal = torus.normal({6.0, 0.0, 0.0});
  check_near(outer_normal.x, 1.0, 1.0e-13, "outer torus normal x");
  check_near(outer_normal.y, 0.0, 1.0e-13, "outer torus normal y");
  check_near(outer_normal.z, 0.0, 1.0e-13, "outer torus normal z");

  const auto options = root_options();
  auto inward = torus.distance_reference({7.0, 0.0, 0.0}, {-1.0, 0.0, 0.0},
    false, options);
  check(inward.found, "outside-to-torus crossing should be found");
  check_near(inward.distance, 1.0, 1.0e-9, "outside-to-torus distance");

  auto from_origin = torus.distance_reference({0.0, 0.0, 0.0}, {1.0, 0.0, 0.0},
    false, options);
  check(from_origin.found, "origin-to-inner-torus crossing should be found");
  check_near(from_origin.distance, 4.0, 1.0e-9, "origin-to-inner-torus distance");

  auto tangent = torus.distance_reference({6.0, -2.0, 0.0}, {0.0, 1.0, 0.0},
    false, options);
  check(tangent.found, "tangent torus crossing should be found");
  check_near(tangent.distance, 2.0, 2.0e-8, "tangent torus distance");

  auto coincident_outward = torus.distance_reference({6.0, 0.0, 0.0},
    {1.0, 0.0, 0.0}, true, options);
  check(!coincident_outward.found,
    "coincident outward ray should not immediately recross the surface");

  auto coincident_inward = torus.distance_reference({6.0, 0.0, 0.0},
    {-1.0, 0.0, 0.0}, true, options);
  check(coincident_inward.found, "coincident inward ray should find the next crossing");
  check_near(coincident_inward.distance, 2.0, 1.0e-8,
    "coincident inward next crossing");

  // Deterministic radial-ray sweep across the complete poloidal/toroidal domain.
  // For a circular torus these rays have an exact first-intersection distance.
  constexpr double start_rho = 1.75;
  for (int iphi = 0; iphi < 16; ++iphi) {
    const double phi = 2.0 * 3.141592653589793238462643383279502884
                       * static_cast<double>(iphi) / 16.0;
    for (int itheta = 0; itheta < 32; ++itheta) {
      const double theta = 2.0 * 3.141592653589793238462643383279502884
                           * static_cast<double>(itheta) / 32.0;
      const double R = 5.0 + start_rho * std::cos(theta);
      const Vec3 origin {R * std::cos(phi), R * std::sin(phi),
        start_rho * std::sin(theta)};
      const Vec3 inward_direction {-std::cos(theta) * std::cos(phi),
        -std::cos(theta) * std::sin(phi), -std::sin(theta)};
      const auto radial = torus.distance_reference(origin, inward_direction,
        false, options);
      check(radial.found, "torus radial sweep crossing should be found");
      if (radial.found) {
        check_near(radial.distance, 0.75, 3.0e-8,
          "torus radial sweep exact distance");
      }
    }
  }

  // Tangent lines at the outer equator exercise tangent detection away from a
  // sample-grid-aligned root and across the atan2 branch cut.
  constexpr double tangent_offset = 1.23456789;
  for (int iphi = 0; iphi < 12; ++iphi) {
    const double phi = 2.0 * 3.141592653589793238462643383279502884
                       * static_cast<double>(iphi) / 12.0;
    const Vec3 surface_point {6.0 * std::cos(phi), 6.0 * std::sin(phi), 0.0};
    const Vec3 tangent_direction {-std::sin(phi), std::cos(phi), 0.0};
    const Vec3 origin = surface_point - tangent_offset * tangent_direction;
    const auto grazing = torus.distance_reference(origin, tangent_direction,
      false, options);
    check(grazing.found, "toroidal tangent sweep root should be found");
    if (grazing.found) {
      check_near(grazing.distance, tangent_offset, 4.0e-8,
        "toroidal tangent sweep distance");
    }
  }

  auto nonunit = torus.distance_reference({7.0, 0.0, 0.0}, {-2.0, 0.0, 0.0},
    false, options);
  check(nonunit.found, "non-unit direction should be normalized");
  check_near(nonunit.distance, 1.0, 1.0e-9,
    "distance should be physical length for a non-unit direction");
}

void test_shaped_axisymmetric_surface()
{
  constexpr double major_radius = 5.0;
  const auto radius = [](double theta, double) {
    const double value = 1.0 + 0.25 * std::cos(theta) - 0.10 * std::cos(2.0 * theta);
    const double dtheta = -0.25 * std::sin(theta) + 0.20 * std::sin(2.0 * theta);
    return RadiusSample {value, dtheta, 0.0};
  };
  PeriodicRadialSurface surface(stellarcsg::circular_axis(major_radius), radius,
    BoundingBox {{-6.4, -6.4, -1.4}, {6.4, 6.4, 1.4}}, 6.4);

  for (double theta : {-2.7, -1.0, 0.0, 0.8, 2.4}) {
    const double rho = radius(theta, 0.0).value;
    for (double phi : {0.0, 0.4, 2.0}) {
      const double R = major_radius + rho * std::cos(theta);
      const Vec3 point {R * std::cos(phi), R * std::sin(phi), rho * std::sin(theta)};
      check_near(surface.evaluate(point), 0.0, 2.0e-12,
        "shaped axisymmetric surface point");
    }
  }

  const auto crossing = surface.distance_reference({7.0, 0.0, 0.0},
    {-1.0, 0.0, 0.0}, false, root_options());
  check(crossing.found, "shaped axisymmetric radial crossing should be found");
  check_near(crossing.distance, 0.85, 2.0e-8,
    "shaped axisymmetric outer crossing distance");
}

void test_helical_surface_and_gradient()
{
  constexpr double major_radius = 5.0;
  constexpr double epsilon = 0.12;
  constexpr double m = 2.0;
  constexpr double n = 1.0;
  constexpr int nfp = 5;
  const auto radius = [](double theta, double phi) {
    const double phase = m * theta - n * static_cast<double>(nfp) * phi;
    return RadiusSample {
      1.0 + epsilon * std::cos(phase),
      -epsilon * m * std::sin(phase),
      epsilon * n * static_cast<double>(nfp) * std::sin(phase),
    };
  };
  PeriodicRadialSurface surface(stellarcsg::circular_axis(major_radius), radius,
    BoundingBox {{-6.2, -6.2, -1.2}, {6.2, 6.2, 1.2}}, 6.2);

  const double theta = 0.73;
  const double phi = 0.19;
  const double rho = radius(theta, phi).value;
  const double R = major_radius + rho * std::cos(theta);
  const Vec3 point {R * std::cos(phi), R * std::sin(phi), rho * std::sin(theta)};
  check_near(surface.evaluate(point), 0.0, 2.0e-12, "helical surface point");

  const double periodic_phi = phi + 2.0 * 3.141592653589793238462643383279502884 / static_cast<double>(nfp);
  const double periodic_rho = radius(theta, periodic_phi).value;
  const double periodic_R = major_radius + periodic_rho * std::cos(theta);
  const Vec3 periodic_point {periodic_R * std::cos(periodic_phi),
    periodic_R * std::sin(periodic_phi), periodic_rho * std::sin(theta)};
  check_near(surface.evaluate(periodic_point), 0.0, 3.0e-12,
    "helical field-period closure");

  const Vec3 gradient = surface.gradient(point);
  const double h = 1.0e-6;
  const double fd_x =
    (surface.evaluate(point + Vec3 {h, 0.0, 0.0})
      - surface.evaluate(point - Vec3 {h, 0.0, 0.0}))
    / (2.0 * h);
  const double fd_y =
    (surface.evaluate(point + Vec3 {0.0, h, 0.0})
      - surface.evaluate(point - Vec3 {0.0, h, 0.0}))
    / (2.0 * h);
  const double fd_z =
    (surface.evaluate(point + Vec3 {0.0, 0.0, h})
      - surface.evaluate(point - Vec3 {0.0, 0.0, h}))
    / (2.0 * h);
  check_near(gradient.x, fd_x, 2.0e-7, "helical gradient x");
  check_near(gradient.y, fd_y, 2.0e-7, "helical gradient y");
  check_near(gradient.z, fd_z, 2.0e-7, "helical gradient z");

  const Vec3 radial_direction {
    std::cos(theta) * std::cos(phi),
    std::cos(theta) * std::sin(phi),
    std::sin(theta),
  };
  const double start_rho = 2.0;
  const double start_R = major_radius + start_rho * std::cos(theta);
  const Vec3 origin {start_R * std::cos(phi), start_R * std::sin(phi),
    start_rho * std::sin(theta)};
  const auto crossing = surface.distance_reference(origin, -radial_direction,
    false, root_options());
  check(crossing.found, "helical radial crossing should be found");
  check_near(crossing.distance, start_rho - rho, 3.0e-8,
    "helical radial crossing distance");

  for (int iphi = 0; iphi < 10; ++iphi) {
    const double sweep_phi = 2.0 * 3.141592653589793238462643383279502884
                             * static_cast<double>(iphi) / 10.0;
    for (int itheta = 0; itheta < 20; ++itheta) {
      const double sweep_theta = 2.0 * 3.141592653589793238462643383279502884
                                 * static_cast<double>(itheta) / 20.0;
      const double target_rho = radius(sweep_theta, sweep_phi).value;
      constexpr double sweep_start_rho = 1.5;
      const double sweep_R = major_radius + sweep_start_rho * std::cos(sweep_theta);
      const Vec3 sweep_origin {sweep_R * std::cos(sweep_phi),
        sweep_R * std::sin(sweep_phi), sweep_start_rho * std::sin(sweep_theta)};
      const Vec3 sweep_direction {-std::cos(sweep_theta) * std::cos(sweep_phi),
        -std::cos(sweep_theta) * std::sin(sweep_phi), -std::sin(sweep_theta)};
      const auto sweep_crossing = surface.distance_reference(sweep_origin,
        sweep_direction, false, root_options());
      check(sweep_crossing.found, "helical radial sweep crossing should be found");
      if (sweep_crossing.found) {
        check_near(sweep_crossing.distance, sweep_start_rho - target_rho, 4.0e-8,
          "helical radial sweep exact distance");
      }
    }
  }
}

} // namespace

int main()
{
  try {
    test_root_solver();
    test_periodic_bicubic_spline();
    test_exact_torus();
    test_shaped_axisymmetric_surface();
    test_helical_surface_and_gradient();
  } catch (const std::exception& error) {
    ++failures;
    std::cerr << "UNCAUGHT EXCEPTION: " << error.what() << '\n';
  }

  if (failures != 0) {
    std::cerr << failures << " test assertion(s) failed\n";
    return EXIT_FAILURE;
  }
  std::cout << "All StellarCSG reference-kernel tests passed\n";
  return EXIT_SUCCESS;
}
