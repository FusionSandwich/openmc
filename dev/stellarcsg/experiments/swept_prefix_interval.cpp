// Experimental, fail-closed span-prefix exclusion using the compiled powers.
// It is not wired into tracking: finite root-tile isolation and formal
// floating-path review are still required before a query can be admitted.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <algorithm>
#include <array>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr double infinity = std::numeric_limits<double>::infinity();
constexpr double two_pi = 6.283185307179586476925286766559005768;
// Experimental allowance for sin/cos roundoff. This is not an audited libm
// error bound and is one reason the result cannot admit a production root.
double unit_circle_slack = 1.0e-12;

double down(double value) { return std::nextafter(value, -infinity); }
double up(double value) { return std::nextafter(value, infinity); }

struct I {
  double lo;
  double hi;
  static I point(double x) { return {x, x}; }
  static I bounds(double a, double b)
  {
    if (std::isnan(a) || std::isnan(b)) return {-infinity, infinity};
    return {down(a), up(b)};
  }
  static I full() { return {-infinity, infinity}; }
  bool contains_zero() const { return lo <= 0.0 && hi >= 0.0; }
  std::optional<I> clip_unit() const
  {
    const double a = std::max(-1.0, lo);
    const double b = std::min(1.0, hi);
    if (a > b) return std::nullopt;
    return I {a, b};
  }
};

I operator+(I a, I b) { return I::bounds(a.lo + b.lo, a.hi + b.hi); }
I operator-(I a) { return {-a.hi, -a.lo}; }
I operator-(I a, I b) { return a + -b; }
I operator*(I a, I b)
{
  const std::array<double, 4> products {
    a.lo * b.lo, a.lo * b.hi, a.hi * b.lo, a.hi * b.hi};
  if (std::any_of(products.begin(), products.end(),
                  [](double x) { return std::isnan(x); })) return I::full();
  return I::bounds(*std::min_element(products.begin(), products.end()),
                   *std::max_element(products.begin(), products.end()));
}
I operator/(I a, I b)
{
  if (b.contains_zero()) return I::full();
  const std::array<double, 4> quotients {
    a.lo / b.lo, a.lo / b.hi, a.hi / b.lo, a.hi / b.hi};
  if (std::any_of(quotients.begin(), quotients.end(),
                  [](double x) { return std::isnan(x); })) return I::full();
  return I::bounds(*std::min_element(quotients.begin(), quotients.end()),
                   *std::max_element(quotients.begin(), quotients.end()));
}
I square(I x)
{
  const double a = x.lo * x.lo;
  const double b = x.hi * x.hi;
  if (std::isnan(a) || std::isnan(b)) return I::full();
  if (x.contains_zero()) return {0.0, up(std::max(a, b))};
  return I::bounds(std::min(a, b), std::max(a, b));
}
I square_root(I x)
{
  if (x.hi < 0.0 || std::isnan(x.hi)) return I::full();
  return {x.lo <= 0.0 ? 0.0 : down(std::sqrt(x.lo)),
          up(std::sqrt(x.hi))};
}
std::optional<I> intersection(I a, I b)
{
  const double lo = std::max(a.lo, b.lo);
  const double hi = std::min(a.hi, b.hi);
  if (lo > hi) return std::nullopt;
  return I {lo, hi};
}

using V = std::array<I, 3>;
I dot(const V& a, const V& b)
{
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}
V cross(const V& a, const V& b)
{
  return {a[1] * b[2] - a[2] * b[1],
          a[2] * b[0] - a[0] * b[2],
          a[0] * b[1] - a[1] * b[0]};
}
std::optional<V> normalized(const V& a)
{
  const I length = square_root(square(a[0]) + square(a[1]) + square(a[2]));
  if (!(length.lo > 0.0) || !std::isfinite(length.hi))
    return std::nullopt;
  // The production Vec3 operator/ forms one reciprocal, then multiplies.
  const I inverse = I::point(1.0) / length;
  return V {a[0] * inverse, a[1] * inverse, a[2] * inverse};
}

I polynomial(const stellarcsg::SweptSpan& span, int field, I u)
{
  const auto* p = span.power.data() + 4 * field;
  return ((I::point(p[3]) * u + I::point(p[2])) * u
          + I::point(p[1])) * u + I::point(p[0]);
}
I derivative(const stellarcsg::SweptSpan& span, int field, I u,
             double scale)
{
  const auto* p = span.power.data() + 4 * field;
  return ((I::point(3.0) * I::point(p[3]) * u
           + I::point(2.0) * I::point(p[2])) * u + I::point(p[1]))
         * I::point(scale);
}

enum class Outcome {
  projection, single_prefix, unit_branches, unit_circle, ray_prefix,
  undecided_frame, undecided_projection, undecided_root, alpha_arcs
};
const char* name(Outcome outcome)
{
  switch (outcome) {
  case Outcome::projection: return "excluded_projection";
  case Outcome::single_prefix: return "excluded_single_prefix";
  case Outcome::unit_branches: return "excluded_unit_branches";
  case Outcome::unit_circle: return "excluded_unit_circle";
  case Outcome::ray_prefix: return "excluded_ray_prefix";
  case Outcome::undecided_frame: return "undecided_frame";
  case Outcome::undecided_projection: return "undecided_projection";
  case Outcome::undecided_root: return "undecided_root";
  case Outcome::alpha_arcs: return "excluded_alpha_arcs";
  }
  return "invalid";
}
bool excluded(Outcome state)
{
  return state == Outcome::projection || state == Outcome::single_prefix
    || state == Outcome::unit_branches || state == Outcome::unit_circle
    || state == Outcome::ray_prefix || state == Outcome::alpha_arcs;
}

