#include "stellarcsg/dyadic_axis_plane.hpp"

#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

#ifdef __FAST_MATH__
#error "Dyadic axis-plane finite validation requires fast-math disabled"
#endif

namespace stellarcsg {
namespace {

using Words = std::array<std::uint64_t, DyadicDifference::word_count>;
static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559
  && std::numeric_limits<double>::digits == 53
  && std::numeric_limits<double>::max_exponent == 1024,
  "Dyadic axis planes require IEEE binary64");

std::uint64_t bits(double value)
{
  std::uint64_t out;
  std::memcpy(&out, &value, sizeof(out));
  return out;
}

double from_bits(std::uint64_t value)
{
  double out;
  std::memcpy(&out, &value, sizeof(out));
  return out;
}

Words decode(double value)
{
  if (!std::isfinite(value))
    throw std::invalid_argument("Dyadic operand must be finite");
  Words result {};
  const auto raw = bits(value);
  const auto exponent = (raw >> 52) & 0x7ff;
  auto mantissa = raw & ((std::uint64_t {1} << 52) - 1);
  if (exponent) mantissa |= std::uint64_t {1} << 52;
  const unsigned shift = exponent ? static_cast<unsigned>(exponent - 1) : 0;
  const auto word = shift / 64;
  const auto offset = shift % 64;
  result[word] = mantissa << offset;
  if (offset) result[word + 1] = mantissa >> (64 - offset);
  return result;
}

int compare_words(const Words& a, const Words& b)
{
  for (std::size_t i = a.size(); i-- > 0;) {
    if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
  }
  return 0;
}

Words add_words(const Words& a, const Words& b)
{
  Words result {};
  std::uint64_t carry = 0;
  for (std::size_t i = 0; i < a.size(); ++i) {
    const auto sum = a[i] + b[i];
    const auto first_carry = sum < a[i];
    result[i] = sum + carry;
    carry = first_carry || result[i] < sum;
  }
  // Finite binary64 differences cannot exhaust 2112 bits.
  if (carry) throw std::overflow_error("Dyadic magnitude capacity exhausted");
  return result;
}

Words subtract_words(const Words& a, const Words& b)
{
  Words result {};
  std::uint64_t borrow = 0;
  for (std::size_t i = 0; i < a.size(); ++i) {
    const auto difference = a[i] - b[i];
    const auto first_borrow = a[i] < b[i];
    result[i] = difference - borrow;
    borrow = first_borrow || difference < borrow;
  }
  if (borrow) throw std::logic_error("Dyadic subtraction order violated");
  return result;
}

bool bit_at(const Words& value, unsigned index)
{
  return (value[index / 64] >> (index % 64)) & 1;
}

bool any_below(const Words& value, unsigned count)
{
  for (unsigned i = 0; i < count / 64; ++i)
    if (value[i]) return true;
  const auto remainder = count % 64;
  return remainder && (value[count / 64]
    & ((std::uint64_t {1} << remainder) - 1));
}

std::uint64_t shifted_low(const Words& value, unsigned shift)
{
  const auto word = shift / 64;
  const auto offset = shift % 64;
  auto out = value[word] >> offset;
  if (offset && word + 1 < value.size())
    out |= value[word + 1] << (64 - offset);
  return out;
}

void validate_plane(AxisPlane plane)
{
  if (plane.axis < 0 || plane.axis > 2 || !std::isfinite(plane.offset))
    throw std::invalid_argument("Axis plane requires axis 0..2 and finite offset");
}

} // namespace

DyadicDifference DyadicDifference::between(double end, double begin)
{
  const auto a = decode(end);
  const auto b = decode(begin);
  DyadicDifference out;
  const bool negative_a = std::signbit(end);
  const bool negative_b = std::signbit(begin);
  if (negative_a != negative_b) {
    out.magnitude_ = add_words(a, b);
    out.sign_ = negative_a ? -1 : 1;
  } else {
    const int order = compare_words(a, b);
    if (!order) return out;
    out.magnitude_ = order > 0 ? subtract_words(a, b) : subtract_words(b, a);
    out.sign_ = negative_a ? -order : order;
  }
  if (compare_words(out.magnitude_, Words {}) == 0) out.sign_ = 0;
  return out;
}

