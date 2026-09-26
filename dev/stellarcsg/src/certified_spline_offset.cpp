#include "stellarcsg/certified_spline_offset.hpp"
#include "exact_dyadic.hpp"
#include "stellarcsg/compiled_swept_surface.hpp"

#include <algorithm>
#include <array>
#include <cfenv>
#include <cmath>
#include <limits>
#include <optional>
#include <queue>
#include <stdexcept>
#include <vector>

namespace stellarcsg {
namespace {
using Real = long double;
constexpr Real infinity = std::numeric_limits<Real>::infinity();
Real down(Real x)
{
  return std::nextafter(x, -infinity);
}
Real up(Real x)
{
  return std::nextafter(x, infinity);
}
struct I {
  Real lo, hi;
  I(Real x = 0) : lo(x), hi(x)
  {
    if (!std::isfinite(x))
      throw std::runtime_error("Nonfinite offset interval");
  }
  I(Real l, Real h) : lo(l), hi(h)
  {
    if (!std::isfinite(l) || !std::isfinite(h) || l > h)
      throw std::runtime_error("Invalid offset interval");
  }
};
I operator+(I a, I b)
{
  if (a.lo == 0 && a.hi == 0)
    return b;
  if (b.lo == 0 && b.hi == 0)
    return a;
  return {down(a.lo + b.lo), up(a.hi + b.hi)};
}
I operator-(I a, I b)
{
  if (b.lo == 0 && b.hi == 0)
    return a;
  if (a.lo == 0 && a.hi == 0)
    return {-b.hi, -b.lo};
  if (a.lo == a.hi && b.lo == b.hi && a.lo == b.lo)
    return I(0);
  return {down(a.lo - b.hi), up(a.hi - b.lo)};
}
I operator-(I a)
{
  return {-a.hi, -a.lo};
}
I operator*(I a, I b)
{
  if ((a.lo == 0 && a.hi == 0) || (b.lo == 0 && b.hi == 0))
    return I(0);
  const std::array<Real, 4> p {
    a.lo * b.lo, a.lo * b.hi, a.hi * b.lo, a.hi * b.hi};
  return {down(*std::min_element(p.begin(), p.end())),
    up(*std::max_element(p.begin(), p.end()))};
}
I operator/(I a, I b)
{
  if (b.lo <= 0 && b.hi >= 0)
    throw std::runtime_error("Offset interval division by zero");
  if (a.lo == 0 && a.hi == 0)
    return I(0);
  return a * I {down(1 / b.hi), up(1 / b.lo)};
}
I square(I x)
{
  if (x.lo == 0 && x.hi == 0)
    return I(0);
  const Real lo =
    x.lo <= 0 && x.hi >= 0 ? 0 : std::min(x.lo * x.lo, x.hi * x.hi);
  return {std::max(Real(0), down(lo)), up(std::max(x.lo * x.lo, x.hi * x.hi))};
}
I root(I x)
{
  if (x.lo == 0 && x.hi == 0)
    return I(0);
  if (x.hi < 0)
    throw std::runtime_error("Negative squared offset distance");
  return {std::max(Real(0), down(std::sqrt(std::max(Real(0), x.lo)))),
    up(std::sqrt(std::max(Real(0), x.hi)))};
}
using V = std::array<I, 3>;
V operator-(const V& a, const V& b)
{
  return {a[0] - b[0], a[1] - b[1], a[2] - b[2]};
}
I dot_i(const V& a, const V& b)
{
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
I length2(const V& a)
{
  return square(a[0]) + square(a[1]) + square(a[2]);
}
void finite_point(const Vec3& p)
{
  if (std::fegetround() != FE_TONEAREST)
    throw std::runtime_error(
      "Offset query requires round-to-nearest arithmetic");
  if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z) ||
      std::max({std::abs(p.x), std::abs(p.y), std::abs(p.z)}) > 1e100)
    throw std::invalid_argument(
      "Offset query coordinates must be finite and at most 1e100");
}
struct Span {
  std::array<std::array<I, 4>, 3> c;
  std::array<std::array<double, 4>, 3> nominal;
  // Original four-control convex hull, transformed by the positive metric.
  // This bounds the exact cardinal spline independently of power arithmetic.
  V scaled_hull;
};
V sample(const Span& s, I u, int derivative = 0)
{
  V result;
  for (int a = 0; a < 3; ++a) {
    const auto& c = s.c[a];
    if (derivative == 0) {
      result[a] = ((c[3] * u + c[2]) * u + c[1]) * u + c[0];
      if (u.lo < u.hi) {
        const I slope = (I(3) * c[3] * u + I(2) * c[2]) * u + c[1];
        if (slope.lo >= 0 || slope.hi <= 0) {
          const I l =
            ((c[3] * I(u.lo) + c[2]) * I(u.lo) + c[1]) * I(u.lo) + c[0];
          const I r =
            ((c[3] * I(u.hi) + c[2]) * I(u.hi) + c[1]) * I(u.hi) + c[0];
          result[a] = I(std::max(result[a].lo, std::min(l.lo, r.lo)),
            std::min(result[a].hi, std::max(l.hi, r.hi)));
        }
      }
    } else if (derivative == 1)
      result[a] = (I(3) * c[3] * u + I(2) * c[2]) * u + c[1];
    else
      result[a] = I(6) * c[3] * u + I(2) * c[2];
  }
  return result;
}
struct Tile {
  std::size_t span;
  Real left, right, lower;
  unsigned depth;
};
struct NearFirst {
  bool operator()(const Tile& a, const Tile& b) const
  {
    return a.lower > b.lower;
  }
};
struct Minimum {
  I squared;
  std::size_t span {0};
  Real u {0};
  bool complete {false};
  std::vector<Tile> possible;
};
} // namespace

struct CertifiedSplineOffset::Implementation {
  using Exact = offset_detail::ExactDyadic;
  struct SupportContact {
    Exact six_other_coordinate;
  };
  struct Support {
    int axis;
    int orientation;
    Exact six_limit;
    std::vector<SupportContact> contacts;
  };
  std::vector<Span> spans;
  std::vector<Support> supports;
  std::array<I, 3> scale;
  BoundingBox box;
  double characteristic;
  double major_radius, minor_radius, plane_z;
  static constexpr std::size_t minimum_budget = 24000;
  static constexpr std::size_t ray_budget = 8192;
  static constexpr unsigned maximum_depth = 64;

  V scaled(const V& v) const
  {
    return {v[0] * scale[0], v[1] * scale[1], v[2] * scale[2]};
  }
  V point(const Vec3& p) const { return scaled({I(p.x), I(p.y), I(p.z)}); }
  V center(std::size_t s, I u, int derivative = 0) const
  {
    return scaled(sample(spans[s], u, derivative));
  }
  V ray_point(const Vec3& o, const Vec3& d, I t) const
  {
    return scaled(
      {I(o.x) + I(d.x) * t, I(o.y) + I(d.y) * t, I(o.z) + I(d.z) * t});
  }