std::array<I, 2> complementary_branches(I known)
{
  const double largest = std::max(std::abs(known.lo), std::abs(known.hi));
  const double squared_upper = up(largest * largest);
  const double complement_lower = std::max(0.0,
    down((1.0 - unit_circle_slack) - squared_upper));
  const double lower = std::max(0.0, down(std::sqrt(complement_lower)));
  return {I {-1.0, -lower}, I {lower, 1.0}};
}

Outcome exclude_tile(const stellarcsg::SweptSpan& span, I u,
                     const stellarcsg::Vec3& origin,
                     const stellarcsg::Vec3& direction,
                     int dominant_axis, double cutoff, bool use_unit_circle,
                     double projection_slack = 0.0,
                     int alpha_arc_count = 0)
{
  const double scale = 1.0 / (span.angle_max - span.angle_min);
  V center, center_derivative, supplied;
  for (int axis = 0; axis < 3; ++axis) {
    center[axis] = polynomial(span, axis, u);
    center_derivative[axis] = derivative(span, axis, u, scale);
    supplied[axis] = polynomial(span, 3 + axis, u);
  }
  const auto tangent = normalized(center_derivative);
  if (!tangent) return Outcome::undecided_frame;
  const I projection = dot(supplied, *tangent);
  V raw_normal;
  for (int axis = 0; axis < 3; ++axis)
    raw_normal[axis] = supplied[axis] - projection * (*tangent)[axis];
  auto normal = normalized(raw_normal);
  if (!normal) return Outcome::undecided_frame;
  const auto binormal = normalized(cross(*tangent, *normal));
  if (!binormal) return Outcome::undecided_frame;
  normal = cross(*binormal, *tangent);
  const I major = polynomial(span, 6, u);
  const I minor = polynomial(span, 7, u);
  const int j = (dominant_axis + 1) % 3;
  const int l = (dominant_axis + 2) % 3;
  const std::array<double, 3> o {origin.x, origin.y, origin.z};
  const std::array<double, 3> d {direction.x, direction.y, direction.z};
  const auto row = [&](int axis) {
    const I dj = I::point(d[axis]);
    const I dk = I::point(d[dominant_axis]);
    const I offset = (center[axis] - I::point(o[axis])) * dk
      - (center[dominant_axis] - I::point(o[dominant_axis])) * dj;
    const I a = major * ((*normal)[axis] * dk
      - (*normal)[dominant_axis] * dj);
    const I b = minor * ((*binormal)[axis] * dk
      - (*binormal)[dominant_axis] * dj);
    // For the fixed axial fixture, this pads each transverse equation for
    // accepted projected residual and a conservative arithmetic allowance.
    return std::array<I, 3> {
      -offset + I::bounds(-projection_slack, projection_slack), a, b};
  };
  const auto first = row(j);
  const auto second = row(l);
  const I unit {-1.0, 1.0};
  const auto ray_t = [&](I cosine, I sine) {
    const I coordinate = center[dominant_axis]
      + major * cosine * (*normal)[dominant_axis]
      + minor * sine * (*binormal)[dominant_axis];
    return (coordinate - I::point(o[dominant_axis]))
      / I::point(d[dominant_axis]);
  };
  const auto away = [&](I t) { return t.hi < 0.0 || t.lo > cutoff; };
  // An experimental alternative to the unit-circle test: cover one complete
  // alpha period by correlated cosine/sine rectangles. The 1e-6 endpoint
  // allowance is not a certified error bound for the production libm path.
  const auto arcs_exclude = [&]() {
    if (alpha_arc_count == 0) return false;
    constexpr double trig_slack = 1.0e-6;
    for (int arc = 0; arc < alpha_arc_count; ++arc) {
      const double a = two_pi * static_cast<double>(arc)
        / static_cast<double>(alpha_arc_count);
      const double b = two_pi * static_cast<double>(arc + 1)
        / static_cast<double>(alpha_arc_count);
      // Arc counts are multiples of four, so extrema lie on arc endpoints.
      const double ca = std::cos(a), cb = std::cos(b);
      const double sa = std::sin(a), sb = std::sin(b);
      I cosine = I::bounds(
        std::max(-1.0, std::min(ca, cb) - trig_slack),
        std::min(1.0, std::max(ca, cb) + trig_slack));
      I sine = I::bounds(
        std::max(-1.0, std::min(sa, sb) - trig_slack),
        std::min(1.0, std::max(sa, sb) + trig_slack));
      const auto contract = [&](const std::array<I, 3>& equation) {
        const I rhs = equation[0], c = equation[1], s = equation[2];
        if (!c.contains_zero()) {
          const auto narrowed = intersection(cosine, (rhs - s * sine) / c);
          if (!narrowed) return false;
          cosine = *narrowed;
        }
        if (!s.contains_zero()) {
          const auto narrowed = intersection(sine, (rhs - c * cosine) / s);
          if (!narrowed) return false;
          sine = *narrowed;
        }
        const I projected = c * cosine + s * sine;
        return projected.lo <= rhs.hi && projected.hi >= rhs.lo;
      };
      bool possible = true;
      for (int pass = 0; pass < 3 && possible; ++pass)
        possible = contract(first) && contract(second);
      if (possible && !away(ray_t(cosine, sine))) return false;
    }
    return true;
  };
  for (const auto& equation : {first, second}) {
    const I rhs = equation[0], a = equation[1], b = equation[2];
    if (!a.contains_zero()) {
      const auto cosine = ((rhs - b * unit) / a).clip_unit();
      if (!cosine) return Outcome::projection;
      if (away(ray_t(*cosine, unit))) return Outcome::single_prefix;
      if (use_unit_circle) {
        const auto branches = complementary_branches(*cosine);
        if (away(ray_t(*cosine, branches[0]))
            && away(ray_t(*cosine, branches[1])))
          return Outcome::unit_branches;
      }
    }
    if (!b.contains_zero()) {
      const auto sine = ((rhs - a * unit) / b).clip_unit();
      if (!sine) return Outcome::projection;
      if (away(ray_t(unit, *sine))) return Outcome::single_prefix;
      if (use_unit_circle) {
        const auto branches = complementary_branches(*sine);
        if (away(ray_t(branches[0], *sine))
            && away(ray_t(branches[1], *sine)))
          return Outcome::unit_branches;
      }
    }
  }
  const I determinant = first[1] * second[2] - first[2] * second[1];
  if (determinant.contains_zero())
    return arcs_exclude() ? Outcome::alpha_arcs
                          : Outcome::undecided_projection;
  const auto cosine = ((first[0] * second[2]
    - first[2] * second[0]) / determinant).clip_unit();
  const auto sine = ((first[1] * second[0]
    - first[0] * second[1]) / determinant).clip_unit();
  if (!cosine || !sine) return Outcome::projection;
  const I length_squared = square(*cosine) + square(*sine);
  if (use_unit_circle && (length_squared.hi < 1.0 - unit_circle_slack
      || length_squared.lo > 1.0 + unit_circle_slack))
    return Outcome::unit_circle;
  if (away(ray_t(*cosine, *sine))) return Outcome::ray_prefix;
  return arcs_exclude() ? Outcome::alpha_arcs : Outcome::undecided_root;
}

