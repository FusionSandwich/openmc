#pragma once

// One-way exclusions for the exact circular tube. This header is included only
// by compiled_swept_surface.cpp, compiled with strict binary64 FP flags.
#include <algorithm>
#include <array>
#include <cfenv>
#include <cfloat>
#include <cmath>
#include <cstddef>
#include <limits>
#include <numeric>
#include <vector>
#if defined(__SSE__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

namespace stellarcsg::circular_filter {

constexpr double inf = std::numeric_limits<double>::infinity();
struct Interval {
  double lo {0.0};
  double hi {0.0};
  bool valid() const { return std::isfinite(lo) && std::isfinite(hi) && lo <= hi; }
  bool zero() const { return lo == 0.0 && hi == 0.0; }
};
inline Interval unknown() { return {-inf, inf}; }
inline bool supported_environment()
{
#if !defined(STELLARCSG_FILTER_STRICT_FP) || defined(__FAST_MATH__) \
  || defined(_M_FP_FAST) || FLT_EVAL_METHOD != 0
  return false;
#elif defined(__SSE__) || defined(_M_X64)
  // MXCSR belongs to the calling thread; never cache this test globally.
  return std::numeric_limits<double>::is_iec559
    && std::fegetround() == FE_TONEAREST && (_mm_getcsr() & 0xE040U) == 0;
#else
  // Other FP environments need their own reviewed gradual-underflow check.
  return false;
#endif
}
inline Interval add(Interval a, Interval b)
{
  if (!a.valid() || !b.valid()) return unknown();
  if (a.zero()) return b;
  if (b.zero()) return a;
  const double lo = a.lo + b.lo, hi = a.hi + b.hi;
  if (!std::isfinite(lo) || !std::isfinite(hi)) return unknown();
  return {std::nextafter(lo, -inf), std::nextafter(hi, inf)};
}
inline Interval sub(Interval a, Interval b) { return add(a, {-b.hi, -b.lo}); }
inline Interval mul(Interval a, Interval b)
{
  if (!a.valid() || !b.valid()) return unknown();
  if (a.zero() || b.zero()) return {};
  const std::array<double, 4> products {a.lo*b.lo, a.lo*b.hi, a.hi*b.lo, a.hi*b.hi};
  for (double value : products) if (!std::isfinite(value)) return unknown();
  return {std::nextafter(*std::min_element(products.begin(), products.end()), -inf),
    std::nextafter(*std::max_element(products.begin(), products.end()), inf)};
}
inline Interval divide(Interval a, double b)
{
  if (!a.valid() || !std::isfinite(b) || b == 0.0) return unknown();
  double lo = a.lo / b, hi = a.hi / b;
  if (!std::isfinite(lo) || !std::isfinite(hi)) return unknown();
  if (b < 0.0) std::swap(lo, hi);
  return {std::nextafter(lo, -inf), std::nextafter(hi, inf)};
}

using Box = std::array<Interval, 3>;
using Poly = std::array<Interval, 11>;
using VectorPoly = std::array<Poly, 3>;
struct Span { Box box; VectorPoly c, d; };
inline Poly plus(const Poly& a, const Poly& b)
{
  Poly out;
  for (std::size_t i = 0; i < out.size(); ++i) out[i] = add(a[i], b[i]);
  return out;
}
inline Poly times(const Poly& a, const Poly& b)
{
  Poly out;
  for (std::size_t i = 0; i < a.size(); ++i)
    for (std::size_t j = 0; i+j < out.size(); ++j)
      out[i+j] = add(out[i+j], mul(a[i], b[j]));
  return out;
}
inline Poly scale(const Poly& a, Interval b)
{
  Poly out;
  for (std::size_t i = 0; i < out.size(); ++i) out[i] = mul(a[i], b);
  return out;
}
inline Poly dot(const VectorPoly& a, const VectorPoly& b)
{
  Poly out;
  for (std::size_t i = 0; i < 3; ++i) out = plus(out, times(a[i], b[i]));
  return out;
}
inline unsigned choose(unsigned n, unsigned k)
{
  unsigned result = 1;
  for (unsigned i = 1; i <= k; ++i) result = result*(n+1-i)/i;
  return result;
}
inline bool excludes_resultant(const Span& span, Interval radius_squared,
  const std::array<double, 3>& origin, const std::array<double, 3>& direction)
{
  VectorPoly w = span.c;
  Poly a, d;
  Interval q;
  for (std::size_t axis = 0; axis < 3; ++axis) {
    w[axis][0] = sub(w[axis][0], {origin[axis], origin[axis]});
    const Interval ray_d {direction[axis], direction[axis]};
    a = plus(a, scale(span.d[axis], ray_d));
    d = plus(d, scale(w[axis], ray_d));
    q = add(q, mul(ray_d, ray_d));
  }
  const Poly b = dot(w, span.d);
  Poly e = dot(w, w);
  e[0] = sub(e[0], radius_squared);
  const Poly p = plus(plus(scale(times(b, b), q),
    scale(times(times(a, b), d), {-2.0, -2.0})), times(times(a, a), e));
  // deg(A,B,D,E) <= (2,5,3,6), hence no term above degree ten exists.
  // Degree elevation includes both closed endpoints and singular A=B=0 roots.
  bool positive = true, negative = true;
  for (unsigned i = 0; i <= 10; ++i) {
    Interval control;
    for (unsigned k = 0; k <= i; ++k) {
      const double numerator = choose(i, k), denominator = choose(10, k);
      const Interval weight = divide({numerator, numerator}, denominator);
      control = add(control, mul(p[k], weight));
    }
    if (!control.valid()) return false;
    positive = positive && control.lo > 0.0;
    negative = negative && control.hi < 0.0;
  }
  return positive || negative;
}

struct Node {
  Box box;
  std::size_t left {0}, right {0}, first {0}, count {0};
};
struct Data {
  std::vector<Span> spans;
  std::vector<std::size_t> order;
  std::vector<Node> nodes;
  Interval radius_squared;
  bool valid {false};
};
inline std::size_t build_node(Data& data, std::size_t first, std::size_t count)
{
  const auto index = data.nodes.size();
  Node node;
  node.box = data.spans[data.order[first]].box;
  for (std::size_t i = first+1; i < first+count; ++i)
    for (std::size_t axis = 0; axis < 3; ++axis) {
      const auto box = data.spans[data.order[i]].box[axis];
      node.box[axis].lo = std::min(node.box[axis].lo, box.lo);
      node.box[axis].hi = std::max(node.box[axis].hi, box.hi);
    }
  data.nodes.push_back(node);
  if (count <= 4) {
    data.nodes[index].first = first;
    data.nodes[index].count = count;
  } else {
    // Equal-count partition bounds tree depth independently of geometry.
    const std::size_t axis = index % 3;
    const auto middle = first+count/2;
    std::nth_element(data.order.begin()+first, data.order.begin()+middle,
      data.order.begin()+first+count, [&](std::size_t a, std::size_t b) {
        return data.spans[a].box[axis].lo < data.spans[b].box[axis].lo;
      });
    data.nodes[index].left = build_node(data, first, count/2);
    data.nodes[index].right = build_node(data, middle, count-count/2);
  }
  return index;
}
inline void build(Data& data)
{
  data.valid = supported_environment() && !data.spans.empty() && data.spans.size() <= 512;
  for (const auto& span : data.spans)
    for (const auto& axis : span.box) data.valid = data.valid && axis.valid();
  if (!data.valid) return;
  data.order.resize(data.spans.size());
  std::iota(data.order.begin(), data.order.end(), 0);
  data.nodes.reserve(2*data.spans.size());
  build_node(data, 0, data.spans.size());
}

// Returns possible on any arithmetic uncertainty. Entry is used for ordering
// only, never as an unproved best-hit pruning threshold.
inline bool ray_box(const Box& box, const std::array<double, 3>& o,
  const std::array<double, 3>& d, bool whole_line, double& entry)
{
  double enter = whole_line ? -inf : 0.0, exit = inf;
  for (std::size_t axis = 0; axis < 3; ++axis) {
    if (!box[axis].valid()) { entry = -inf; return true; }
    if (d[axis] == 0.0) {
      if (o[axis] < box[axis].lo || o[axis] > box[axis].hi) return false;
      continue;
    }
    const auto slab = divide(sub(box[axis], {o[axis], o[axis]}), d[axis]);
    if (!slab.valid()) { entry = -inf; return true; }
    enter = std::max(enter, slab.lo);
    exit = std::min(exit, slab.hi);
    if (enter > exit) return false;
  }
  entry = enter;
  return true;
}
struct Candidates { std::array<std::size_t, 512> ids {}; std::size_t count {0}; };
inline Candidates all_spans(const Data& data)
{
  Candidates out;
  out.count = data.spans.size();
  std::iota(out.ids.begin(), out.ids.begin()+out.count, 0);
  return out;
}
inline Candidates candidates(const Data& data, const std::array<double, 3>& o,
  const std::array<double, 3>& d, bool whole_line)
{
  Candidates out;
  std::array<std::size_t, 32> pending {};
  std::size_t size = 1;
  while (size) {
    const auto& node = data.nodes[pending[--size]];
    double entry;
    if (!ray_box(node.box, o, d, whole_line, entry)) continue;
    if (node.count) {
      for (std::size_t i = node.first; i < node.first+node.count; ++i) {
        const auto id = data.order[i];
        if (ray_box(data.spans[id].box, o, d, whole_line, entry))
          out.ids[out.count++] = id;
      }
    } else {
      double left, right;
      const bool hit_left = ray_box(data.nodes[node.left].box, o, d, whole_line, left);
      const bool hit_right = ray_box(data.nodes[node.right].box, o, d, whole_line, right);
      // Defensive degradation to the full exact population, never truncation.
      if (size+2 > pending.size()) return all_spans(data);
      if (hit_left && hit_right) {
        pending[size++] = left <= right ? node.right : node.left;
        pending[size++] = left <= right ? node.left : node.right;
      } else if (hit_left) pending[size++] = node.left;
      else if (hit_right) pending[size++] = node.right;
    }
  }
  return out;
}
} // namespace stellarcsg::circular_filter
