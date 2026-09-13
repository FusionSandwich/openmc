// Diagnostic fixed-bank replay. This is not transport or qualification timing.
// Build against an existing standalone StellarCSG library; no new dependencies.
#include "stellarcsg/compiled_periodic_surface.hpp"
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/performance_counters.hpp"

#include <array>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using stellarcsg::Vec3;
using Clock = std::chrono::steady_clock;
constexpr double pi = 3.1415926535897932384626433832795;
constexpr std::size_t bank_size = 512;
constexpr double radius = 0.25;
constexpr double offset = 0.002;
volatile double sink = 0.0;

struct Ray {
  Vec3 origin;
  Vec3 direction;
};

stellarcsg::SweptSplineSurfaceData coil_data()
{
  stellarcsg::SweptSplineSurfaceData data;
  data.coil_id = 71;
  data.sample_count = 64;
  data.length = 10*pi; // Parameter scale, not measured arc length.
  data.characteristic_length = 9;
  data.major_radius_coefficients.assign(data.sample_count, radius);
  data.minor_radius_coefficients.assign(data.sample_count, radius);
  for (std::size_t i = 0; i < data.sample_count; ++i) {
    const double q = 2*pi*i/data.sample_count;
    for (double value : {5*std::cos(q), 5*std::sin(q), 0.4*std::sin(3*q)})
      data.centerline_coefficients.push_back(value);
    for (double value : {0., 0., 1.}) data.normal_coefficients.push_back(value);
    for (double value : {1., 0., 0.}) data.binormal_coefficients.push_back(value);
  }
  return data;
}

// Independent cardinal cubic basis evaluation and derivative, with no production
// classification, projection, pruning or root solver calls.
std::array<Vec3, 2> center_and_tangent(
  const stellarcsg::SweptSplineSurfaceData& data, double q)
{
  const auto whole = static_cast<long>(std::floor(q));
  const double u = q-std::floor(q);
  const std::array<double, 4> weights {std::pow(1-u, 3)/6,
    (3*u*u*u-6*u*u+4)/6, (-3*u*u*u+3*u*u+3*u+1)/6, u*u*u/6};
  const std::array<double, 4> derivatives {-0.5*(1-u)*(1-u),
    1.5*u*u-2*u, -1.5*u*u+u+0.5, 0.5*u*u};
  Vec3 center {}, tangent {};
  const auto count = static_cast<long>(data.sample_count);
  for (long a = 0; a < 4; ++a) {
    const auto i = static_cast<std::size_t>((whole+a-1+count)%count);
    const Vec3 control {data.centerline_coefficients[3*i],
      data.centerline_coefficients[3*i+1], data.centerline_coefficients[3*i+2]};
    center = center + weights[a]*control;
    tangent = tangent + derivatives[a]*control;
  }
  return {center, stellarcsg::normalized(tangent)};
}

stellarcsg::PeriodicSplineSurfaceData plasma_data()
{
  stellarcsg::PeriodicSplineSurfaceData data;
  data.n_field_periods = 1;
  data.n_theta = 16;
  data.n_phi = 16;
  data.axis_r_coefficients.assign(16, 5.0);
  data.axis_z_coefficients.assign(16, 0.0);
  data.characteristic_length = 6;
  data.force_general_solver = true;
  for (std::size_t i = 0; i < data.n_theta; ++i)
    for (std::size_t j = 0; j < data.n_phi; ++j)
      data.radius_coefficients.push_back(
        1.0 + 0.1*std::cos(2*pi*i/data.n_theta-6*pi*j/data.n_phi));
  return data;
}

void number(double value)
{
  if (std::isfinite(value)) std::cout << value;
  else std::cout << "null";
}

void text(const std::string& value)
{
  std::cout << '"';
  for (const unsigned char c : value) {
    if (c == '"' || c == '\\') std::cout << '\\' << c;
    else if (c < 32) std::cout << "\\u" << std::hex << std::setw(4)
                             << std::setfill('0') << static_cast<unsigned>(c)
                             << std::dec << std::setfill(' ');
    else std::cout << c;
  }
  std::cout << '"';
}