struct SpanResult {
  std::size_t nodes {0};
  std::size_t undecided {0};
  std::array<std::size_t, 9> outcomes {};
};
SpanResult analyze_span(const stellarcsg::SweptSpan& span,
                        const stellarcsg::Vec3& origin,
                        const stellarcsg::Vec3& direction,
                        int dominant_axis, double cutoff, bool use_unit_circle,
                        double projection_slack = 0.0,
                        int max_depth = 36, std::size_t max_nodes = 10000,
                        int alpha_arc_count = 0)
{
  if (alpha_arc_count < 0 || alpha_arc_count % 4 != 0)
    throw std::invalid_argument("alpha arc count must be a multiple of four");
  struct Tile { double lo, hi; int depth; };
  // frame_in_span computes (angle - angle_min) * a rounded reciprocal.
  // Its evaluated endpoint may lie outside [0, 1] by more than one ulp.
  const double scale = 1.0 / (span.angle_max - span.angle_min);
  const I angle = I::bounds(span.angle_min, span.angle_max);
  const I local_u = (angle - I::point(span.angle_min)) * I::point(scale);
  std::vector<Tile> stack {{local_u.lo, local_u.hi, 0}};
  SpanResult result;
  while (!stack.empty()) {
    const auto tile = stack.back();
    stack.pop_back();
    if (++result.nodes > max_nodes) {
      ++result.undecided;
      break;
    }
    const Outcome state = exclude_tile(span, I::bounds(tile.lo, tile.hi),
      origin, direction, dominant_axis, cutoff, use_unit_circle,
      projection_slack, alpha_arc_count);
    if (excluded(state) || tile.depth == max_depth) {
      ++result.outcomes[static_cast<std::size_t>(state)];
      if (!excluded(state)) ++result.undecided;
      continue;
    }
    const double midpoint = 0.5 * (tile.lo + tile.hi);
    if (!(midpoint > tile.lo && midpoint < tile.hi)) {
      ++result.undecided;
      break;
    }
    stack.push_back({midpoint, tile.hi, tile.depth + 1});
    stack.push_back({tile.lo, midpoint, tile.depth + 1});
  }
  return result;
}

enum class QuadraticOutcome {
  separated_value, no_real_root, outside_prefix, separated_plane,
  undecided_frame, undecided_root
};

bool quadratic_excluded(QuadraticOutcome state)
{
  return state == QuadraticOutcome::separated_value
    || state == QuadraticOutcome::no_real_root
    || state == QuadraticOutcome::outside_prefix
    || state == QuadraticOutcome::separated_plane;
}

