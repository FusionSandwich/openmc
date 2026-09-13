// Independent containment checks for the private swept-tube floating filter.
// This test must be compiled with the same strict-FP options as the filter TU.
#include "../src/swept_floating_filter.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

#include <gmpxx.h>

namespace {
namespace filter = stellarcsg::circular_filter;
using Q = mpq_class;
using ExactPoly = std::array<Q, 11>;
using ExactVectorPoly = std::array<ExactPoly, 3>;

void require(bool condition, const std::string& label)
{
  if (!condition) throw std::runtime_error(label);
}

void contains(filter::Interval enclosure, const Q& lo, const Q& hi,
  const std::string& label)
{
  if (!enclosure.valid()) return; // Unknown is the required conservative result.
  require(Q(enclosure.lo) <= lo && Q(enclosure.hi) >= hi, label);
}

void arithmetic_containment()
{
  const double denorm = std::numeric_limits<double>::denorm_min();
  const double normal = std::numeric_limits<double>::min();
  const double largest = std::numeric_limits<double>::max();
  const std::vector<filter::Interval> values {
    {0.0, 0.0}, {-0.0, 0.0}, {denorm, 4*denorm},
    {-4*denorm, -denorm}, {-normal, normal}, {-3.25, 7.5},
    {-largest, -largest/2}, {largest/2, largest}
  };
  for (const auto& a : values) for (const auto& b : values) {
    const Q alo(a.lo), ahi(a.hi), blo(b.lo), bhi(b.hi);
    contains(filter::add(a, b), alo+blo, ahi+bhi, "add lost containment");
    contains(filter::sub(a, b), alo-bhi, ahi-blo, "sub lost containment");
    const std::array<Q, 4> products {alo*blo, alo*bhi, ahi*blo, ahi*bhi};
    contains(filter::mul(a, b), *std::min_element(products.begin(), products.end()),
      *std::max_element(products.begin(), products.end()), "mul lost containment");
  }
  for (const auto& a : values) for (double divisor :
      {-largest, -normal, -denorm, 0.5, denorm, normal, largest}) {
    const Q qlo = Q(a.lo)/Q(divisor), qhi = Q(a.hi)/Q(divisor);
    contains(filter::divide(a, divisor), std::min(qlo, qhi), std::max(qlo, qhi),
      "divide lost containment");
  }
  require(!filter::add({largest, largest}, {largest, largest}).valid(),
    "overflowing add did not become unknown");
  require(!filter::divide({1.0, 1.0}, denorm).valid(),
    "overflowing divide did not become unknown");
}

void environment_guards()
{
#if defined(__SSE__) || defined(_M_X64)
  struct RestoreMxcsr {
    unsigned value;
    ~RestoreMxcsr() { _mm_setcsr(value); }
  } restore {_mm_getcsr()};
  const auto rejected = [&](unsigned mask, const char* label) {
    _mm_setcsr(restore.value | mask);
    if ((_mm_getcsr() & mask) != 0)
      require(!filter::supported_environment(), label);
    _mm_setcsr(restore.value);
  };
  rejected(0x2000U, "MXCSR non-nearest rounding was accepted");
  rejected(0x8000U, "MXCSR flush-to-zero was accepted");
  rejected(0x0040U, "MXCSR denormals-are-zero was accepted");
#else
  require(!filter::supported_environment(),
    "unreviewed non-x86 floating environment was accepted");
#endif
}

bool exact_ray_box(const filter::Box& box, const std::array<double, 3>& origin,
  const std::array<double, 3>& direction, bool whole_line)
{
  Q enter = 0, exit = 0;
  bool bounded = false;
  for (std::size_t axis = 0; axis < 3; ++axis) {
    const Q o(origin[axis]), d(direction[axis]);
    const Q lo(box[axis].lo), hi(box[axis].hi);
    if (d == 0) {
      if (o < lo || o > hi) return false;
      continue;
    }
    Q a = (lo-o)/d, b = (hi-o)/d;
    if (a > b) std::swap(a, b);
    if (!bounded) {
      enter = whole_line ? a : std::max(Q(0), a);
      exit = b;
      bounded = true;
    } else {
      enter = std::max(enter, a);
      exit = std::min(exit, b);
    }
    if (enter > exit) return false;
  }
  return bounded;
}

void slab_implication()
{
  const filter::Box unit {{{0,1}, {0,1}, {0,1}}};
  double entry = 0;
  require(filter::ray_box(unit, {-1,0,0}, {1,0,0}, false, entry),
    "closed tangential slab contact was discarded");
  const filter::Box behind {{{-2,-1}, {-1,1}, {-1,1}}};
  const bool forward = filter::ray_box(behind, {0,0,0}, {1,0,0}, false, entry);
  require(!forward && !exact_ray_box(behind, {0,0,0}, {1,0,0}, false),
    "forward slab unexpectedly retained a box behind the origin");
  const bool line = filter::ray_box(behind, {0,0,0}, {1,0,0}, true, entry);
  require(line && exact_ray_box(behind, {0,0,0}, {1,0,0}, true),
    "whole-line coincident slab discarded a box behind the origin");
  const double largest = std::numeric_limits<double>::max();
  const double denorm = std::numeric_limits<double>::denorm_min();
  const filter::Box extreme {{{-largest,-largest/2}, {-1,1}, {-1,1}}};
  require(filter::ray_box(extreme, {largest,0,0}, {denorm,0,0}, false, entry),
    "uncertain overflow slab was converted to a miss");
}

ExactPoly plus(ExactPoly a, const ExactPoly& b)
{
  for (std::size_t i = 0; i < a.size(); ++i) a[i] += b[i];
  return a;
}

ExactPoly scale(ExactPoly a, const Q& factor)
{
  for (auto& value : a) value *= factor;
  return a;
}

ExactPoly times(const ExactPoly& a, const ExactPoly& b)
{
  ExactPoly result {};
  for (std::size_t i = 0; i < a.size(); ++i)
    for (std::size_t j = 0; i+j < result.size(); ++j)
      result[i+j] += a[i]*b[j];
  return result;
}

ExactPoly dot(const ExactVectorPoly& a, const ExactVectorPoly& b)
{
  ExactPoly result {};
  for (std::size_t axis = 0; axis < 3; ++axis)
    result = plus(result, times(a[axis], b[axis]));
  return result;
}

unsigned choose(unsigned n, unsigned k)
{
  unsigned result = 1;
  for (unsigned i = 1; i <= k; ++i) result = result*(n+1-i)/i;
  return result;
}

ExactPoly exact_resultant(const ExactVectorPoly& c, const ExactVectorPoly& tangent,
  const std::array<Q, 3>& origin, const std::array<Q, 3>& direction,
  const Q& radius_squared)
{
  ExactVectorPoly w = c;
  ExactPoly a {}, d {};
  Q q = 0;
  for (std::size_t axis = 0; axis < 3; ++axis) {
    w[axis][0] -= origin[axis];
    a = plus(a, scale(tangent[axis], direction[axis]));
    d = plus(d, scale(w[axis], direction[axis]));
    q += direction[axis]*direction[axis];
  }
  const ExactPoly b = dot(w, tangent);
  ExactPoly e = dot(w, w);
  e[0] -= radius_squared;
  return plus(plus(scale(times(b, b), q), scale(times(times(a, b), d), -2)),
    times(times(a, a), e));
}

bool exact_bernstein_strict_sign(const ExactPoly& p)
{
  bool positive = true, negative = true;
  for (unsigned i = 0; i <= 10; ++i) {
    Q control = 0;
    for (unsigned k = 0; k <= i; ++k)
      control += p[k]*Q(static_cast<unsigned long>(choose(i, k)),
        static_cast<unsigned long>(choose(10, k)));
    positive = positive && control > 0;
    negative = negative && control < 0;
  }
  return positive || negative;
}

void assign_point(filter::Interval& target, const Q& value)
{
  const double converted = value.get_d();
  require(Q(converted) == value, "test generator produced a non-binary64 coefficient");
  target = {converted, converted};
}

std::uint64_t random_state = UINT64_C(0x6a09e667f3bcc909);
int small_random()
{
  random_state ^= random_state << 13;
  random_state ^= random_state >> 7;
  random_state ^= random_state << 17;
  return static_cast<int>(random_state % 9)-4;
}

void resultant_implication()
{
  unsigned exclusions = 0;
  for (unsigned trial = 0; trial < 512; ++trial) {
    ExactVectorPoly c {}, tangent {};
    filter::Span span {};
    for (std::size_t axis = 0; axis < 3; ++axis) {
      for (std::size_t power = 0; power <= 3; ++power) {
        c[axis][power] = small_random();
        assign_point(span.c[axis][power], c[axis][power]);
        if (power) {
          tangent[axis][power-1] = Q(static_cast<unsigned long>(power))*c[axis][power];
          assign_point(span.d[axis][power-1], tangent[axis][power-1]);
        }
      }
    }
    std::array<Q, 3> origin, direction;
    std::array<double, 3> floating_origin, floating_direction;
    for (std::size_t axis = 0; axis < 3; ++axis) {
      origin[axis] = small_random();
      direction[axis] = small_random();
      floating_origin[axis] = origin[axis].get_d();
      floating_direction[axis] = direction[axis].get_d();
    }
    if (direction[0] == 0 && direction[1] == 0 && direction[2] == 0) {
      direction[0] = 1;
      floating_direction[0] = 1;
    }
    // Keep a deterministic non-vacuous subsequence while the other trials
    // exercise unconstrained cubic resultants.
    if (trial%8 == 0) {
      c = {}; tangent = {}; span = {};
      c[0][0] = 10; c[0][1] = 1; tangent[0][0] = 1;
      assign_point(span.c[0][0], c[0][0]);
      assign_point(span.c[0][1], c[0][1]);
      assign_point(span.d[0][0], tangent[0][0]);
      origin = {Q(0), Q(0), Q(0)};
      direction = {Q(0), Q(0), Q(1)};
      floating_origin = {0,0,0};
      floating_direction = {0,0,1};
    }
    const Q radius_squared = Q(1 + trial%7);
    const filter::Interval floating_radius {radius_squared.get_d(), radius_squared.get_d()};
    if (filter::excludes_resultant(span, floating_radius,
          floating_origin, floating_direction)) {
      ++exclusions;
      require(exact_bernstein_strict_sign(
        exact_resultant(c, tangent, origin, direction, radius_squared)),
        "floating strict-sign result lacks exact Bernstein certificate");
    }
  }
  require(exclusions != 0, "random implication check was vacuous");
}

void singular_a_control()
{
  filter::Span span {};
  // c(u)=(1+u,2,0), ray x=(0,0,lambda), r=1 gives A=0 and P=(1+u)^2.
  span.c[0][0] = {1,1}; span.c[0][1] = {1,1}; span.d[0][0] = {1,1};
  span.c[1][0] = {2,2};
  require(filter::excludes_resultant(span, {1,1}, {0,0,0}, {0,0,1}),
    "strict positive A=0 resultant was not excluded");
}
}

int main()
{
#if !defined(STELLARCSG_FILTER_STRICT_FP)
  require(!filter::supported_environment(),
    "filter enabled without the reviewed strict-FP compile contract");
#else
  environment_guards();
  arithmetic_containment();
  slab_implication();
  singular_a_control();
  resultant_implication();
#endif
}