template<class Array> void array(const Array& values)
{
  std::cout << '[';
  bool first = true;
  for (const auto value : values) {
    if (!first) std::cout << ',';
    first = false;
    std::cout << value;
  }
  std::cout << ']';
}

void counters()
{
  if (!stellarcsg::performance_counters_enabled()) {
    std::cout << "null";
    return;
  }
  const auto c = stellarcsg::performance_counters_snapshot();
  std::cout << '{';
#define COUNT(name) std::cout << "\"" #name "\":" << c.name << ','
  COUNT(distance_calls); COUNT(evaluate_calls); COUNT(normal_calls);
  COUNT(candidate_bvh_nodes); COUNT(candidate_patches_or_segments);
  COUNT(proxy_intersections); COUNT(proxy_seeds); COUNT(newton_iterations);
  COUNT(newton_failures); COUNT(local_interval_certifications);
  COUNT(local_subdivision_calls); COUNT(local_subdivision_nodes);
  COUNT(global_reference_calls); COUNT(tangent_or_grazing_cases);
  COUNT(coincident_cases); COUNT(rejected_roots); COUNT(deduplicated_roots);
  COUNT(accepted_roots); COUNT(no_hit_returns); COUNT(cache_hits); COUNT(cache_misses);
#undef COUNT
#define HIST(name) std::cout << "\"" #name "\":"; array(c.name); std::cout << ','
  HIST(candidate_histogram); HIST(newton_histogram); HIST(subdivision_histogram);
  HIST(residual_histogram); HIST(incidence_histogram);
#undef HIST
  std::cout << "\"distance_time_histogram\":";
  array(c.distance_time_histogram);
  std::cout << '}';
}

template<class Surface> void replay(const char* method, const Surface& surface,
  const std::vector<Ray>& bank, int repeats, bool known_bound, double init_seconds)
{
  std::cout << "{\"method\":\"" << method << "\",\"initialization_seconds\":"
            << init_seconds << ",\"correctness\":\"NOT_RUN\",\"phases\":[";
  for (int phase = 0; phase < 3; ++phase) {
    if (phase) std::cout << ',';
    const char* names[] {"evaluate", "normal", "distance"};
    std::size_t exceptions = 0, nonfinite = 0, missing = 0, late = 0, negative = 0;
    std::vector<double> distances(bank.size()*repeats, INFINITY);
    std::vector<unsigned> states(bank.size()*repeats, 0);
    std::vector<std::string> errors(bank.size()*repeats);
    stellarcsg::reset_performance_counters();
    const auto start = Clock::now();
    for (int repetition = 0; repetition < repeats; ++repetition) {
      for (std::size_t i = 0; i < bank.size(); ++i) {
        const auto index = repetition*bank.size()+i;
        try {
          if (phase == 0) {
            const double value = surface.evaluate(bank[i].origin);
            if (std::isfinite(value)) sink = sink + value;
            else { ++nonfinite; states[index] = 1; }
          } else if (phase == 1) {
            const auto normal = surface.normal(bank[i].origin);
            const double value = normal.x+normal.y+normal.z;
            if (std::isfinite(value)) sink = sink + value;
            else { ++nonfinite; states[index] = 1; }
          } else {
            const auto result = surface.distance(bank[i].origin, bank[i].direction, false);
            if (!result.found) { ++missing; states[index] = 2; }
            else {
              distances[index] = result.distance;
              if (!std::isfinite(result.distance)) { ++nonfinite; states[index] = 1; }
              else if (result.distance < 0) { ++negative; states[index] = 3; }
              else if (known_bound && result.distance > offset+1e-8) {
                ++late; states[index] = 4;
              }
              if (std::isfinite(result.distance)) sink = sink + result.distance;
            }
          }
        } catch (const std::exception& error) {
          ++exceptions;
          states[index] = 5;
          errors[index] = error.what();
        }
      }
    }
    const auto seconds = std::chrono::duration<double>(Clock::now()-start).count();
    std::cout << "{\"operation\":\"" << names[phase] << "\",\"calls\":"
              << bank.size()*repeats << ",\"seconds\":" << seconds
              << ",\"ns_per_query\":" << 1e9*seconds/(bank.size()*repeats)
              << ",\"exceptions\":" << exceptions << ",\"nonfinite\":" << nonfinite
              << ",\"missing_hits\":" << missing << ",\"negative_hits\":" << negative
              << ",\"known_hit_bound_violations\":" << late << ",\"counters\":";
    counters();
    std::cout << ",\"query_states\":"; array(states);
    std::cout << ",\"query_errors\":[";
    bool first_error = true;
    for (std::size_t i = 0; i < errors.size(); ++i) {
      if (errors[i].empty()) continue;
      if (!first_error) std::cout << ',';
      first_error = false;
      std::cout << "{\"query_index\":" << i << ",\"message\":";
      text(errors[i]);
      std::cout << '}';
    }
    std::cout << ']';
    if (phase == 2) {
      std::cout << ",\"known_hit_upper_bound_cm\":";
      if (known_bound) std::cout << offset; else std::cout << "null";
      std::cout << ",\"bound_check_state\":\""
                << (!known_bound ? "NOT_RUN" : missing+late+negative+nonfinite
                    ? "FAIL" : exceptions ? "BLOCKED" : "PASS")
                << "\",\"distances_cm\":[";
      for (std::size_t i = 0; i < distances.size(); ++i) {
        if (i) std::cout << ',';
        number(distances[i]);
      }
      std::cout << ']';
    }
    std::cout << '}';
  }
  std::cout << "]}";
}
} // namespace