  void compile_supports(const SweptSplineSurfaceData& data)
  {
    const auto n = data.sample_count;
    plane_z = data.centerline_coefficients[2];
    for (std::size_t j = 0; j < n; ++j)
      if (data.centerline_coefficients[3 * j + 2] != plane_z)
        return;
    const auto bezier = [&](std::size_t j, int axis, int orientation,
                          int control) {
      const std::array<std::size_t, 4> ids {
        (j + n - 1) % n, j, (j + 1) % n, (j + 2) % n};
      constexpr int weights[4][4] {
        {1, 4, 1, 0}, {0, 4, 2, 0}, {0, 2, 4, 0}, {0, 1, 4, 1}};
      Exact result;
      for (int k = 0; k < 4; ++k)
        result.add_double(data.centerline_coefficients[3 * ids[k] + axis],
          orientation * weights[control][k]);
      return result;
    };
    for (int axis = 0; axis < 2; ++axis)
      for (const int orientation : {-1, 1}) {
        Support candidate {
          axis, orientation, bezier(0, axis, orientation, 0), {}};
        bool valid = candidate.six_limit.valid();
        for (std::size_t j = 1; j < n && valid; ++j) {
          const auto seam = bezier(j, axis, orientation, 0);
          valid = seam.valid();
          if (valid && seam.compare(candidate.six_limit) > 0)
            candidate.six_limit = seam;
        }
        for (std::size_t j = 0; j < n && valid; ++j) {
          bool strict = false;
          for (int k = 0; k < 4; ++k) {
            const auto control = bezier(j, axis, orientation, k);
            if (!control.valid() || control.compare(candidate.six_limit) > 0) {
              valid = false;
              break;
            }
            strict = strict || control.compare(candidate.six_limit) < 0;
          }
          // All Bernstein weights are positive in a chart interior. At least
          // one strict coefficient proves strict interior support separation;
          // flat support charts deliberately reject this finite-contact proof.
          if (!strict)
            valid = false;
          const auto seam = bezier(j, axis, orientation, 0);
          if (valid && seam.compare(candidate.six_limit) == 0) {
            const auto other = bezier(j, 1 - axis, 1, 0);
            if (!other.valid())
              valid = false;
            else
              candidate.contacts.push_back({other});
          }
        }
        if (valid && !candidate.contacts.empty())
          supports.push_back(std::move(candidate));
      }
  }

  std::optional<DistanceResult> support_distance(const Vec3& o, const Vec3& d,
    bool coincident, Real minimum_t, const RootSearchOptions& options,
    RootSearchDiagnostics diagnostics) const
  {
    if (d.z != 0)
      return std::nullopt;
    const int ray_axis = d.x == 0 && std::abs(d.y) == 1
                           ? 1
                           : (d.y == 0 && std::abs(d.x) == 1 ? 0 : -1);
    if (ray_axis < 0)
      return std::nullopt;
    const std::array<double, 3> origin {o.x, o.y, o.z},
      direction {d.x, d.y, d.z};
    for (const auto& support : supports) {
      if (support.axis == ray_axis)
        continue;
      Exact cap_coordinate;
      cap_coordinate.add_double(origin[support.axis], 6 * support.orientation);
      const bool cap_plane = cap_coordinate.valid() &&
                             cap_coordinate.compare(support.six_limit) == 0;
      Exact z_positive, z_negative;
      z_positive.add_double(o.z);
      z_positive.add_double(plane_z, -1);
      z_positive.add_double(major_radius, -1);
      z_negative.add_double(o.z);
      z_negative.add_double(plane_z, -1);
      z_negative.add_double(major_radius);
      const bool cap = cap_plane && z_positive.valid() && z_negative.valid() &&
                       (z_positive.zero() || z_negative.zero());
      Exact edge_coordinate;
      edge_coordinate.add_double(origin[support.axis], 6 * support.orientation);
      edge_coordinate.add_double(minor_radius, -6);
      const bool edge = o.z == plane_z && edge_coordinate.valid() &&
                        edge_coordinate.compare(support.six_limit) == 0;
      if (!cap && !edge)
        continue;

      // Cap: Q>=z_distance^2/a^2=1. Edge: global support separation gives
      // Q>=support_distance^2/b^2=1. Equality requires a seam support contact
      // and equality of its other planar coordinate to the ray coordinate.
      // This finite exact contact list therefore proves every ray root,
      // including even contacts, without a sampled stationarity assumption.
      Exact threshold;
      threshold.add_double(static_cast<double>(minimum_t), 6);
      if (!threshold.valid())
        return std::nullopt;
      bool found = false;
      Exact earliest;
      for (const auto& contact : support.contacts) {
        Exact t = contact.six_other_coordinate;
        t.add_double(origin[ray_axis], -6);
        if (direction[ray_axis] < 0)
          t.negate();
        if (!t.valid())
          return std::nullopt;
        if (t.compare(threshold) < 0)
          continue;
        if (!found || t.compare(earliest) < 0) {
          earliest = t;
          found = true;
        }
      }
      if (!found) {
        ++diagnostics.certified_excluded_intervals;
        return DistanceResult {false, INFINITY, RootKind::stationary_tangent,
          INFINITY, diagnostics, false};
      }
      // Preserve the existing unsuppressed exact-origin-contact policy. A
      // strictly positive dyadic contact is never merged into t=0 by tolerance.
      if (!coincident && earliest.zero()) {
        diagnostics.unresolved_intervals = 1;
        return DistanceResult {false, INFINITY, RootKind::stationary_tangent,
          INFINITY, diagnostics, true};
      }
      Real lower, upper;
      if (!earliest.interval(lower, upper))
        return std::nullopt;
      const I enclosure = I(lower, upper) / I(6);
      const double t = static_cast<double>((enclosure.lo + enclosure.hi) / 2);
      if (!std::isfinite(t) || !(t > 0))
        return std::nullopt;
      const Real error = std::max(up(std::abs(Real(t) - enclosure.lo)),
        up(std::abs(enclosure.hi - Real(t))));
      // The contact normal is perpendicular to this ray. Its exact center
      // witnesses Q(t)-1=(A_ray*(t-t_contact))^2; global support gives F>=0.
      const I residual = square(I(error) * scale[ray_axis]);
      if (error > options.absolute_t_tolerance ||
          residual.hi > options.absolute_f_tolerance)
        return std::nullopt;
      double residual_bound = static_cast<double>(residual.hi);
      if (Real(residual_bound) < residual.hi)
        residual_bound = std::nextafter(residual_bound, INFINITY);
      ++diagnostics.stationary_brackets;
      return DistanceResult {true, t, RootKind::stationary_tangent,
        residual_bound, diagnostics, false};
    }
    return std::nullopt;
  }

