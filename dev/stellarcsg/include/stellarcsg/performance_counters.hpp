#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
#include <chrono>
#endif

namespace stellarcsg {

constexpr std::size_t performance_histogram_bins = 16;

struct SurfacePerformanceCounters {
  std::uint64_t distance_calls {0};
  std::uint64_t evaluate_calls {0};
  std::uint64_t normal_calls {0};
  std::uint64_t candidate_bvh_nodes {0};
  std::uint64_t candidate_patches_or_segments {0};
  std::uint64_t proxy_intersections {0};
  std::uint64_t proxy_seeds {0};
  std::uint64_t newton_iterations {0};
  std::uint64_t newton_failures {0};
  std::uint64_t local_interval_certifications {0};
  std::uint64_t local_subdivision_calls {0};
  std::uint64_t local_subdivision_nodes {0};
  std::uint64_t global_reference_calls {0};
  std::uint64_t tangent_or_grazing_cases {0};
  std::uint64_t coincident_cases {0};
  std::uint64_t rejected_roots {0};
  std::uint64_t deduplicated_roots {0};
  std::uint64_t accepted_roots {0};
  std::uint64_t no_hit_returns {0};
  std::uint64_t cache_hits {0};
  std::uint64_t cache_misses {0};
  std::array<std::uint64_t, performance_histogram_bins> candidate_histogram {};
  std::array<std::uint64_t, performance_histogram_bins> newton_histogram {};
  std::array<std::uint64_t, performance_histogram_bins> subdivision_histogram {};
  std::array<std::uint64_t, performance_histogram_bins> residual_histogram {};
  std::array<std::uint64_t, performance_histogram_bins> incidence_histogram {};
  std::array<std::uint64_t, performance_histogram_bins> distance_time_histogram {};

  SurfacePerformanceCounters& operator+=(
    const SurfacePerformanceCounters& other) noexcept;
};

enum class PerformanceCounter : std::uint8_t {
  distance_calls,
  evaluate_calls,
  normal_calls,
  candidate_bvh_nodes,
  candidate_patches_or_segments,
  proxy_intersections,
  proxy_seeds,
  newton_iterations,
  newton_failures,
  local_interval_certifications,
  local_subdivision_calls,
  local_subdivision_nodes,
  global_reference_calls,
  tangent_or_grazing_cases,
  coincident_cases,
  rejected_roots,
  deduplicated_roots,
  accepted_roots,
  no_hit_returns,
  cache_hits,
  cache_misses,
};

[[nodiscard]] bool performance_counters_enabled() noexcept;
[[nodiscard]] SurfacePerformanceCounters performance_counters_snapshot() noexcept;
void reset_performance_counters() noexcept;
void add_performance_counter(
  PerformanceCounter counter, std::uint64_t amount = 1) noexcept;
void record_candidate_count(std::uint64_t value) noexcept;
void record_newton_count(std::uint64_t value) noexcept;
void record_subdivision_depth(std::uint64_t value) noexcept;
void record_residual(double value, double characteristic_length) noexcept;
void record_incidence(double value) noexcept;
void record_distance_time_ns(std::uint64_t value) noexcept;

class ScopedDistanceTimer {
public:
#ifdef STELLARCSG_ENABLE_PERFORMANCE_COUNTERS
  ScopedDistanceTimer() noexcept : start_ {Clock::now()} {}
  ~ScopedDistanceTimer() noexcept
  {
    const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
      Clock::now() - start_).count();
    record_distance_time_ns(static_cast<std::uint64_t>(elapsed));
  }

private:
  using Clock = std::chrono::steady_clock;
  Clock::time_point start_;
#else
  ScopedDistanceTimer() noexcept = default;
#endif
};

} // namespace stellarcsg
