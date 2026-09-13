// Independent cardinal-basis replay. Sampled sign brackets do not certify
// nearest-root completeness, tangencies, or absence of narrow crossings.
#include "stellarcsg/coefficient_file.hpp"
#include "stellarcsg/compiled_periodic_surface.hpp"
#include "stellarcsg/performance_counters.hpp"
#include <array>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {
using stellarcsg::Vec3;
constexpr double pi = 3.1415926535897932384626433832795;
constexpr double inf = std::numeric_limits<double>::infinity();
std::array<double, 4> basis(double u)
{
  return {std::pow(1-u, 3)/6, (3*u*u*u-6*u*u+4)/6,
    (-3*u*u*u+3*u*u+3*u+1)/6, u*u*u/6};
}
std::size_t wrap(long i, std::size_t count)
{
  const auto n = static_cast<long>(count);
  return static_cast<std::size_t>((i%n+n)%n);
}
double scalar(const std::vector<double>& values, double q)
{
  const auto whole = static_cast<long>(std::floor(q));
  const auto w = basis(q-std::floor(q));
  double result = 0;
  for (long a = 0; a < 4; ++a)
    result += values[wrap(whole+a-1, values.size())]*w[a];
  return result;
}
double radial(const stellarcsg::PeriodicSplineSurfaceData& d, double theta, double phi)
{
  const double x = theta*d.n_theta/(2*pi);
  const double y = phi*d.n_phi*d.n_field_periods/(2*pi);
  const auto ix = static_cast<long>(std::floor(x));
  const auto iy = static_cast<long>(std::floor(y));
  const auto wx = basis(x-std::floor(x)), wy = basis(y-std::floor(y));
  double result = 0;
  for (long a = 0; a < 4; ++a)
    for (long b = 0; b < 4; ++b)
      result += wx[a]*wy[b]*d.radius_coefficients[
        wrap(ix+a-1, d.n_theta)*d.n_phi+wrap(iy+b-1, d.n_phi)];
  return result;
}
Vec3 position(const stellarcsg::PeriodicSplineSurfaceData& d, double theta, double phi)
{
  const double q = phi*d.axis_r_coefficients.size()*d.n_field_periods/(2*pi);
  const double radius = radial(d, theta, phi);
  const double r = scalar(d.axis_r_coefficients, q)+radius*std::cos(theta);
  return {r*std::cos(phi), r*std::sin(phi),
    scalar(d.axis_z_coefficients, q)+radius*std::sin(theta)};
}
double implicit(const stellarcsg::PeriodicSplineSurfaceData& d, Vec3 point)
{
  const double phi = std::atan2(point.y, point.x);
  const double q = phi*d.axis_r_coefficients.size()*d.n_field_periods/(2*pi);
  const double r = std::hypot(point.x, point.y)-scalar(d.axis_r_coefficients, q);
  const double z = point.z-scalar(d.axis_z_coefficients, q);
  return std::hypot(r, z)-radial(d, std::atan2(z, r), phi);
}
stellarcsg::PeriodicSplineSurfaceData helical_data()
{
  stellarcsg::PeriodicSplineSurfaceData d;
  d.n_theta = d.n_phi = 16;
  d.axis_r_coefficients.assign(16, 5);
  d.axis_z_coefficients.assign(16, 0);
  d.characteristic_length = 6;
  d.force_general_solver = true;
  for (std::size_t i = 0; i < 16; ++i)
    for (std::size_t j = 0; j < 16; ++j)
      d.radius_coefficients.push_back(1+.1*std::cos(2*pi*i/16-6*pi*j/16));
  return d;
}
struct Ray { Vec3 origin; Vec3 direction; bool coincident; const char* kind; };
double bracket_root(const stellarcsg::PeriodicSplineSurfaceData& d,
  const Ray& ray, double scale)
{
  double a = ray.coincident ? 1e-8*scale : 0;
  double fa = implicit(d, ray.origin+a*ray.direction);
  for (int i = 1; i <= 512; ++i) {
    double b = 4*scale*i/512;
    const double fb = implicit(d, ray.origin+b*ray.direction);
    if (std::isfinite(fa) && std::isfinite(fb) && std::signbit(fa) != std::signbit(fb)) {
      for (int k = 0; k < 64; ++k) {
        const double mid = .5*(a+b);
        const double fm = implicit(d, ray.origin+mid*ray.direction);
        if (std::signbit(fa) != std::signbit(fm)) b = mid;
        else { a = mid; fa = fm; }
      }
      return .5*(a+b);
    }
    a = b; fa = fb;
  }
  return inf;
}
void number(double value)
{
  if (std::isfinite(value)) std::cout << value;
  else std::cout << "null";
}
void vector(Vec3 value)
{
  std::cout << '[' << value.x << ',' << value.y << ',' << value.z << ']';
}
void text(const std::string& value)
{
  std::cout << '"';
  for (const unsigned char c : value) {
    if (c == '"' || c == '\\') std::cout << '\\' << c;
    else if (c < 32) std::cout << "\\u" << std::hex << std::setw(4)
      << std::setfill('0') << static_cast<unsigned>(c) << std::dec << std::setfill(' ');
    else std::cout << c;
  }
  std::cout << '"';
}
std::uint64_t bits(double value)
{
  std::uint64_t result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
} // namespace