QuadraticOutcome exclude_quadratic_tile(
  const stellarcsg::SweptSpan& span, I u,
  const stellarcsg::Vec3& origin,
  const stellarcsg::Vec3& direction, double cutoff,
  double implicit_slack, double plane_slack)
{
  const double scale = 1.0 / (span.angle_max - span.angle_min);
  V center, center_derivative, supplied;
  for (int axis = 0; axis < 3; ++axis) {
    center[axis] = polynomial(span, axis, u);
    center_derivative[axis] = derivative(span, axis, u, scale);
    supplied[axis] = polynomial(span, 3 + axis, u);
  }
  const auto tangent = normalized(center_derivative);
  if (!tangent) return QuadraticOutcome::undecided_frame;
  const I projection = dot(supplied, *tangent);
  V raw_normal;
  for (int axis = 0; axis < 3; ++axis)
    raw_normal[axis] = supplied[axis] - projection * (*tangent)[axis];
  auto normal = normalized(raw_normal);
  if (!normal) return QuadraticOutcome::undecided_frame;
  const auto binormal = normalized(cross(*tangent, *normal));
  if (!binormal) return QuadraticOutcome::undecided_frame;
  normal = cross(*binormal, *tangent);
  const I major = polynomial(span, 6, u);
  const I minor = polynomial(span, 7, u);
  if (major.contains_zero() || minor.contains_zero())
    return QuadraticOutcome::undecided_frame;
  const std::array<double, 3> o {origin.x, origin.y, origin.z};
  const std::array<double, 3> d {direction.x, direction.y, direction.z};
  V offset;
  for (int axis = 0; axis < 3; ++axis)
    offset[axis] = I::point(o[axis]) - center[axis];
  const I an = dot(offset, *normal) / major;
  const I ab = dot(offset, *binormal) / minor;
  V ray_direction;
  for (int axis = 0; axis < 3; ++axis)
    ray_direction[axis] = I::point(d[axis]);
  const I bn = -dot(ray_direction, *normal) / major;
  const I bb = -dot(ray_direction, *binormal) / minor;
  const I t {0.0, cutoff};
  const I value = square(an - bn * t) + square(ab - bb * t)
    - I::point(1.0);
  if (value.lo > implicit_slack || value.hi < -implicit_slack)
    return QuadraticOutcome::separated_value;
  const I qa = square(bn) + square(bb);
  if (!(qa.lo > 0.0) || !std::isfinite(qa.hi))
    return QuadraticOutcome::undecided_root;
  const I qb = -I::point(2.0) * (an * bn + ab * bb);
  const I qc = square(an) + square(ab) - I::point(1.0)
    + I {-implicit_slack, implicit_slack};
  const I discriminant = square(qb) - I::point(4.0) * qa * qc;
  if (discriminant.hi < 0.0) return QuadraticOutcome::no_real_root;
  const I root = square_root(discriminant);
  const I denominator = I::point(2.0) * qa;
  const I first = (-qb - root) / denominator;
  const I second = (-qb + root) / denominator;
  bool used_plane = false;
  const auto branch_excluded = [&](I candidate) {
    const auto prefix = intersection(candidate, t);
    if (!prefix) return true;
    V at_root;
    for (int axis = 0; axis < 3; ++axis)
      at_root[axis] = offset[axis] + ray_direction[axis] * *prefix;
    const I plane = dot(at_root, *tangent);
    if (plane.lo > plane_slack || plane.hi < -plane_slack) {
      used_plane = true;
      return true;
    }
    return false;
  };
  if (!branch_excluded(first) || !branch_excluded(second))
    return QuadraticOutcome::undecided_root;
  return used_plane ? QuadraticOutcome::separated_plane
                    : QuadraticOutcome::outside_prefix;
}

struct QuadraticResult {
  std::size_t nodes {0};
  std::size_t undecided {0};
  std::array<std::size_t, 6> outcomes {};
};

QuadraticResult analyze_quadratic_span(
  const stellarcsg::SweptSpan& span,
  const stellarcsg::Vec3& origin,
  const stellarcsg::Vec3& direction, double cutoff,
  double implicit_slack, double plane_slack, int max_depth = 36,
  std::size_t max_nodes = 10000)
{
  struct Tile { double lo, hi; int depth; };
  const double scale = 1.0 / (span.angle_max - span.angle_min);
  const I angle = I::bounds(span.angle_min, span.angle_max);
  const I local_u = (angle - I::point(span.angle_min)) * I::point(scale);
  std::vector<Tile> stack {{local_u.lo, local_u.hi, 0}};
  QuadraticResult result;
  while (!stack.empty()) {
    const auto tile = stack.back();
    stack.pop_back();
    if (++result.nodes > max_nodes) {
      ++result.undecided;
      break;
    }
    const auto state = exclude_quadratic_tile(
      span, I::bounds(tile.lo, tile.hi), origin, direction, cutoff,
      implicit_slack, plane_slack);
    if (quadratic_excluded(state) || tile.depth == max_depth) {
      ++result.outcomes[static_cast<std::size_t>(state)];
      if (!quadratic_excluded(state)) ++result.undecided;
      continue;
    }
    const double midpoint = 0.5 * (tile.lo + tile.hi);
    if (!(midpoint > tile.lo && midpoint < tile.hi)) {
      ++result.undecided;
      break;
    }
    stack.push_back({midpoint, tile.hi, tile.depth + 1});
    stack.push_back({tile.lo, midpoint, tile.depth + 1});
  }
  return result;
}