int main(int argc, char** argv)
{
  int repeats = 1;
  if (argc > 2) return 2;
  if (argc == 2) {
    try {
      std::size_t used = 0;
      repeats = std::stoi(argv[1], &used);
      if (used != std::string(argv[1]).size()) return 2;
    } catch (...) { return 2; }
    if (repeats < 1 || repeats > 100) return 2;
  }
  const auto start = Clock::now();
  const auto data = coil_data();
  const stellarcsg::CompiledSweptSplineSurface coil {data, true};
  const auto coil_init = std::chrono::duration<double>(Clock::now()-start).count();
  const auto plasma_start = Clock::now();
  const stellarcsg::CompiledPeriodicSplineSurface plasma {plasma_data()};
  const auto plasma_init = std::chrono::duration<double>(Clock::now()-plasma_start).count();
  std::vector<Ray> coil_bank, plasma_bank;
  for (std::size_t i = 0; i < bank_size; ++i) {
    const auto frame = center_and_tangent(data, (i+0.375)*data.sample_count/bank_size);
    const Vec3 up {0, 0, 1};
    const auto normal = stellarcsg::normalized(up-stellarcsg::dot(up, frame[1])*frame[1]);
    const auto binormal = stellarcsg::cross(frame[1], normal);
    const double angle = 2*pi*((i*137)%bank_size)/bank_size;
    const auto radial = std::cos(angle)*normal+std::sin(angle)*binormal;
    coil_bank.push_back({frame[0]+(radius+offset)*radial, -1.0*radial});
    const auto sample = plasma.sample_parametric(2*pi*(i+0.375)/bank_size,
      2*pi*((i*137)%bank_size+0.25)/bank_size);
    const auto outward = stellarcsg::normalized(stellarcsg::cross(sample.dtheta, sample.dphi));
    plasma_bank.push_back({sample.position+offset*outward, -1.0*outward});
  }
  std::cout << std::setprecision(17)
    << "{\"schema\":\"stellarcsg.fixed-replay-diagnostic/v1\","
    << "\"qualification\":\"NOT_RUN\",\"bank_size\":" << bank_size
    << ",\"repeats\":" << repeats << ",\"counters_enabled\":"
    << (stellarcsg::performance_counters_enabled() ? "true" : "false")
    << ",\"notes\":\"No transport, warmup, comparative ratio or qualification. "
    << "Coil bound checks cannot certify nearest completeness. Plasma bank uses "
    << "production parametric samples and has no independent oracle. Timings "
    << "include result bookkeeping and exception handling. Query states: "
    << "0=returned,1=nonfinite,2=missing,3=negative,4=late,5=exception.\",\"cases\":[";
  replay("legacy_swept_span_v1_nonplanar_circular", coil, coil_bank, repeats, true, coil_init);
  std::cout << ',';
  replay("legacy_periodic_patch_v1_helical", plasma, plasma_bank, repeats, false, plasma_init);
  std::cout << "]}\n";
}