  Minimum minimum(const V& p, Real tolerance, bool retain = false,
    RootSearchDiagnostics* diagnostics = nullptr) const
  {
    if (diagnostics)
      ++diagnostics->function_evaluations;
    Minimum answer;
    answer.squared = {0, std::numeric_limits<Real>::max() / 2};
    std::priority_queue<Tile, std::vector<Tile>, NearFirst> queue;
    auto witness = [&](std::size_t s, Real u) {
      const I q = length2(p - center(s, I(u)));
      if (q.hi < answer.squared.hi) {
        answer.squared.hi = q.hi;
        answer.span = s;
        answer.u = u;
      }
    };
    auto insert = [&](std::size_t s, Real l, Real r, unsigned depth) {
      if (length2(p - center(s, I(l, r))).lo > answer.squared.hi)
        return;
      witness(s, l);
      witness(s, (l + r) / 2);
      witness(s, r);
      // Every minimum of the exact periodic C2 curve is stationary, including
      // chart boundaries. A sign-definite h excludes a global minimizer here.
      for (unsigned iteration = 0; iteration < 8; ++iteration) {
        const I u(l, r);
        const V c = center(s, u), d = center(s, u, 1), dd = center(s, u, 2);
        const I h = dot_i(c - p, d);
        if (h.lo > 0 || h.hi < 0)
          return;
        const I slope = length2(d) + dot_i(c - p, dd);
        if (slope.lo <= 0 && slope.hi >= 0)
          break;
        const Real mid = (l + r) / 2;
        const I hm = dot_i(center(s, I(mid)) - p, center(s, I(mid), 1));
        const I next = I(mid) - hm / slope;
        const Real nl = std::max(l, next.lo), nr = std::min(r, next.hi);
        if (nl > nr)
          return;
        const Real old_width = r - l;
        l = nl;
        r = nr;
        if (r - l >= old_width * 0.99L)
          break;
      }
      witness(s, (l + r) / 2);
      const I u(l, r);
      const V c = center(s, u), d = center(s, u, 1), dd = center(s, u, 2);
      const I q = length2(p - c);
      const Real mid = (l + r) / 2;
      const I delta(down(l - mid), up(r - mid));
      const I qm = length2(p - center(s, I(mid)));
      const I hm = dot_i(center(s, I(mid)) - p, center(s, I(mid), 1));
      const I slope = length2(d) + dot_i(c - p, dd);
      const I taylor = qm + I(2) * hm * delta + slope * square(delta);
      const Real lower = std::max(q.lo, taylor.lo);
      if (lower <= answer.squared.hi)
        queue.push({s, l, r, lower, depth});
    };
    witness(0, 0);
    for (std::size_t s = 0; s < spans.size(); ++s) {
      // Nonnegative cardinal B-spline basis weights sum exactly to one.
      // Every center point belongs to the original control convex hull, so
      // strict distance separation safely eliminates this complete span.
      if (length2(p - spans[s].scaled_hull).lo > answer.squared.hi)
        continue;
      insert(s, 0, 1, 0);
    }
    std::size_t nodes = 0;
    while (!queue.empty() && nodes++ < minimum_budget) {
      if (diagnostics)
        ++diagnostics->subdivided_intervals;
      const Tile tile = queue.top();
      if (tile.lower > answer.squared.hi) {
        queue.pop();
        continue;
      }
      answer.squared.lo = tile.lower;
      if (answer.squared.hi - answer.squared.lo <= tolerance) {
        answer.complete = true;
        break;
      }
      queue.pop();
      const Real mid = (tile.left + tile.right) / 2;
      if (tile.depth == maximum_depth || mid == tile.left ||
          mid == tile.right) {
        queue.push(tile);
        break;
      }
      insert(tile.span, tile.left, mid, tile.depth + 1);
      insert(tile.span, mid, tile.right, tile.depth + 1);
    }
    if (queue.empty())
      throw std::runtime_error(
        "Offset stationary-minimum coverage unexpectedly empty");
    else
      answer.squared.lo = queue.top().lower;
    if (retain)
      while (!queue.empty()) {
        if (queue.top().lower <= answer.squared.hi)
          answer.possible.push_back(queue.top());
        queue.pop();
      }
    return answer;
  }