int quadratic_seam_main(const char* h5)
{
  constexpr double slack = 1.0e-6;
  constexpr double plane_slack = 1.0e-4;
  std::cout << std::setprecision(17);
  const stellarcsg::Vec3 origin {550.0, 0.0, 0.0};
  const stellarcsg::Vec3 direction {-1.0, 0.0, 0.0};
  for (int member : {2, 3}) {
    const auto data = stellarcsg::read_swept_spline_surface_hdf5(
      h5, "/coils/coil_00" + std::to_string(member));
    const stellarcsg::CompiledSweptSplineSurface surface {data};
    const auto lead = surface.distance(origin, direction, false);
    if (!lead.found || !lead.terminal_unresolved)
      throw std::runtime_error("expected unresolved lead fixture changed");
    for (std::size_t span_id : {std::size_t {0}, surface.spans().size() - 1}) {
      for (double gap : {1.0, 1.0e-5, 0.0, -4.0}) {
        const auto result = analyze_quadratic_span(
          surface.spans()[span_id], origin, direction, lead.distance - gap,
          slack, plane_slack);
        std::cout << "{\"kind\":\"quadratic_seam\",\"member\":"
                  << member << ",\"span\":" << span_id
                  << ",\"gap_cm\":" << gap
                  << ",\"slack\":" << slack
                  << ",\"plane_slack_cm\":" << plane_slack
                  << ",\"nodes\":" << result.nodes
                  << ",\"undecided\":" << result.undecided
                  << ",\"outcomes\":[";
        for (std::size_t i = 0; i < result.outcomes.size(); ++i) {
          if (i != 0) std::cout << ',';
          std::cout << result.outcomes[i];
        }
        std::cout << "]}\n";
      }
    }
  }
  return 0;
}

stellarcsg::SweptSplineSurfaceData torus_data()
{
  // Match the geometry construction in recovery04_frozen_bank.cpp exactly.
  stellarcsg::SweptSplineSurfaceData data;
  data.coil_id = 9040;
  data.sample_count = 64;
  data.length = two_pi * 5.0;
  data.characteristic_length = 5.0;
  data.major_radius_coefficients.assign(data.sample_count, 0.25);
  data.minor_radius_coefficients.assign(data.sample_count, 0.25);
  for (std::size_t i = 0; i < data.sample_count; ++i) {
    const double a = two_pi * i / data.sample_count;
    const double c = std::cos(a), s = std::sin(a);
    for (double x : {5.0 * c, 5.0 * s, 0.0})
      data.centerline_coefficients.push_back(x);
    for (double x : {0.0, 0.0, 1.0})
      data.normal_coefficients.push_back(x);
    for (double x : {c, s, 0.0})
      data.binormal_coefficients.push_back(x);
  }
  return data;
}

std::string torus_hash(const stellarcsg::SweptSplineSurfaceData& data)
{
  // Stable payload identifier used by recovery04_frozen_bank.cpp.
  std::uint64_t hash = 1469598103934665603ULL;
  const auto add = [&hash](const void* bytes, std::size_t count) {
    const auto* p = static_cast<const unsigned char*>(bytes);
    for (std::size_t i = 0; i < count; ++i) {
      hash ^= p[i];
      hash *= 1099511628211ULL;
    }
  };
  add(&data.coil_id, sizeof(data.coil_id));
  for (const auto* values : {&data.centerline_coefficients,
         &data.normal_coefficients, &data.binormal_coefficients,
         &data.major_radius_coefficients, &data.minor_radius_coefficients}) {
    for (double value : *values) add(&value, sizeof(value));
  }
  std::ostringstream out;
  out << std::hex << hash;
  return out.str();
}

