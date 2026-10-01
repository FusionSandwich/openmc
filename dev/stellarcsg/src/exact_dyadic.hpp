#ifndef STELLARCSG_EXACT_DYADIC_HPP
#define STELLARCSG_EXACT_DYADIC_HPP

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>

namespace stellarcsg::offset_detail {
static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559 &&
                std::numeric_limits<double>::radix == 2 &&
                std::numeric_limits<double>::digits == 53 &&
                std::numeric_limits<double>::max_exponent == 1024,
  "Exact dyadic certificates require IEEE binary64 double storage");

// Signed multiples of 2^-1074. A finite binary64 input occupies at most 2098
// bits; 2304 bits leave headroom for all small integer sums used by the support
// certificate. Overflow invalidates the predicate instead of truncating it.
class ExactDyadic {
public:
  bool valid() const noexcept { return valid_; }
  bool zero() const noexcept
  {
    for (const auto limb : limbs_)
      if (limb != 0)
        return false;
    return true;
  }
  void add_double(double value, int weight = 1)
  {
    ExactDyadic term;
    std::uint64_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    const auto exponent = static_cast<unsigned>((bits >> 52) & 0x7ff);
    if (exponent == 0x7ff || weight < -16 || weight > 16) {
      valid_ = false;
      return;
    }
    std::uint64_t significand = bits & ((std::uint64_t(1) << 52) - 1);
    if (exponent != 0)
      significand |= std::uint64_t(1) << 52;
    const unsigned shift = exponent == 0 ? 0 : exponent - 1;
    const unsigned index = shift / 64, offset = shift % 64;
    term.limbs_[index] = significand << offset;
    if (offset != 0)
      term.limbs_[index + 1] = significand >> (64 - offset);
    term.negative_ = ((bits >> 63) != 0) != (weight < 0);
    term.multiply_small(static_cast<unsigned>(weight < 0 ? -weight : weight));
    add(term);
  }
  void negate() noexcept
  {
    if (!zero())
      negative_ = !negative_;
  }
  int compare(const ExactDyadic& other) const noexcept
  {
    if (zero() && other.zero())
      return 0;
    if (negative_ != other.negative_)
      return negative_ ? -1 : 1;
    const int magnitude = compare_magnitude(other);
    return negative_ ? -magnitude : magnitude;
  }
  bool interval(long double& lower, long double& upper) const
  {
    if (!valid_ || std::numeric_limits<long double>::digits < 64)
      return false;
    lower = upper = 0;
    bool first = true;
    for (std::size_t i = limbs_.size(); i-- != 0;) {
      if (limbs_[i] == 0)
        continue;
      // uint64 -> binary80 is exact with its 64-bit significand. Scaling by
      // a power of two is exact in the admitted normal exponent range.
      const auto piece = std::ldexp(
        static_cast<long double>(limbs_[i]), static_cast<int>(64 * i) - 1074);
      if (!std::isfinite(piece))
        return false;
      if (first) {
        lower = upper = piece;
        first = false;
      } else {
        lower = std::nextafter(
          lower + piece, -std::numeric_limits<long double>::infinity());
        upper = std::nextafter(
          upper + piece, std::numeric_limits<long double>::infinity());
      }
    }
    if (negative_) {
      const auto old_lower = lower;
      lower = -upper;
      upper = -old_lower;
    }
    return std::isfinite(lower) && std::isfinite(upper);
  }

private:
  std::array<std::uint64_t, 36> limbs_ {};
  bool negative_ {false};
  bool valid_ {true};
  int compare_magnitude(const ExactDyadic& other) const noexcept
  {
    for (std::size_t i = limbs_.size(); i-- != 0;)
      if (limbs_[i] != other.limbs_[i])
        return limbs_[i] < other.limbs_[i] ? -1 : 1;
    return 0;
  }
  void multiply_small(unsigned factor)
  {
    std::uint64_t carry = 0;
    for (auto& limb : limbs_) {
      const std::uint64_t low = (limb & 0xffffffffULL) * factor + carry;
      const std::uint64_t high = (limb >> 32) * factor + (low >> 32);
      limb = (high << 32) | (low & 0xffffffffULL);
      carry = high >> 32;
    }
    if (carry != 0)
      valid_ = false;
    if (zero())
      negative_ = false;
  }
  void subtract_magnitude(const ExactDyadic& smaller)
  {
    std::uint64_t borrow = 0;
    for (std::size_t i = 0; i < limbs_.size(); ++i) {
      const auto subtrahend = smaller.limbs_[i] + borrow;
      const bool overflow = subtrahend < smaller.limbs_[i];
      const auto previous = limbs_[i];
      limbs_[i] = previous - subtrahend;
      borrow = overflow || previous < subtrahend;
    }
    if (borrow != 0)
      valid_ = false;
    if (zero())
      negative_ = false;
  }
  void add(const ExactDyadic& other)
  {
    if (!valid_ || !other.valid_) {
      valid_ = false;
      return;
    }
    if (negative_ != other.negative_) {
      const int magnitude = compare_magnitude(other);
      if (magnitude >= 0)
        subtract_magnitude(other);
      else {
        const auto smaller = *this;
        *this = other;
        subtract_magnitude(smaller);
      }
      return;
    }
    std::uint64_t carry = 0;
    for (std::size_t i = 0; i < limbs_.size(); ++i) {
      const auto previous = limbs_[i];
      const auto partial = previous + other.limbs_[i];
      const bool carry1 = partial < previous;
      const auto total = partial + carry;
      const bool carry2 = total < partial;
      limbs_[i] = total;
      carry = carry1 || carry2;
    }
    if (carry != 0)
      valid_ = false;
  }
};
} // namespace stellarcsg::offset_detail
#endif