  // A narrow joined arc avoids requiring convexity at a distant corner merely
  // because it shares a neighboring full chart with a straight local minimum.
  bool projection_arc(const V& p, const Minimum& nearest, Real radius,
    V* offset, RootSearchDiagnostics* diagnostics, const V* ray_direction,
    I* ray_derivative) const
  {
    struct Arc {
      std::size_t span;
      I u;
    };
    const auto n = static_cast<long long>(spans.size());
    const Real coordinate = Real(nearest.span) + nearest.u;
    const Real left = coordinate - radius, right = coordinate + radius;
    std::vector<Arc> local;
    for (auto chart = static_cast<long long>(std::floor(left));
         chart <= static_cast<long long>(std::floor(right)); ++chart) {
      const auto s = static_cast<std::size_t>((chart % n + n) % n);
      local.push_back({s, I(std::max(Real(0), left - Real(chart)),
                            std::min(Real(1), right - Real(chart)))});
    }
    const I hl = dot_i(center(local.front().span, I(local.front().u.lo)) - p,
      center(local.front().span, I(local.front().u.lo), 1));
    const I hr = dot_i(center(local.back().span, I(local.back().u.hi)) - p,
      center(local.back().span, I(local.back().u.hi), 1));
    if (!(hl.hi < 0 && hr.lo > 0))
      return false;
    Real slope_lower = infinity, slope_upper = 0;
    std::size_t visits = 0;
    for (const auto& arc : local) {
      const auto s = arc.span;
      std::vector<std::pair<I, unsigned>> todo {{arc.u, 0}};
      while (!todo.empty()) {
        if (diagnostics)
          ++diagnostics->derivative_evaluations;
        if (++visits > 16000)
          return false;
        const auto item = todo.back();
        todo.pop_back();
        const V c = center(s, item.first), d = center(s, item.first, 1),
                dd = center(s, item.first, 2);
        const I slope = length2(d) + dot_i(c - p, dd);
        if (slope.lo > 0) {
          slope_lower = std::min(slope_lower, slope.lo);
          slope_upper = std::max(slope_upper, slope.hi);
          continue;
        }
        if (item.second >= 12)
          return false;
        const Real m = (item.first.lo + item.first.hi) / 2;
        todo.push_back({I(item.first.lo, m), item.second + 1});
        todo.push_back({I(m, item.first.hi), item.second + 1});
      }
    }
    for (std::size_t s = 0; s < spans.size(); ++s) {
      std::vector<std::pair<I, unsigned>> todo;
      const auto owned = std::find_if(local.begin(), local.end(),
        [&](const Arc& arc) { return arc.span == s; });
      if (owned == local.end())
        todo.push_back({I(0, 1), 0});
      else {
        // Every omitted tail of a partially owned chart is nonlocal and must
        // pass the same distance exclusion as a completely remote chart.
        if (owned->u.lo > 0)
          todo.push_back({I(0, owned->u.lo), 0});
        if (owned->u.hi < 1)
          todo.push_back({I(owned->u.hi, 1), 0});
      }
      while (!todo.empty()) {
        if (diagnostics)
          ++diagnostics->derivative_evaluations;
        if (++visits > 16000)
          return false;
        const auto item = todo.back();
        todo.pop_back();
        if (length2(p - center(s, item.first)).lo > nearest.squared.hi)
          continue;
        if (item.second >= 16)
          return false;
        const Real m = (item.first.lo + item.first.hi) / 2;
        todo.push_back({I(item.first.lo, m), item.second + 1});
        todo.push_back({I(m, item.first.hi), item.second + 1});
      }
    }
    if (offset || ray_derivative) {
      // Interval Newton uses the certified slope over the entire joined arc.
      // Retain every chart which can contain its unique stationary zero.
      bool first = true;
      bool first_derivative = true;
      for (const auto& arc : local) {
        const auto s = arc.span;
        I u = arc.u;
        bool excluded = false;
        for (unsigned iteration = 0; iteration < 64; ++iteration) {
          const I h = dot_i(center(s, u) - p, center(s, u, 1));
          if (h.lo > 0 || h.hi < 0) {
            excluded = true;
            break;
          }
          const Real mid = (u.lo + u.hi) / 2;
          const I hm = dot_i(center(s, I(mid)) - p, center(s, I(mid), 1));
          const I next = I(mid) - hm / I(slope_lower, slope_upper);
          const Real clipped_lo = std::max(u.lo, next.lo),
                     clipped_hi = std::min(u.hi, next.hi);
          if (clipped_lo > clipped_hi) {
            excluded = true;
            break;
          }
          const I clipped(clipped_lo, clipped_hi);
          const Real old_width = u.hi - u.lo;
          u = clipped;
          if (u.hi - u.lo >= old_width * 0.99L)
            break;
        }
        if (excluded)
          continue;
        const V candidate = p - center(s, u);
        if (offset) {
          if (first) {
            *offset = candidate;
          } else
            for (int a = 0; a < 3; ++a) {
              (*offset)[a].lo = std::min((*offset)[a].lo, candidate[a].lo);
              (*offset)[a].hi = std::max((*offset)[a].hi, candidate[a].hi);
            }
        }
        first = false;
        if (ray_derivative) {
          I bound = dot_i(candidate, *ray_direction);
          const V tangent = center(s, u, 1);
          int pivot = -1;
          Real margin = 0;
          for (int k = 0; k < 3; ++k) {
            const Real m = tangent[k].lo > 0
                             ? tangent[k].lo
                             : (tangent[k].hi < 0 ? -tangent[k].hi : 0);
            if (m > margin) {
              margin = m;
              pivot = k;
            }
          }
          if (pivot >= 0) {
            // At a stationary projection R.D=0. Eliminate the tangent-axis
            // offset to preserve dependence between ray point and owner.
            I reduced(0);
            for (int k = 0; k < 3; ++k)
              if (k != pivot)
                reduced =
                  reduced + candidate[k] * ((*ray_direction)[k] -
                                             (*ray_direction)[pivot] *
                                               tangent[k] / tangent[pivot]);
            const Real l = std::max(bound.lo, reduced.lo),
                       r = std::min(bound.hi, reduced.hi);
            if (l > r)
              continue;
            bound = {l, r};
          }
          if (first_derivative) {
            *ray_derivative = bound;
            first_derivative = false;
          } else
            *ray_derivative = I(std::min(ray_derivative->lo, bound.lo),
              std::max(ray_derivative->hi, bound.hi));
        }
      }
      if (first || (ray_derivative && first_derivative))
        return false;
    }
    return true;
  }
  bool projection(const V& p, const Minimum& nearest, V* offset = nullptr,
    RootSearchDiagnostics* diagnostics = nullptr,
    const V* ray_direction = nullptr, I* ray_derivative = nullptr) const
  {
    // Three deterministic arc sizes, with a combined 48,000 visit cap.
    // Exact C2 identities join partial charts across the periodic seam.
    for (const Real radius : {0.5L, 1.0L, 1.5L})
      if (projection_arc(p, nearest, radius, offset, diagnostics, ray_direction,
            ray_derivative))
        return true;
    return false;
  }
  // Floating values only propose a bracket or a curve witness. Neither a
  // sampled sign nor convergence of this Newton iteration admits a result.
  double proposal_value(const Vec3& o, const Vec3& d, Real t,
    std::size_t* witness_span = nullptr, double* witness_u = nullptr) const
  {
    std::array<double, 3> p;
    const std::array<double, 3> origin {o.x, o.y, o.z},
      direction {d.x, d.y, d.z};
    for (int a = 0; a < 3; ++a)
      p[a] = (origin[a] + double(t) * direction[a]) *
             double((scale[a].lo + scale[a].hi) / 2);
    double best = std::numeric_limits<double>::infinity();
    for (std::size_t s = 0; s < spans.size(); ++s) {
      const auto& c = spans[s].nominal;
      auto consider = [&](double u) {
        double q = 0;
        for (int a = 0; a < 3; ++a) {
          const double r =
            ((c[a][3] * u + c[a][2]) * u + c[a][1]) * u + c[a][0] - p[a];
          q += r * r;
        }
        if (q < best) {
          best = q;
          if (witness_span)
            *witness_span = s;
          if (witness_u)
            *witness_u = u;
        }
      };
      consider(0);
      consider(1);
      double u = .5;
      for (int step = 0; step < 6; ++step) {
        double h = 0, slope = 0;
        for (int a = 0; a < 3; ++a) {
          const double r =
            ((c[a][3] * u + c[a][2]) * u + c[a][1]) * u + c[a][0] - p[a];
          const double first = (3 * c[a][3] * u + 2 * c[a][2]) * u + c[a][1];
          const double second = 6 * c[a][3] * u + 2 * c[a][2];
          h += r * first;
          slope += first * first + r * second;
        }
        if (!(slope > 0))
          break;
        const double next = std::clamp(u - h / slope, 0., 1.);
        if (!std::isfinite(next) || next == u)
          break;
        u = next;
      }
      consider(u);
    }
    return best - 1;
  }