int quadratic_bank_anchors_main(const char* bank_path)
{
  std::ifstream bank {bank_path};
  std::string line;
  if (!std::getline(bank, line))
    throw std::runtime_error("missing frozen bank header");
  const auto data = torus_data();
  const std::string coefficient_hash = torus_hash(data);
  const stellarcsg::CompiledSweptSplineSurface surface {data, true};
  std::size_t selected = 0;
  std::cout << std::setprecision(17);
  while (std::getline(bank, line)) {
    std::stringstream stream {line};
    std::vector<std::string> fields;
    std::string field;
    while (std::getline(stream, field, ',')) fields.push_back(field);
    if (fields.size() != 15) throw std::runtime_error("malformed frozen bank row");
    const std::string& id = fields[0];
    if (id != "a03" && id != "a06" && id != "a08" && id != "a15")
      continue;
    if (fields[1] != "torus" || fields[2] != coefficient_hash)
      throw std::runtime_error("anchor geometry or coefficients changed");
    ++selected;
    const stellarcsg::Vec3 origin {std::stod(fields[9]),
                                   std::stod(fields[10]),
                                   std::stod(fields[11])};
    const stellarcsg::Vec3 supplied_direction {std::stod(fields[12]),
                                               std::stod(fields[13]),
                                               std::stod(fields[14])};
    const auto direction = stellarcsg::normalized(supplied_direction);
    const auto candidate = surface.distance(origin, supplied_direction, false);
    const std::vector<double> cutoffs = id == "a03"
      ? std::vector<double> {0.00199, 0.002, 0.012}
      : id == "a06" ? std::vector<double> {0.0, 0.01}
      : std::vector<double> {1.99999, 2.0, 2.1};
    for (std::size_t span_id : {std::size_t {0}, surface.spans().size() - 1}) {
      for (double cutoff : cutoffs) {
        const auto result = analyze_quadratic_span(surface.spans()[span_id],
          origin, direction, cutoff, 1.0e-6, 1.0e-4, 36, 2000);
        std::cout << "{\"kind\":\"quadratic_bank_anchor\",\"id\":\""
                  << id << "\",\"span\":" << span_id
                  << ",\"cutoff_cm\":" << cutoff
                  << ",\"candidate_disposition\":\""
                  << (candidate.disposition() == stellarcsg::DistanceDisposition::hit
                        ? "hit" : candidate.disposition()
                          == stellarcsg::DistanceDisposition::no_hit
                        ? "no_hit" : "unresolved") << "\""
                  << ",\"candidate_distance_cm\":";
        if (candidate.found) std::cout << candidate.distance;
        else std::cout << "null";
        std::cout << ",\"nodes\":" << result.nodes
                  << ",\"undecided\":" << result.undecided
                  << ",\"outcomes\":[";
        for (std::size_t i = 0; i < result.outcomes.size(); ++i) {
          if (i != 0) std::cout << ',';
          std::cout << result.outcomes[i];
        }
        std::cout << "]}\n";
      }
    }
  }
  if (selected != 4) throw std::runtime_error("expected four bank anchors");
  return 0;
}

} // namespace

