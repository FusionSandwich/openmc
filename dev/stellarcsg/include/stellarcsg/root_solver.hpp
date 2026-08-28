#ifndef STELLARCSG_ROOT_SOLVER_HPP
#define STELLARCSG_ROOT_SOLVER_HPP

#include <functional>
#include <limits>
#include <vector>

namespace stellarcsg {

enum class RootKind {
  sign_change,
  sampled_zero,
  stationary_tangent,
};

struct RootSearchOptions {
  int initial_subdivisions {128};
  int max_refinement_levels {7};
  int max_bisection_iterations {128};
  double absolute_t_tolerance {1.0e-11};
  double relative_t_tolerance {1.0e-11};
  double absolute_f_tolerance {1.0e-10};
  double derivative_tolerance {1.0e-12};
  double tangent_residual_multiplier {16.0};
  double duplicate_t_multiplier {8.0};
  bool require_refinement_stability {true};
};

struct RootCandidate {
  double t {std::numeric_limits<double>::infinity()};
  double residual {std::numeric_limits<double>::infinity()};
  RootKind kind {RootKind::sign_change};
};

struct RootSearchDiagnostics {
  int refinement_levels {0};
  long function_evaluations {0};
  long derivative_evaluations {0};
  long sign_change_brackets {0};
  long stationary_brackets {0};
  long sampled_zero_candidates {0};
  long deduplicated_candidates {0};
};

struct RootSearchResult {
  bool found {false};
  RootCandidate root {};
  RootSearchDiagnostics diagnostics {};
  std::vector<RootCandidate> candidates {};
};

using ScalarFunction = std::function<double(double)>;

// Reference search intended as the independent correctness oracle for the first
// StellarCSG development gates. It scans the full finite interval, brackets all
// detected sign changes, and searches derivative stationary points for tangent
// roots. It is deliberately conservative and not the eventual transport fast
// path. A future certified implementation must add interval bounds.
[[nodiscard]] RootSearchResult find_nearest_root_reference(
  const ScalarFunction& function, const ScalarFunction& derivative,
  double t_min, double t_max, const RootSearchOptions& options = {});

} // namespace stellarcsg

#endif