  using Tensor = std::array<I, 21>;
  Tensor squared_bernstein(
    std::size_t s, const Vec3& o, const Vec3& d, Real left, Real right) const
  {
    Tensor power {}, bernstein {};
    const std::array<double, 3> origin {o.x, o.y, o.z},
      direction {d.x, d.y, d.z};
    for (int a = 0; a < 3; ++a) {
      std::array<I, 4> r;
      r[0] = (I(origin[a]) + I(direction[a]) * I(left) - spans[s].c[a][0]) *
             scale[a];
      for (int k = 1; k < 4; ++k)
        r[k] = -spans[s].c[a][k] * scale[a];
      const I velocity = I(direction[a]) * scale[a] * (I(right) - I(left));
      for (int k = 0; k < 4; ++k) {
        for (int l = 0; l < 4; ++l)
          power[3 * (k + l)] = power[3 * (k + l)] + r[k] * r[l];
        power[3 * k + 1] = power[3 * k + 1] + I(2) * r[k] * velocity;
      }
      power[2] = power[2] + square(velocity);
    }
    constexpr int choose[7][7] {{1}, {1, 1}, {1, 2, 1}, {1, 3, 3, 1},
      {1, 4, 6, 4, 1}, {1, 5, 10, 10, 5, 1}, {1, 6, 15, 20, 15, 6, 1}};
    for (int i = 0; i < 7; ++i)
      for (int j = 0; j < 3; ++j)
        for (int k = 0; k <= i; ++k)
          for (int l = 0; l <= j; ++l)
            bernstein[3 * i + j] =
              bernstein[3 * i + j] + power[3 * k + l] *
                                       (I(choose[i][k]) / I(choose[6][k])) *
                                       (I(choose[j][l]) / I(choose[2][l]));
    return bernstein;
  }
  std::pair<Tensor, Tensor> split_tensor(
    const Tensor& coefficients, bool split_u) const
  {
    Tensor left {}, right {};
    const int degree = split_u ? 6 : 2, rows = split_u ? 3 : 7;
    for (int row = 0; row < rows; ++row) {
      std::array<I, 7> work;
      auto index = [&](int k) { return split_u ? 3 * k + row : 3 * row + k; };
      for (int k = 0; k <= degree; ++k)
        work[k] = coefficients[index(k)];
      left[index(0)] = work[0];
      right[index(degree)] = work[degree];
      for (int level = 1; level <= degree; ++level) {
        for (int k = 0; k <= degree - level; ++k)
          work[k] = (work[k] + work[k + 1]) * I(.5);
        left[index(level)] = work[0];
        right[index(degree - level)] = work[degree - level];
      }
    }
    return {left, right};
  }
  bool outside_prefix(const Vec3& o, const Vec3& d, Real left, Real right,
    std::size_t budget, RootSearchDiagnostics& diagnostics) const
  {
    if (right == left)
      return true;
    if (!(right > left))
      return false;
    const V p = ray_point(o, d, I(left, right));
    struct Box {
      Tensor q;
      unsigned depth;
    };
    std::size_t visits = 0;
    for (std::size_t s = 0; s < spans.size(); ++s) {
      if (length2(p - spans[s].scaled_hull).lo > 1)
        continue;
      std::vector<Box> todo {{squared_bernstein(s, o, d, left, right), 0}};
      while (!todo.empty()) {
        if (++visits > budget)
          return false;
        ++diagnostics.subdivided_intervals;
        const auto box = todo.back();
        todo.pop_back();
        bool excluded = true;
        for (const auto q : box.q)
          excluded = excluded && q.lo > 1;
        if (excluded)
          continue;
        // Corners are actual values; a proved nonoutside prefix sample blocks
        // this proposal. Other uncertain controls only trigger subdivision.
        for (const int corner : {0, 2, 18, 20})
          if (box.q[corner].hi <= 1)
            return false;
        if (box.depth >= 48)
          return false;
        const auto children = split_tensor(box.q, box.depth % 2 == 0);
        todo.push_back({children.second, box.depth + 1});
        todo.push_back({children.first, box.depth + 1});
      }
    }
    ++diagnostics.certified_excluded_intervals;
    return true;
  }
  bool inside_prefix(const Vec3& o, const Vec3& d, Real left, Real right,
    std::size_t budget, RootSearchDiagnostics& diagnostics) const
  {
    if (right == left)
      return true;
    if (!(right > left))
      return false;
    struct Slab {
      Real l, r;
      unsigned depth;
    };
    std::vector<Slab> todo {{left, right, 0}};
    std::size_t visits = 0;
    while (!todo.empty()) {
      if (++visits > budget)
        return false;
      const auto slab = todo.back();
      todo.pop_back();
      const Real mid = (slab.l + slab.r) / 2;
      std::size_t s = 0;
      double u = 0;
      if (!std::isfinite(proposal_value(o, d, mid, &s, &u)))
        return false;
      const V c = center(s, I(u));
      // For this fixed exact curve point, squared metric distance along the
      // ray is convex quadratic. Its endpoint upper bounds cover the slab.
      if (length2(ray_point(o, d, I(slab.l)) - c).hi < 1 &&
          length2(ray_point(o, d, I(slab.r)) - c).hi < 1) {
        ++diagnostics.certified_excluded_intervals;
        continue;
      }
      if (slab.depth >= 48 || mid == slab.l || mid == slab.r)
        return false;
      todo.push_back({mid, slab.r, slab.depth + 1});
      todo.push_back({slab.l, mid, slab.depth + 1});
    }
    return true;
  }
  std::optional<DistanceResult> accelerated_distance(const Vec3& o,
    const Vec3& d, Real enter, Real exit, int initial, std::size_t budget,
    const RootSearchOptions& options, RootSearchDiagnostics& diagnostics) const
  {
    Real left = enter, right = enter;
    bool proposed = false;
    for (int i = 1; i <= 128; ++i) {
      const Real sample_t = enter + (exit - enter) * Real(i) / 128;
      const double value = proposal_value(o, d, sample_t);
      if (!std::isfinite(value))
        return std::nullopt;
      if (initial > 0 ? value < 0 : value > 0) {
        right = sample_t;
        proposed = true;
        break;
      }
      left = sample_t;
    }
    if (!proposed)
      return std::nullopt;
    for (int i = 0; i < 64 && right - left > 1e-8L; ++i) {
      const Real mid = (left + right) / 2;
      const double value = proposal_value(o, d, mid);
      if (!std::isfinite(value))
        return std::nullopt;
      if (initial > 0 ? value > 0 : value < 0)
        left = mid;
      else
        right = mid;
    }
    auto signed_bounds = [&](Real t) {
      return root(minimum(ray_point(o, d, I(t)), 1e-16L, false, &diagnostics)
                    .squared) -
             I(1);
    };
    const I gl = signed_bounds(left), gr = signed_bounds(right);
    if (!(initial > 0 ? (gl.lo > 0 && gr.hi < 0) : (gl.hi < 0 && gr.lo > 0)))
      return std::nullopt;
    const V p = ray_point(o, d, I(left, right)),
            w = scaled({I(d.x), I(d.y), I(d.z)});
    auto nearest = minimum(
      ray_point(o, d, I((left + right) / 2)), 1e-12L, false, &diagnostics);
    nearest.squared = {0, length2(p - center(nearest.span, I(nearest.u))).hi};
    I derivative;
    if (!projection(p, nearest, nullptr, &diagnostics, &w, &derivative) ||
        !(initial > 0 ? derivative.hi < 0 : derivative.lo > 0))
      return std::nullopt;
    if (!(initial > 0 ? outside_prefix(o, d, enter, left, budget, diagnostics)
                      : inside_prefix(o, d, enter, left, budget, diagnostics)))
      return std::nullopt;
    for (int i = 0; i < std::min(options.max_bisection_iterations, 1024) &&
                    right - left > options.absolute_t_tolerance / 2;
         ++i) {
      const Real mid = (left + right) / 2;
      const I g = signed_bounds(mid);
      const int sign = g.lo > 0 ? 1 : (g.hi < 0 ? -1 : 0);
      if (sign == initial)
        left = mid;
      else if (sign == -initial)
        right = mid;
      else {
        const Real slope = down((initial > 0 ? -derivative.hi : derivative.lo) /
                                root(nearest.squared).hi);
        if (!(slope > 0))
          return std::nullopt;
        const Real radius =
          up(std::max(std::abs(g.lo), std::abs(g.hi)) / slope);
        left = std::max(left, down(mid - radius));
        right = std::min(right, up(mid + radius));
      }
    }
    const double t = static_cast<double>((left + right) / 2);
    const Real error =
      std::max(up(std::abs(Real(t) - left)), up(std::abs(right - Real(t))));
    const I residual =
      minimum(ray_point(o, d, I(t)), 1e-14L, false, &diagnostics).squared -
      I(1);
    const Real bound = std::max(std::abs(residual.lo), std::abs(residual.hi));
    if (!(error <= options.absolute_t_tolerance &&
          bound <= options.absolute_f_tolerance))
      return std::nullopt;
    ++diagnostics.sign_change_brackets;
    diagnostics.refinement_levels =
      1; // Certified Bernstein prefix acceleration.
    double residual_bound = static_cast<double>(bound);
    if (Real(residual_bound) < bound)
      residual_bound = std::nextafter(residual_bound, INFINITY);
    return DistanceResult {
      true, t, RootKind::sign_change, residual_bound, diagnostics, false};
  }
};