int main(int argc, char** argv)
{
  auto data = helical_data();
  std::string label = "synthetic_helical_16x16";
  int repeats = 1;
  if (argc == 2 || argc == 4) {
    try {
      const std::string argument = argv[argc-1];
      std::size_t used = 0;
      repeats = std::stoi(argument, &used);
      if (used != argument.size() || repeats < 1 || repeats > 1000) return 2;
    } catch (...) { return 2; }
  }
  if (argc == 3 || argc == 4) {
#ifdef STELLARCSG_HAS_HDF5
    data = stellarcsg::read_periodic_spline_surface_hdf5(argv[1], argv[2]);
    data.force_general_solver = true;
    label = "supplied_hdf5";
#else
    std::cerr << "HDF5 support required\n";
    return 2;
#endif
  } else if (argc != 1 && argc != 2) return 2;
  const stellarcsg::CompiledPeriodicSplineSurface surface {data};
  std::vector<Ray> rays;
  for (std::size_t i = 0; i < 256; ++i) {
    const double theta = 2*pi*(i+.375)/256;
    const double phi = 2*pi*((i*137)%256+.25)/256;
    const auto p = position(data, theta, phi);
    const auto dt = position(data, theta+1e-5, phi)-position(data, theta-1e-5, phi);
    const auto dp = position(data, theta, phi+1e-5)-position(data, theta, phi-1e-5);
    const auto n = stellarcsg::normalized(stellarcsg::cross(dt, dp));
    if (i < 128) rays.push_back({p+.002*n, -n, false, "near_normal"});
    else if (i < 192) {
      const double epsilon = std::pow(10., -static_cast<int>(i%6)-2);
      rays.push_back({p+.002*n, stellarcsg::normalized(stellarcsg::normalized(dt)-epsilon*n),
        false, "grazing_ladder"});
    } else if (i < 224)
      rays.push_back({p+data.characteristic_length*n, -n, false, "far_tail"});
    else if (i < 240) rays.push_back({p-.002*n, n, false, "inside"});
    else rays.push_back({p, n, true, "coincident"});
  }
  stellarcsg::reset_performance_counters();
  std::vector<double> distances, residuals;
  std::vector<unsigned> found, exception;
  std::vector<std::string> errors;
  std::vector<std::uint64_t> return_digests;
  std::size_t repeat_mismatches = 0;
  const auto start = std::chrono::steady_clock::now();
  for (int repetition = 0; repetition < repeats; ++repetition) {
    std::uint64_t digest = 14695981039346656037ULL;
    for (std::size_t i = 0; i < rays.size(); ++i) {
      const auto& ray = rays[i];
      unsigned hit = 0, failed = 0;
      double distance = inf, residual = inf;
      std::string error_text;
      try {
        const auto result = surface.distance(ray.origin, ray.direction, ray.coincident);
        hit = result.found; distance = result.distance; residual = result.residual;
      } catch (const std::exception& error) {
        failed = 1; error_text = error.what();
      }
      for (const auto value : {bits(distance), bits(residual), std::uint64_t(hit),
                               std::uint64_t(failed)}) {
        digest ^= value; digest *= 1099511628211ULL;
      }
      if (repetition == 0) {
        found.push_back(hit); distances.push_back(distance); residuals.push_back(residual);
        exception.push_back(failed); errors.push_back(error_text);
      } else if (hit != found[i] || failed != exception[i]
          || bits(distance) != bits(distances[i]) || bits(residual) != bits(residuals[i])
          || error_text != errors[i]) ++repeat_mismatches;
    }
    return_digests.push_back(digest);
  }
  const double seconds = std::chrono::duration<double>(
    std::chrono::steady_clock::now()-start).count();
  const auto counters = stellarcsg::performance_counters_snapshot();
  // Separate one-bank timer-instrumented tail diagnostics, excluded from seconds
  // above. These observations must not be substituted for minimally instrumented
  // ablation timing; all query timing samples are retained below.
  std::vector<double> query_ns;
  for (const auto& ray : rays) {
    const auto query_start = std::chrono::steady_clock::now();
    try {
      const auto result = surface.distance(ray.origin, ray.direction, ray.coincident);
      // Observable checksum use prevents dead-call elimination.
      if (result.found && !std::isfinite(result.distance)) ++repeat_mismatches;
    } catch (const std::exception&) {}
    query_ns.push_back(std::chrono::duration<double, std::nano>(
      std::chrono::steady_clock::now()-query_start).count());
  }
  std::cout << std::setprecision(17);
  int failures = repeat_mismatches ? 1 : 0, blocked = 0;
  for (std::size_t i = 0; i < rays.size(); ++i) {
    const auto& ray = rays[i];
    const double expected = bracket_root(data, ray, data.characteristic_length);
    const double tolerance = 2e-7*std::max(1., data.characteristic_length);
    const double residual = found[i]
      ? std::abs(implicit(data, ray.origin+distances[i]*ray.direction)) : inf;
    const char* state = "PASS";
    if (found[i] && (!std::isfinite(distances[i]) || distances[i] < 0
        || !std::isfinite(residual) || residual > tolerance)) {
      state = "FAIL"; ++failures;
    } else if (exception[i] || !std::isfinite(expected)
        || (found[i] && distances[i] < expected-tolerance)) {
      state = "BLOCKED"; ++blocked;
    } else if (!found[i] || distances[i] > expected+tolerance) {
      state = "FAIL"; ++failures;
    }
    std::cout << "{\"kind\":\"ray\",\"index\":" << i << ",\"family\":\""
              << ray.kind << "\",\"found\":" << (found[i] ? "true" : "false")
              << ",\"origin\":";
    vector(ray.origin);
    std::cout << ",\"direction\":"; vector(ray.direction);
    std::cout << ",\"coincident\":" << (ray.coincident ? "true" : "false")
              << ",\"error\":";
    text(errors[i]);
    std::cout << ",\"distance\":";
    number(distances[i]);
    std::cout << ",\"production_residual\":"; number(residuals[i]);
    std::cout << ",\"independent_residual\":"; number(residual);
    std::cout << ",\"sampled_first_bracket\":"; number(expected);
    std::cout << ",\"oracle_state\":\"" << state << "\"}\n";
  }
  std::cout << "{\"kind\":\"summary\",\"case\":\"" << label
            << "\",\"qualification\":\"NOT_RUN\",\"oracle\":\"independent cardinal basis, "
            << "sampled sign brackets; no tangency or completeness certification\","
            << "\"bank_size\":" << rays.size() << ",\"repeats\":" << repeats
            << ",\"calls\":" << rays.size()*repeats << ",\"seconds\":" << seconds
            << ",\"ns_per_query\":" << 1e9*seconds/(rays.size()*repeats)
            << ",\"repeat_mismatches\":" << repeat_mismatches
            << ",\"failures\":" << failures << ",\"blocked\":" << blocked
            << ",\"counters_enabled\":"
            << (stellarcsg::performance_counters_enabled() ? "true" : "false")
            << ",\"evaluate_calls\":";
  if (stellarcsg::performance_counters_enabled()) std::cout << counters.evaluate_calls;
  else std::cout << "null";
  std::cout << ",\"return_digests\":[";
  for (std::size_t i = 0; i < return_digests.size(); ++i) {
    if (i) std::cout << ',';
    std::cout << '"' << std::hex << return_digests[i] << std::dec << '"';
  }
  std::cout << "],\"separate_diagnostic_query_ns\":[";
  for (std::size_t i = 0; i < query_ns.size(); ++i) {
    if (i) std::cout << ',';
    std::cout << query_ns[i];
  }
  auto ordered = query_ns;
  std::sort(ordered.begin(), ordered.end());
  std::cout << "],\"separate_diagnostic_min_ns\":" << ordered.front()
            << ",\"separate_diagnostic_p95_ns\":" << ordered[243]
            << ",\"separate_diagnostic_max_ns\":" << ordered.back() << "}\n";
  return failures ? 1 : 0;
}
