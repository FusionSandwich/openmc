#include "stellarcsg/performance_counters.hpp"

#include <algorithm>
#include <cmath>

namespace stellarcsg {
namespace {

#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
thread_local SurfacePerformanceCounters counters;

std::size_t integer_bin(std::uint64_t value) noexcept
{
  std::size_t bin = 0;
  while (value > 1 && bin + 1 < performance_histogram_bins) {
    value >>= 1;
    ++bin;
  }
  return bin;
}

std::size_t logarithmic_bin(double value) noexcept
{
  if (!(value > 0.0) || !std::isfinite(value)) return 0;
  const int exponent = std::ilogb(value);
  return static_cast<std::size_t>(std::clamp(
    exponent + static_cast<int>(performance_histogram_bins / 2), 0,
    static_cast<int>(performance_histogram_bins - 1)));
}
#endif

} // namespace

SurfacePerformanceCounters& SurfacePerformanceCounters::operator+=(
  const SurfacePerformanceCounters& other) noexcept
{
#define STELLARCSG_MERGE_FIELD(name) name += other.name
  STELLARCSG_MERGE_FIELD(distance_calls);
  STELLARCSG_MERGE_FIELD(evaluate_calls);
  STELLARCSG_MERGE_FIELD(normal_calls);
  STELLARCSG_MERGE_FIELD(candidate_bvh_nodes);
  STELLARCSG_MERGE_FIELD(candidate_patches_or_segments);
  STELLARCSG_MERGE_FIELD(proxy_intersections);
  STELLARCSG_MERGE_FIELD(proxy_seeds);
  STELLARCSG_MERGE_FIELD(newton_iterations);
  STELLARCSG_MERGE_FIELD(newton_failures);
  STELLARCSG_MERGE_FIELD(local_interval_certifications);
  STELLARCSG_MERGE_FIELD(local_subdivision_calls);
  STELLARCSG_MERGE_FIELD(local_subdivision_nodes);
  STELLARCSG_MERGE_FIELD(global_reference_calls);
  STELLARCSG_MERGE_FIELD(tangent_or_grazing_cases);
  STELLARCSG_MERGE_FIELD(coincident_cases);
  STELLARCSG_MERGE_FIELD(rejected_roots);
  STELLARCSG_MERGE_FIELD(deduplicated_roots);
  STELLARCSG_MERGE_FIELD(accepted_roots);
  STELLARCSG_MERGE_FIELD(no_hit_returns);
  STELLARCSG_MERGE_FIELD(cache_hits);
  STELLARCSG_MERGE_FIELD(cache_misses);
#undef STELLARCSG_MERGE_FIELD
  for (std::size_t i = 0; i < performance_histogram_bins; ++i) {
    candidate_histogram[i] += other.candidate_histogram[i];
    newton_histogram[i] += other.newton_histogram[i];
    subdivision_histogram[i] += other.subdivision_histogram[i];
    residual_histogram[i] += other.residual_histogram[i];
    incidence_histogram[i] += other.incidence_histogram[i];
    distance_time_histogram[i] += other.distance_time_histogram[i];
  }
  return *this;
}

bool performance_counters_enabled() noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  return true;
#else
  return false;
#endif
}

SurfacePerformanceCounters performance_counters_snapshot() noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  return counters;
#else
  return {};
#endif
}

void reset_performance_counters() noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  counters = {};
#endif
}

void add_performance_counter(
  PerformanceCounter counter, std::uint64_t amount) noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  switch (counter) {
#define STELLARCSG_COUNTER_CASE(name) \
  case PerformanceCounter::name: counters.name += amount; break
    STELLARCSG_COUNTER_CASE(distance_calls);
    STELLARCSG_COUNTER_CASE(evaluate_calls);
    STELLARCSG_COUNTER_CASE(normal_calls);
    STELLARCSG_COUNTER_CASE(candidate_bvh_nodes);
    STELLARCSG_COUNTER_CASE(candidate_patches_or_segments);
    STELLARCSG_COUNTER_CASE(proxy_intersections);
    STELLARCSG_COUNTER_CASE(proxy_seeds);
    STELLARCSG_COUNTER_CASE(newton_iterations);
    STELLARCSG_COUNTER_CASE(newton_failures);
    STELLARCSG_COUNTER_CASE(local_interval_certifications);
    STELLARCSG_COUNTER_CASE(local_subdivision_calls);
    STELLARCSG_COUNTER_CASE(local_subdivision_nodes);
    STELLARCSG_COUNTER_CASE(global_reference_calls);
    STELLARCSG_COUNTER_CASE(tangent_or_grazing_cases);
    STELLARCSG_COUNTER_CASE(coincident_cases);
    STELLARCSG_COUNTER_CASE(rejected_roots);
    STELLARCSG_COUNTER_CASE(deduplicated_roots);
    STELLARCSG_COUNTER_CASE(accepted_roots);
    STELLARCSG_COUNTER_CASE(no_hit_returns);
    STELLARCSG_COUNTER_CASE(cache_hits);
    STELLARCSG_COUNTER_CASE(cache_misses);
#undef STELLARCSG_COUNTER_CASE
  }
#else
  (void) counter;
  (void) amount;
#endif
}

void record_candidate_count(std::uint64_t value) noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  ++counters.candidate_histogram[integer_bin(value)];
#else
  (void) value;
#endif
}

void record_newton_count(std::uint64_t value) noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  ++counters.newton_histogram[integer_bin(value)];
#else
  (void) value;
#endif
}

void record_subdivision_depth(std::uint64_t value) noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  ++counters.subdivision_histogram[integer_bin(value)];
#else
  (void) value;
#endif
}

void record_residual(double value, double characteristic_length) noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  const double scale = std::max(characteristic_length, 1.0);
  ++counters.residual_histogram[logarithmic_bin(std::abs(value) / scale)];
#else
  (void) value;
  (void) characteristic_length;
#endif
}

void record_incidence(double value) noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  ++counters.incidence_histogram[logarithmic_bin(std::abs(value))];
#else
  (void) value;
#endif
}

void record_distance_time_ns(std::uint64_t value) noexcept
{
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  const std::uint64_t scaled = std::max<std::uint64_t>(1, value / 64);
  ++counters.distance_time_histogram[integer_bin(scaled)];
#else
  (void) value;
#endif
}

} // namespace stellarcsg