CertifiedSplineOffset::CertifiedSplineOffset(const SweptSplineSurfaceData& data)
  : implementation_(std::make_unique<Implementation>())
{
  if (std::fegetround() != FE_TONEAREST ||
      std::numeric_limits<Real>::radix != 2 ||
      !std::numeric_limits<Real>::is_iec559 ||
      std::numeric_limits<Real>::digits < 64 ||
      std::numeric_limits<Real>::max_exponent < 16384)
    throw std::invalid_argument(
      "Offset certificate requires IEEE binary round-to-nearest arithmetic");
  const auto n = data.sample_count;
  if (n < 4 || n > 4096 || data.centerline_coefficients.size() != 3 * n ||
      data.normal_coefficients.size() != 3 * n ||
      data.major_radius_coefficients.size() != n ||
      data.binormal_coefficients.size() != 3 * n ||
      data.minor_radius_coefficients.size() != n ||
      !(data.characteristic_length > 0) ||
      !std::isfinite(data.characteristic_length) ||
      data.characteristic_length > 1e100)
    throw std::invalid_argument(
      "Invalid exact-control offset coefficient dimensions");
  for (const auto* values : {&data.centerline_coefficients,
         &data.normal_coefficients, &data.binormal_coefficients,
         &data.major_radius_coefficients, &data.minor_radius_coefficients})
    for (const auto x : *values)
      if (!std::isfinite(x) || std::abs(x) > 1e100)
        throw std::invalid_argument("Nonfinite offset coefficient");
  const double a = data.major_radius_coefficients[0],
               b = data.minor_radius_coefficients[0];
  if (!(a >= 1e-100 && b >= 1e-100))
    throw std::invalid_argument("Offset radii must be at least 1e-100");
  for (std::size_t j = 0; j < n; ++j)
    if (data.major_radius_coefficients[j] != a ||
        data.minor_radius_coefficients[j] != b)
      throw std::invalid_argument(
        "Offset representation requires constant radii");
  if (a != b)
    for (std::size_t j = 0; j < n; ++j)
      if (data.centerline_coefficients[3 * j + 2] !=
            data.centerline_coefficients[2] ||
          data.normal_coefficients[3 * j] != 0 ||
          data.normal_coefficients[3 * j + 1] != 0 ||
          data.normal_coefficients[3 * j + 2] == 0 ||
          std::signbit(data.normal_coefficients[3 * j + 2]) !=
            std::signbit(data.normal_coefficients[2]))
        throw std::invalid_argument("Elliptic offset requires xy-planar curve "
                                    "and nonvanishing axial normal");
  auto& impl = *implementation_;
  impl.scale = {I(1) / I(b), I(1) / I(b), I(1) / I(a)};
  impl.major_radius = a;
  impl.minor_radius = b;
  impl.characteristic = data.characteristic_length;
  const double double_infinity = std::numeric_limits<double>::infinity();
  impl.box.lower = {double_infinity, double_infinity, double_infinity};
  impl.box.upper = {-double_infinity, -double_infinity, -double_infinity};
  std::size_t regularity_visits = 0;
  for (std::size_t j = 0; j < n; ++j) {
    Span span;
    for (int axis = 0; axis < 3; ++axis) {
      const I p0(data.centerline_coefficients[3 * ((j + n - 1) % n) + axis]);
      const I p1(data.centerline_coefficients[3 * j + axis]);
      const I p2(data.centerline_coefficients[3 * ((j + 1) % n) + axis]);
      const I p3(data.centerline_coefficients[3 * ((j + 2) % n) + axis]);
      span.c[axis] = {(p0 + I(4) * p1 + p2) / I(6), (-p0 + p2) / I(2),
        (p0 - I(2) * p1 + p2) / I(2),
        (-p0 + I(3) * p1 - I(3) * p2 + p3) / I(6)};
      span.scaled_hull[axis] = I(std::min({p0.lo, p1.lo, p2.lo, p3.lo}),
                                 std::max({p0.hi, p1.hi, p2.hi, p3.hi})) *
                               impl.scale[axis];
    }
    for (int axis = 0; axis < 3; ++axis)
      for (int k = 0; k < 4; ++k)
        span.nominal[axis][k] = static_cast<double>(
          (span.c[axis][k].lo + span.c[axis][k].hi) / 2 *
          ((impl.scale[axis].lo + impl.scale[axis].hi) / 2));
    impl.spans.push_back(span);
    std::vector<std::pair<I, unsigned>> todo {{I(0, 1), 0}};
    while (!todo.empty()) {
      if (++regularity_visits > 65536)
        throw std::invalid_argument(
          "Offset regularity admission budget exhausted");
      const auto item = todo.back();
      todo.pop_back();
      if (length2(sample(span, item.first, 1)).lo > 0)
        continue;
      if (item.second >= 16)
        throw std::invalid_argument(
          "Could not certify whole-span nonzero offset tangent");
      const Real m = (item.first.lo + item.first.hi) / 2;
      todo.push_back({I(item.first.lo, m), item.second + 1});
      todo.push_back({I(m, item.first.hi), item.second + 1});
    }
  }
  for (std::size_t j = 0; j < n; ++j) {
    const Vec3 c {data.centerline_coefficients[3 * j],
      data.centerline_coefficients[3 * j + 1],
      data.centerline_coefficients[3 * j + 2]};
    impl.box.lower.x = std::min(impl.box.lower.x, c.x);
    impl.box.upper.x = std::max(impl.box.upper.x, c.x);
    impl.box.lower.y = std::min(impl.box.lower.y, c.y);
    impl.box.upper.y = std::max(impl.box.upper.y, c.y);
    impl.box.lower.z = std::min(impl.box.lower.z, c.z);
    impl.box.upper.z = std::max(impl.box.upper.z, c.z);
  }
  impl.box.lower = {std::nextafter(impl.box.lower.x - b, -INFINITY),
    std::nextafter(impl.box.lower.y - b, -INFINITY),
    std::nextafter(impl.box.lower.z - a, -INFINITY)};
  impl.box.upper = {std::nextafter(impl.box.upper.x + b, INFINITY),
    std::nextafter(impl.box.upper.y + b, INFINITY),
    std::nextafter(impl.box.upper.z + a, INFINITY)};
  impl.compile_supports(data);
}
CertifiedSplineOffset::~CertifiedSplineOffset() = default;
const BoundingBox& CertifiedSplineOffset::bounding_box() const noexcept
{
  return implementation_->box;
}
OffsetSquaredDistanceEnclosure
CertifiedSplineOffset::squared_distance_enclosure(const Vec3& point) const
{
  finite_point(point);
  const auto result =
    implementation_->minimum(implementation_->point(point), 1e-13L);
  return {result.squared.lo, result.squared.hi, result.complete};
}

