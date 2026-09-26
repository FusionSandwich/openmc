#pragma once
namespace stellarcsg {
enum class PerformanceCounter {candidate_bvh_nodes};
inline void add_performance_counter(PerformanceCounter) {}
inline bool performance_counters_enabled() {return false;}
struct TestCounters {
  long distance_calls=0,evaluate_calls=0,normal_calls=0,candidate_bvh_nodes=0,
    candidate_patches_or_segments=0,proxy_seeds=0,newton_iterations=0,newton_failures=0,
    local_subdivision_calls=0,global_reference_calls=0,accepted_roots=0,
    no_hit_returns=0,cache_hits=0,cache_misses=0;
};
inline TestCounters performance_counters_snapshot() {return {};}
}