int main(int argc, char** argv)
{
  try {
    if (!std::numeric_limits<double>::is_iec559
        || std::fegetround() != FE_TONEAREST
        || std::numeric_limits<double>::has_denorm != std::denorm_present
        || std::ldexp(1.0, -1022) * 0.5 == 0.0) {
      throw std::runtime_error("IEEE nearest and subnormal preflight failed");
    }
    if (argc == 3 && std::string(argv[2]) == "--quadratic-seams") {
      return quadratic_seam_main(argv[1]);
    }
    if (argc == 3 && std::string(argv[2]) == "--quadratic-bank-anchors") {
      return quadratic_bank_anchors_main(argv[1]);
    }
    if (argc != 2) throw std::invalid_argument(
      "usage: swept_prefix_interval H5 [--quadratic-seams]");
    std::cout << std::setprecision(17);
    const stellarcsg::Vec3 origin {550.0, 0.0, 0.0};
    const stellarcsg::Vec3 direction {-1.0, 0.0, 0.0};
    constexpr int dominant_axis = 0;
    constexpr double gap = 1.0e-11;
    stellarcsg::SweptSpan underflow_witness;
    underflow_witness.angle_min = 0.0;
    underflow_witness.angle_max = 1.0;
    underflow_witness.power[1] = 2.2227587494850775e-162;
    underflow_witness.power[4 * 4] = 1.0;
    underflow_witness.power[4 * 6] = 1.0;
    underflow_witness.power[4 * 7] = 1.0;
    const auto witness = exclude_tile(underflow_witness, I::bounds(0.0, 1.0),
      origin, direction, dominant_axis, 1.0, true);
    std::cout << "{\"kind\":\"underflow_control\",\"state\":\""
              << name(witness) << "\"}\n";
    if (witness != Outcome::undecided_frame)
      throw std::runtime_error("underflow frame was falsely excluded");
    for (int member : {2, 3}) {
      const auto data = stellarcsg::read_swept_spline_surface_hdf5(
        argv[1], "/coils/coil_00" + std::to_string(member));
      const stellarcsg::CompiledSweptSplineSurface surface {data};
      const auto lead = surface.distance(origin, direction, false);
      if (!lead.found || !lead.terminal_unresolved)
        throw std::runtime_error("expected unresolved lead fixture changed");
      const double projected_tolerance = std::max(
        1.0e-10 * data.characteristic_length,
        64.0 * std::numeric_limits<double>::epsilon()
          * data.characteristic_length);
      const double projection_slack = 2.0 * projected_tolerance
        + 256.0 * std::numeric_limits<double>::epsilon()
          * data.characteristic_length;
      std::size_t selected = 0, excluded_prefix = 0, rectangle_excluded = 0;
      std::size_t u_endpoint_above_one_ulp = 0;
      std::size_t padded_excluded = 0;
      std::size_t padded_zero_gap_unknown = 0;
      std::size_t padded_negative_unknown = 0;
      std::array<std::size_t, 3> slack_excluded {};
      std::array<std::array<std::size_t, 3>, 3> gap_slack_excluded {};
      constexpr std::array<double, 6> rectangle_gaps {
        1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2, 1.0e-1, 1.0};
      std::array<std::size_t, rectangle_gaps.size()> rectangle_gap_excluded {};
      constexpr std::array<int, 3> alpha_arc_counts {64, 256, 4096};
      std::array<std::size_t, alpha_arc_counts.size()> alpha_arc_excluded {};
      std::size_t alpha_arc_zero_gap_unknown = 0;
      std::size_t alpha_arc_negative_unknown = 0;
      std::size_t zero_gap_unknown = 0;
      std::size_t negative_unknown = 0;
      std::size_t nodes = 0;
      for (std::size_t index = 0; index < surface.spans().size(); ++index) {
        const auto& span = surface.spans()[index];
        ++selected;
        const double scale = 1.0 / (span.angle_max - span.angle_min);
        const double upper_u = (span.angle_max - span.angle_min) * scale;
        const bool above_one_ulp = upper_u > up(1.0);
        u_endpoint_above_one_ulp += above_one_ulp;
        const auto prefix = analyze_span(span, origin, direction,
          dominant_axis, lead.distance - gap, true);
        const auto rectangle = analyze_span(span, origin, direction,
          dominant_axis, lead.distance - gap, false);
        std::array<bool, rectangle_gaps.size()> rectangle_gap_result {};
        SpanResult rectangle_last_gap;
        for (std::size_t i = 0; i < rectangle_gaps.size(); ++i) {
          const auto gap_result = analyze_span(span, origin, direction,
            dominant_axis, lead.distance - rectangle_gaps[i], false);
          rectangle_gap_result[i] = gap_result.undecided == 0;
          if (i + 1 == rectangle_gaps.size()) rectangle_last_gap = gap_result;
          rectangle_gap_excluded[i] += rectangle_gap_result[i];
        }
        const auto zero_gap = analyze_span(span, origin, direction,
          dominant_axis, lead.distance, true);
        const auto negative = analyze_span(span, origin, direction,
          dominant_axis, lead.distance + 4.0, true);
        std::array<bool, 3> slack_result {};
        constexpr std::array<double, 3> comparison_slacks {
          1.0e-10, 1.0e-8, 1.0e-6};
        for (std::size_t i = 0; i < comparison_slacks.size(); ++i) {
          unit_circle_slack = comparison_slacks[i];
          slack_result[i] = analyze_span(span, origin, direction,
            dominant_axis, lead.distance - gap, true).undecided == 0;
          slack_excluded[i] += slack_result[i];
        }
        constexpr std::array<double, 3> comparison_gaps {
          1.0e-11, 1.0e-8, 1.0e-5};
        constexpr std::array<double, 3> matrix_slacks {
          1.0e-12, 1.0e-8, 1.0e-6};
        std::array<std::array<bool, 3>, 3> matrix_result {};
        for (std::size_t g = 0; g < comparison_gaps.size(); ++g) {
          for (std::size_t s = 0; s < matrix_slacks.size(); ++s) {
            unit_circle_slack = matrix_slacks[s];
            matrix_result[g][s] = analyze_span(span, origin, direction,
              dominant_axis, lead.distance - comparison_gaps[g], true)
              .undecided == 0;
            gap_slack_excluded[g][s] += matrix_result[g][s];
          }
        }
        unit_circle_slack = 1.0e-6;
        const bool padded = analyze_span(span, origin, direction,
          dominant_axis, lead.distance - 1.0e-5, true,
          projection_slack).undecided == 0;
        const bool padded_zero_gap = analyze_span(span, origin, direction,
          dominant_axis, lead.distance, true,
          projection_slack).undecided != 0;
        const bool padded_negative = analyze_span(span, origin, direction,
          dominant_axis, lead.distance + 4.0, true,
          projection_slack).undecided != 0;
        std::array<bool, alpha_arc_counts.size()> arc_result {};
        for (std::size_t i = 0; i < alpha_arc_counts.size(); ++i) {
          arc_result[i] = analyze_span(span, origin, direction,
            dominant_axis, lead.distance - 1.0e-5, false,
            projection_slack, 36, 10000, alpha_arc_counts[i]).undecided == 0;
          alpha_arc_excluded[i] += arc_result[i];
        }
        const bool arc_zero_gap = analyze_span(span, origin, direction,
          dominant_axis, lead.distance, false, projection_slack,
          36, 10000, alpha_arc_counts.back()).undecided != 0;
        const bool arc_negative = analyze_span(span, origin, direction,
          dominant_axis, lead.distance + 4.0, false, projection_slack,
          36, 10000, alpha_arc_counts.back()).undecided != 0;
        alpha_arc_zero_gap_unknown += arc_zero_gap;
        alpha_arc_negative_unknown += arc_negative;
        padded_excluded += padded;
        padded_zero_gap_unknown += padded_zero_gap;
        padded_negative_unknown += padded_negative;
        unit_circle_slack = 1.0e-12;
        nodes += prefix.nodes;
        excluded_prefix += prefix.undecided == 0;
        rectangle_excluded += rectangle.undecided == 0;
        zero_gap_unknown += zero_gap.undecided != 0;
        negative_unknown += negative.undecided != 0;
        std::cout << "{\"kind\":\"span\",\"member\":" << member
                  << ",\"span\":" << index << ",\"nodes\":"
                  << prefix.nodes << ",\"prefix_excluded\":"
                  << (prefix.undecided == 0 ? "true" : "false")
                  << ",\"u_endpoint_above_one_ulp\":"
                  << (above_one_ulp ? "true" : "false")
                  << ",\"padded_excluded\":"
                  << (padded ? "true" : "false")
                  << ",\"padded_zero_gap_undecided\":"
                  << (padded_zero_gap ? "true" : "false")
                  << ",\"padded_negative_undecided\":"
                  << (padded_negative ? "true" : "false")
                  << ",\"rectangle_excluded\":"
                  << (rectangle.undecided == 0 ? "true" : "false")
                  << ",\"rectangle_nodes\":" << rectangle.nodes
                  << ",\"rectangle_gap_excluded\":[";
        for (std::size_t i = 0; i < rectangle_gap_result.size(); ++i) {
          if (i != 0) std::cout << ',';
          std::cout << (rectangle_gap_result[i] ? "true" : "false");
        }
        std::cout << ']'
                  << ",\"rectangle_last_gap_outcomes\":[";
        for (std::size_t i = 0; i < rectangle_last_gap.outcomes.size(); ++i) {
          if (i != 0) std::cout << ',';
          std::cout << rectangle_last_gap.outcomes[i];
        }
        std::cout << ']'
                  << ",\"rectangle_last_gap_undecided\":"
                  << rectangle_last_gap.undecided
                  << ",\"alpha_arc_excluded\":[";
        for (std::size_t i = 0; i < arc_result.size(); ++i) {
          if (i != 0) std::cout << ',';
          std::cout << (arc_result[i] ? "true" : "false");
        }
        std::cout << ']'
                  << ",\"alpha_arc_zero_gap_undecided\":"
                  << (arc_zero_gap ? "true" : "false")
                  << ",\"alpha_arc_negative_undecided\":"
                  << (arc_negative ? "true" : "false")
                  << ",\"slack_excluded\":["
                  << (slack_result[0] ? "true" : "false") << ','
                  << (slack_result[1] ? "true" : "false") << ','
                  << (slack_result[2] ? "true" : "false") << ']'
                  << ",\"gap_slack_excluded\":[";
        for (std::size_t g = 0; g < matrix_result.size(); ++g) {
          if (g != 0) std::cout << ',';
          std::cout << '[';
          for (std::size_t s = 0; s < matrix_result[g].size(); ++s) {
            if (s != 0) std::cout << ',';
            std::cout << (matrix_result[g][s] ? "true" : "false");
          }
          std::cout << ']';
        }
        std::cout << ']'
                  << ",\"zero_gap_undecided\":"
                  << (zero_gap.undecided != 0 ? "true" : "false")
                  << ",\"negative_control_undecided\":"
                  << (negative.undecided != 0 ? "true" : "false")
                  << "}\n";
      }
      std::cout << "{\"kind\":\"member_summary\",\"member\":"
                << member << ",\"lead_cm\":" << lead.distance
                << ",\"selected\":" << selected
                << ",\"u_endpoint_above_one_ulp\":"
                << u_endpoint_above_one_ulp
                << ",\"padded_excluded\":" << padded_excluded
                << ",\"padded_zero_gap_undecided\":"
                << padded_zero_gap_unknown
                << ",\"padded_negative_undecided\":"
                << padded_negative_unknown
                << ",\"projection_slack_cm\":" << projection_slack
                << ",\"prefix_excluded\":" << excluded_prefix
                << ",\"rectangle_excluded\":" << rectangle_excluded
                << ",\"rectangle_gap_excluded\":[";
      for (std::size_t i = 0; i < rectangle_gap_excluded.size(); ++i) {
        if (i != 0) std::cout << ',';
        std::cout << rectangle_gap_excluded[i];
      }
      std::cout << ']'
                << ",\"alpha_arc_excluded\":[";
      for (std::size_t i = 0; i < alpha_arc_excluded.size(); ++i) {
        if (i != 0) std::cout << ',';
        std::cout << alpha_arc_excluded[i];
      }
      std::cout << ']'
                << ",\"alpha_arc_zero_gap_undecided\":"
                << alpha_arc_zero_gap_unknown
                << ",\"alpha_arc_negative_undecided\":"
                << alpha_arc_negative_unknown
                << ",\"slack_excluded\":[" << slack_excluded[0] << ','
                << slack_excluded[1] << ',' << slack_excluded[2] << ']'
                << ",\"gap_slack_excluded\":[";
      for (std::size_t g = 0; g < gap_slack_excluded.size(); ++g) {
        if (g != 0) std::cout << ',';
        std::cout << '[';
        for (std::size_t s = 0; s < gap_slack_excluded[g].size(); ++s) {
          if (s != 0) std::cout << ',';
          std::cout << gap_slack_excluded[g][s];
        }
        std::cout << ']';
      }
      std::cout << ']'
                << ",\"zero_gap_undecided\":" << zero_gap_unknown
                << ",\"negative_control_undecided\":"
                << negative_unknown << ",\"nodes\":" << nodes
                << ",\"terminal_unresolved\":true}\n";
      if (selected == 0 || zero_gap_unknown == 0 || negative_unknown == 0
          || padded_zero_gap_unknown == 0 || padded_negative_unknown == 0)
        throw std::runtime_error("missing candidate or known-root control");
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "swept interval experiment: " << error.what() << '\n';
    return 1;
  }
}