double CertifiedSplineOffset::evaluate(const Vec3& point) const
{
  finite_point(point);
  const auto result =
    implementation_->minimum(implementation_->point(point), 1e-13L);
  // This explicit numerical boundary band is narrower than OpenMC's existing
  // FP_COINCIDENT=1e-12. A proved normal lets Surface::sense choose direction.
  if (result.complete && result.squared.lo >= 1 - 1e-13L &&
      result.squared.hi <= 1 + 1e-13L) {
    (void)normal(point);
    return 0.0;
  }
  if (result.squared.lo <= 1 && result.squared.hi >= 1)
    throw std::runtime_error(
      "Exact-control offset classification is boundary/ambiguous");
  const Real value = (result.squared.lo + result.squared.hi) / 2 - 1;
  const Real finite_limit = std::numeric_limits<double>::max();
  return static_cast<double>(std::clamp(value, -finite_limit, finite_limit));
}
Vec3 CertifiedSplineOffset::normal(const Vec3& point) const
{
  finite_point(point);
  const auto& impl = *implementation_;
  const V p = impl.point(point);
  const auto result = impl.minimum(p, 1e-12L);
  V offset;
  if (!result.complete)
    throw std::runtime_error(
      "Exact-control offset normal minimum budget exhausted");
  if (!impl.projection(p, result, &offset))
    throw std::runtime_error(
      "Exact-control offset normal has no certified unique projection");
  const V physical_gradient {offset[0] * impl.scale[0],
    offset[1] * impl.scale[1], offset[2] * impl.scale[2]};
  const I magnitude = root(length2(physical_gradient));
  if (!(magnitude.lo > 0))
    throw std::runtime_error("Offset normal has no positive norm lower bound");
  std::array<double, 3> v;
  for (int axis = 0; axis < 3; ++axis) {
    const I component = physical_gradient[axis] / magnitude;
    if (component.hi - component.lo > 1e-8L)
      throw std::runtime_error(
        "Exact-control offset normal enclosure is too wide");
    v[axis] = static_cast<double>((component.lo + component.hi) / 2);
  }
  // The returned vector approximates a unit normal componentwise within the
  // declared enclosure width. Renormalizing its midpoint would lose that
  // explicit component enclosure and is deliberately avoided.
  return {v[0], v[1], v[2]};
}