int DyadicDifference::compare(const DyadicDifference& other) const
{
  if (sign_ != other.sign_) return sign_ < other.sign_ ? -1 : 1;
  return sign_ * compare_words(magnitude_, other.magnitude_);
}

RoundedDyadic DyadicDifference::rounded() const
{
  if (!sign_) return {0.0, DyadicRoundingStatus::finite, true};
  unsigned highest = 0;
  for (std::size_t i = magnitude_.size(); i-- > 0;) {
    if (!magnitude_[i]) continue;
    auto word = magnitude_[i];
    highest = static_cast<unsigned>(64 * i);
    while (word >>= 1) ++highest;
    break;
  }
  const auto sign_bit = sign_ < 0 ? std::uint64_t {1} << 63 : 0;
  if (highest < 52)
    return {from_bits(sign_bit | magnitude_[0]), DyadicRoundingStatus::finite, true};
  const auto shift = highest - 52;
  auto mantissa = shifted_low(magnitude_, shift);
  const bool discarded = any_below(magnitude_, shift);
  if (shift && bit_at(magnitude_, shift - 1)
      && (any_below(magnitude_, shift - 1) || (mantissa & 1))) {
    ++mantissa;
    if (mantissa == (std::uint64_t {1} << 53)) {
      mantissa >>= 1;
      ++highest;
    }
  }
  const auto exponent = highest - 51;
  if (exponent >= 2047)
    return {from_bits(sign_bit | (std::uint64_t {0x7ff} << 52)),
      DyadicRoundingStatus::overflow, false};
  const auto raw = sign_bit | (static_cast<std::uint64_t>(exponent) << 52)
    | (mantissa & ((std::uint64_t {1} << 52) - 1));
  return {from_bits(raw), DyadicRoundingStatus::finite, !discarded};
}

UnitAxisRay::UnitAxisRay(std::array<double, 3> anchor, int axis, int direction)
  : anchor_ {anchor}, axis_ {axis}, direction_ {direction}
{
  if (axis < 0 || axis > 2 || (direction != -1 && direction != 1))
    throw std::invalid_argument("Unit axis ray requires axis 0..2 and direction +/-1");
  for (double coordinate : anchor)
    if (!std::isfinite(coordinate))
      throw std::invalid_argument("Unit axis ray requires finite anchor");
}

AxisContact axis_plane_contact(const UnitAxisRay& ray, AxisPlane plane)
{
  validate_plane(plane);
  if (plane.axis != ray.axis()) {
    return {DyadicDifference::between(ray.anchor()[plane.axis], plane.offset).sign() == 0
        ? AxisContactStatus::coplanar : AxisContactStatus::miss, {}};
  }
  auto parameter = axis_interval_length(ray, ray.anchor()[ray.axis()], plane.offset);
  const auto status = parameter.sign() > 0 ? AxisContactStatus::future
    : parameter.sign() < 0 ? AxisContactStatus::behind : AxisContactStatus::origin;
  return {status, parameter};
}

int strict_axis_plane_side(
  const UnitAxisRay& ray, double event_coordinate, AxisPlane plane)
{
  validate_plane(plane);
  if (!std::isfinite(event_coordinate))
    throw std::invalid_argument("Event coordinate must be finite");
  const double coordinate = plane.axis == ray.axis()
    ? event_coordinate : ray.anchor()[plane.axis];
  return DyadicDifference::between(coordinate, plane.offset).sign();
}

int axis_plane_limit_side(const UnitAxisRay& ray, double event_coordinate,
  AxisPlane plane, bool after)
{
  const int side = strict_axis_plane_side(ray, event_coordinate, plane);
  if (side || plane.axis != ray.axis()) return side;
  return after ? ray.direction() : -ray.direction();
}

DyadicDifference axis_interval_length(
  const UnitAxisRay& ray, double begin_coordinate, double end_coordinate)
{
  return ray.direction() > 0
    ? DyadicDifference::between(end_coordinate, begin_coordinate)
    : DyadicDifference::between(begin_coordinate, end_coordinate);
}

} // namespace stellarcsg
