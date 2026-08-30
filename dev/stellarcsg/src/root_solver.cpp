#include "stellarcsg/root_solver.hpp"

#include <algorithm>
#include <cmath>
#include <optional>
#include <stdexcept>
#include <utility>

namespace stellarcsg {
namespace {

bool finite(double value)
{
  return std::isfinite(value);
}

double t_tolerance(double a, double b, const RootSearchOptions& options)
{
  return options.absolute_t_tolerance
         + options.relative_t_tolerance * std::max(std::abs(a), std::abs(b));
}

struct Evaluator {
  const ScalarFunction& function;
  const ScalarFunction& derivative;
  RootSearchDiagnostics& diagnostics;

  double f(double t)
  {
    ++diagnostics.function_evaluations;
    return function(t);
  }

  double df(double t)
  {
    ++diagnostics.derivative_evaluations;
    return derivative(t);
  }
};

std::optional<double> bisect_bracket(Evaluator& evaluator, bool derivative,
  double a, double b, double fa, double fb, const RootSearchOptions& options,
  double value_tolerance)
{
  if (!finite(fa) || !finite(fb)) {
    return std::nullopt;
  }
  if (std::abs(fa) <= value_tolerance) {
    return a;
  }
  if (std::abs(fb) <= value_tolerance) {
    return b;
  }
  if (std::signbit(fa) == std::signbit(fb)) {
    return std::nullopt;
  }

  for (int iteration = 0; iteration < options.max_bisection_iterations; ++iteration) {
    const double midpoint = a + 0.5 * (b - a);
    const double fm = derivative ? evaluator.df(midpoint) : evaluator.f(midpoint);
    if (!finite(fm)) {
      return std::nullopt;
    }
    if (std::abs(fm) <= value_tolerance
        || (b - a) <= t_tolerance(a, b, options)) {
      return midpoint;
    }
    if (std::signbit(fa) != std::signbit(fm)) {
      b = midpoint;
      fb = fm;
    } else {
      a = midpoint;
      fa = fm;
    }
  }
  return a + 0.5 * (b - a);
}

void add_candidate(std::vector<RootCandidate>& candidates, RootCandidate candidate,
  const RootSearchOptions& options, RootSearchDiagnostics& diagnostics)
{
  if (!finite(candidate.t) || !finite(candidate.residual)) {
    return;
  }
  const auto duplicate = std::find_if(candidates.begin(), candidates.end(),
    [&](const RootCandidate& existing) {
      const double tolerance = options.duplicate_t_multiplier
                               * t_tolerance(existing.t, candidate.t, options);
      return std::abs(existing.t - candidate.t) <= tolerance;
    });
  if (duplicate == candidates.end()) {
    candidates.push_back(candidate);
    return;
  }

  ++diagnostics.deduplicated_candidates;
  if (candidate.residual < duplicate->residual) {
    *duplicate = candidate;
  }
}

std::optional<RootCandidate> nearest_candidate(
  const std::vector<RootCandidate>& candidates, double t_min)
{
  std::optional<RootCandidate> nearest;
  for (const auto& candidate : candidates) {
    if (!(candidate.t >= t_min)) {
      continue;
    }
    if (!nearest || candidate.t < nearest->t) {
      nearest = candidate;
    }
  }
  return nearest;
}

} // namespace

RootSearchResult find_nearest_root_reference(const ScalarFunction& function,
  const ScalarFunction& derivative, double t_min, double t_max,
  const RootSearchOptions& options)
{
  if (!(t_max > t_min) || !finite(t_min) || !finite(t_max)) {
    throw std::invalid_argument("Root search requires a finite, increasing interval");
  }
  if (options.initial_subdivisions < 4 || options.max_refinement_levels < 1
      || options.max_bisection_iterations < 1) {
    throw std::invalid_argument("Root search iteration counts are invalid");
  }
  if (!(options.absolute_t_tolerance > 0.0)
      || !(options.relative_t_tolerance >= 0.0)
      || !(options.absolute_f_tolerance > 0.0)
      || !(options.derivative_tolerance > 0.0)) {
    throw std::invalid_argument("Root search tolerances are invalid");
  }

  RootSearchResult result;
  Evaluator evaluator {function, derivative, result.diagnostics};
  std::optional<RootCandidate> previous_nearest;

  for (int level = 0; level < options.max_refinement_levels; ++level) {
    result.diagnostics.refinement_levels = level + 1;
    const int subdivisions = options.initial_subdivisions << level;
    const double step = (t_max - t_min) / static_cast<double>(subdivisions);

    std::vector<double> f_values(static_cast<std::size_t>(subdivisions + 1));
    std::vector<double> df_values(static_cast<std::size_t>(subdivisions + 1));
    for (int i = 0; i <= subdivisions; ++i) {
      const double t = i == subdivisions ? t_max : t_min + step * static_cast<double>(i);
      f_values[static_cast<std::size_t>(i)] = evaluator.f(t);
      df_values[static_cast<std::size_t>(i)] = evaluator.df(t);
      if (finite(f_values[static_cast<std::size_t>(i)])
          && std::abs(f_values[static_cast<std::size_t>(i)])
               <= options.absolute_f_tolerance) {
        ++result.diagnostics.sampled_zero_candidates;
        add_candidate(result.candidates,
          RootCandidate {t, std::abs(f_values[static_cast<std::size_t>(i)]),
            RootKind::sampled_zero},
          options, result.diagnostics);
      }
    }

    for (int i = 0; i < subdivisions; ++i) {
      const std::size_t left = static_cast<std::size_t>(i);
      const std::size_t right = static_cast<std::size_t>(i + 1);
      const double a = t_min + step * static_cast<double>(i);
      const double b = i + 1 == subdivisions ? t_max : a + step;
      const double fa = f_values[left];
      const double fb = f_values[right];

      if (finite(fa) && finite(fb) && std::signbit(fa) != std::signbit(fb)) {
        ++result.diagnostics.sign_change_brackets;
        const auto root = bisect_bracket(evaluator, false, a, b, fa, fb,
          options, options.absolute_f_tolerance);
        if (root) {
          const double residual = std::abs(evaluator.f(*root));
          add_candidate(result.candidates,
            RootCandidate {*root, residual, RootKind::sign_change},
            options, result.diagnostics);
        }
      }

      const double dfa = df_values[left];
      const double dfb = df_values[right];
      const bool derivative_bracket = finite(dfa) && finite(dfb)
                                      && (std::signbit(dfa) != std::signbit(dfb)
                                          || std::abs(dfa) <= options.derivative_tolerance
                                          || std::abs(dfb) <= options.derivative_tolerance);
      if (derivative_bracket) {
        ++result.diagnostics.stationary_brackets;
        std::optional<double> stationary;
        if (std::abs(dfa) <= options.derivative_tolerance) {
          stationary = a;
        } else if (std::abs(dfb) <= options.derivative_tolerance) {
          stationary = b;
        } else {
          stationary = bisect_bracket(evaluator, true, a, b, dfa, dfb,
            options, options.derivative_tolerance);
        }
        if (stationary) {
          const double stationary_value = evaluator.f(*stationary);
          const double residual = std::abs(stationary_value);
          // An even number of crossings can lie inside a scan interval whose
          // endpoint signs match. Splitting at an enclosed stationary point
          // converts that missed-root configuration into ordinary brackets.
          if (*stationary > a && finite(fa) && finite(stationary_value)
              && std::signbit(fa) != std::signbit(stationary_value)) {
            ++result.diagnostics.sign_change_brackets;
            const auto root = bisect_bracket(evaluator, false, a, *stationary,
              fa, stationary_value, options, options.absolute_f_tolerance);
            if (root) {
              add_candidate(result.candidates,
                RootCandidate {*root, std::abs(evaluator.f(*root)),
                  RootKind::sign_change},
                options, result.diagnostics);
            }
          }
          if (*stationary < b && finite(stationary_value) && finite(fb)
              && std::signbit(stationary_value) != std::signbit(fb)) {
            ++result.diagnostics.sign_change_brackets;
            const auto root = bisect_bracket(evaluator, false, *stationary, b,
              stationary_value, fb, options, options.absolute_f_tolerance);
            if (root) {
              add_candidate(result.candidates,
                RootCandidate {*root, std::abs(evaluator.f(*root)),
                  RootKind::sign_change},
                options, result.diagnostics);
            }
          }
          if (residual <= options.tangent_residual_multiplier
                            * options.absolute_f_tolerance) {
            add_candidate(result.candidates,
              RootCandidate {*stationary, residual, RootKind::stationary_tangent},
              options, result.diagnostics);
          }
        }
      }
    }

    std::sort(result.candidates.begin(), result.candidates.end(),
      [](const RootCandidate& lhs, const RootCandidate& rhs) { return lhs.t < rhs.t; });
    const auto nearest = nearest_candidate(result.candidates, t_min);
    if (!nearest) {
      previous_nearest.reset();
      continue;
    }

    if (!options.require_refinement_stability) {
      result.found = true;
      result.root = *nearest;
      return result;
    }

    if (previous_nearest) {
      const double tolerance = options.duplicate_t_multiplier
                               * t_tolerance(previous_nearest->t, nearest->t, options);
      if (std::abs(previous_nearest->t - nearest->t) <= tolerance) {
        result.found = true;
        result.root = *nearest;
        return result;
      }
    }
    previous_nearest = nearest;
  }

  const auto nearest = nearest_candidate(result.candidates, t_min);
  if (nearest && !options.require_refinement_stability) {
    result.found = true;
    result.root = *nearest;
  }
  return result;
}

} // namespace stellarcsg