DistanceResult CertifiedSplineOffset::distance(const Vec3& origin,
  const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  finite_point(origin);
  finite_point(direction);
  const double direction_scale = std::max(
    {std::abs(direction.x), std::abs(direction.y), std::abs(direction.z)});
  if (!(direction_scale > 0))
    throw std::invalid_argument("Offset ray direction must be nonzero");
  const Vec3 reduced {direction.x / direction_scale,
    direction.y / direction_scale, direction.z / direction_scale};
  const double reduced_norm = std::hypot(reduced.x, reduced.y, reduced.z);
  const Vec3 d {reduced.x / reduced_norm, reduced.y / reduced_norm,
    reduced.z / reduced_norm};
  const auto& impl = *implementation_;
  RootSearchDiagnostics diagnostics;
  diagnostics.solver_path = SolverPath::general_swept_certified;
  diagnostics.fallback_reason = SolverFallbackReason::none;
  auto unresolved = [&]() {
    diagnostics.unresolved_intervals = 1;
    return DistanceResult {
      false, INFINITY, RootKind::sign_change, INFINITY, diagnostics, true};
  };
  if (!(options.absolute_t_tolerance > 0 && options.absolute_f_tolerance > 0) ||
      !std::isfinite(options.absolute_t_tolerance) ||
      !std::isfinite(options.absolute_f_tolerance) ||
      options.absolute_t_tolerance > 1e100 ||
      options.absolute_f_tolerance > 1e100)
    return unresolved();
  if (options.initial_subdivisions <= 0 || options.max_refinement_levels < 0 ||
      options.max_bisection_iterations <= 0)
    return unresolved();
  const std::size_t budget = std::min(Implementation::ray_budget,
    std::size_t(options.initial_subdivisions) *
      (std::size_t(options.max_refinement_levels) + 1));
  const Real minimum_t =
    coincident
      ? std::max({64 * options.absolute_t_tolerance,
          8 * options.absolute_f_tolerance * impl.characteristic,
          64 * std::numeric_limits<double>::epsilon() * impl.characteristic})
      : 0;
  if (const auto support = impl.support_distance(
        origin, d, coincident, minimum_t, options, diagnostics))
    return *support;
  Real enter = minimum_t, exit = infinity;
  const std::array<double, 3> o {origin.x, origin.y, origin.z},
    v {d.x, d.y, d.z};
  const std::array<double, 3> lo {
    impl.box.lower.x, impl.box.lower.y, impl.box.lower.z};
  const std::array<double, 3> hi {
    impl.box.upper.x, impl.box.upper.y, impl.box.upper.z};
  for (int axis = 0; axis < 3; ++axis) {
    if (v[axis] == 0) {
      if (o[axis] < lo[axis] || o[axis] > hi[axis])
        return {};
      continue;
    }
    const I l = (I(lo[axis]) - I(o[axis])) / I(v[axis]);
    const I r = (I(hi[axis]) - I(o[axis])) / I(v[axis]);
    enter = std::max(enter, std::min(l.lo, r.lo));
    exit = std::min(exit, std::max(l.hi, r.hi));
  }
  if (exit < enter)
    return {};
  if (exit == enter)
    return unresolved();
  if (!std::isfinite(exit))
    return unresolved();
  const I lipschitz = root(length2(impl.scaled({I(d.x), I(d.y), I(d.z)})));
  auto signed_bounds = [&](Real t, Real tolerance) {
    const auto nearest = impl.minimum(
      impl.ray_point(origin, d, I(t)), tolerance, false, &diagnostics);
    return root(nearest.squared) - I(1);
  };
  const I start = signed_bounds(enter, 1e-14L);
  const int initial = start.lo > 0 ? 1 : (start.hi < 0 ? -1 : 0);
  if (!initial)
    return unresolved();
  if (options.enable_bernstein_prefix) {
    if (const auto accelerated = impl.accelerated_distance(
          origin, d, enter, exit, initial, budget, options, diagnostics))
      return *accelerated;
  }
  struct Slab {
    Real l, r;
    unsigned depth;
  };
  std::vector<Slab> todo {{enter, exit, 0}};
  std::size_t nodes = 0;
  while (!todo.empty() && nodes++ < budget) {
    const auto slab = todo.back();
    todo.pop_back();
    const Real mid = (slab.l + slab.r) / 2;
    const Real rad = std::max(up(mid - slab.l), up(slab.r - mid));
    const I g = signed_bounds(
      mid, std::max(1e-15L, std::min(1e-10L, (slab.r - slab.l) * 1e-4L)));
    const Real spread = up(lipschitz.hi * rad);
    const I cover = g + I(-spread, spread);
    if ((initial > 0 && cover.lo > 0) || (initial < 0 && cover.hi < 0)) {
      ++diagnostics.certified_excluded_intervals;
      continue;
    }
    const I gl = signed_bounds(slab.l, 1e-15L),
            gr = signed_bounds(slab.r, 1e-15L);
    const bool bracket =
      initial > 0 ? (gl.lo > 0 && gr.hi < 0) : (gl.hi < 0 && gr.lo > 0);
    const bool same_sign =
      initial > 0 ? (gl.lo > 0 && gr.lo > 0) : (gl.hi < 0 && gr.hi < 0);
    if ((bracket || same_sign) &&
        slab.r - slab.l < 0.1L * impl.characteristic) {
      const V p = impl.ray_point(origin, d, I(slab.l, slab.r));
      auto nearest = impl.minimum(
        impl.ray_point(origin, d, I(mid)), 1e-12L, false, &diagnostics);
      // A fixed center witness bounds the minimum uniformly over the ray box.
      // Minimizing a spatial box itself needlessly asks an inherently wide
      // interval to converge to point precision and can exhaust the budget.
      nearest.squared = {
        0, length2(p - impl.center(nearest.span, I(nearest.u))).hi};
      V offset;
      const V metric_direction = impl.scaled({I(d.x), I(d.y), I(d.z)});
      I derivative;
      if (impl.projection(p, nearest, &offset, &diagnostics, &metric_direction,
            &derivative)) {
        if (same_sign && (derivative.lo > 0 || derivative.hi < 0)) {
          ++diagnostics.certified_excluded_intervals;
          continue;
        }
        if (initial > 0 ? derivative.hi < 0 : derivative.lo > 0) {
          // The whole bracket has a unique projection and a strict derivative.
          // Its left prefix can now be excluded by monotonicity; unlike the
          // Lipschitz cover this does not subdivide indefinitely near a root.
          Real left = slab.l, right = slab.r;
          for (int iteration = 0;
               iteration < std::min(options.max_bisection_iterations, 1024) &&
               right - left > options.absolute_t_tolerance / 2;
               ++iteration) {
            const Real middle = (left + right) / 2;
            const I gm = signed_bounds(middle, 1e-16L);
            const int sign = gm.lo > 0 ? 1 : (gm.hi < 0 ? -1 : 0);
            if (sign == initial)
              left = middle;
            else if (sign == -initial)
              right = middle;
            else {
              const Real derivative_lower =
                initial > 0 ? -derivative.hi : derivative.lo;
              // g'=F'/(2*sqrt(Q)); use a safe upper distance denominator.
              const Real g_slope =
                down(derivative_lower / root(nearest.squared).hi);
              if (!(g_slope > 0))
                return unresolved();
              const Real error_radius =
                up(std::max(std::abs(gm.lo), std::abs(gm.hi)) / g_slope);
              left = std::max(left, down(middle - error_radius));
              right = std::min(right, up(middle + error_radius));
            }
          }
          const double t = static_cast<double>((left + right) / 2);
          const Real error = std::max(
            up(std::abs(Real(t) - left)), up(std::abs(right - Real(t))));
          const I residual = impl
                               .minimum(impl.ray_point(origin, d, I(t)), 1e-14L,
                                 false, &diagnostics)
                               .squared -
                             I(1);
          const Real bound =
            std::max(std::abs(residual.lo), std::abs(residual.hi));
          if (!(error <= options.absolute_t_tolerance &&
                bound <= options.absolute_f_tolerance))
            return unresolved();
          ++diagnostics.sign_change_brackets;
          double residual_bound = static_cast<double>(bound);
          if (Real(residual_bound) < bound)
            residual_bound = std::nextafter(residual_bound, INFINITY);
          return {
            true, t, RootKind::sign_change, residual_bound, diagnostics, false};
        }
      }
    }
    if (slab.depth >= Implementation::maximum_depth || mid == slab.l ||
        mid == slab.r)
      return unresolved();
    todo.push_back({mid, slab.r, slab.depth + 1});
    todo.push_back({slab.l, mid, slab.depth + 1});
  }
  if (!todo.empty())
    return unresolved();
  return {false, INFINITY, RootKind::sign_change, INFINITY, diagnostics, false};
}
} // namespace stellarcsg
