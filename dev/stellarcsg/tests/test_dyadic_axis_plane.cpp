#include "stellarcsg/dyadic_axis_plane.hpp"

#include <cfenv>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace stellarcsg;

namespace {
void require(bool condition, const char* reason)
{
  if (!condition) throw std::runtime_error(reason);
}

double from_bits(std::uint64_t bits)
{
  double value;
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}

std::uint64_t bits(double value)
{
  std::uint64_t out;
  std::memcpy(&out, &value, sizeof(out));
  return out;
}

template<class F> void rejects(F operation)
{
  bool caught = false;
  try {
    operation();
  } catch (const std::invalid_argument&) {
    caught = true;
  }
  require(caught, "Invalid argument was accepted");
}

void controls()
{
  const double gap = std::ldexp(1.0, -48);
  const double next = std::nextafter(1.0, 2.0);
  UnitAxisRay reverse {{1.75 + gap, .31, .42}, 0, -1};
  auto b = axis_plane_contact(reverse, {0, 1.0 + gap});
  auto a = axis_plane_contact(reverse, {0, 1.0});
  require(b.status == AxisContactStatus::future, "B future contact missing");
  require(b.parameter.compare(a.parameter) < 0, "Positive gap became a tie");
  require(b.parameter.rounded().value == .75, "Wrong B exit parameter");
  require(a.parameter.rounded().value == .75 + gap, "Wrong A entry parameter");
  require(axis_plane_limit_side(reverse, 1.0 + gap, {0, 1.0}, true) == 1,
    "Nearby A was classified inside at B exit");
  require(axis_plane_limit_side(reverse, 1.0 + gap, {0, 1.0 + gap}, true) == -1,
    "B outgoing limit wrong");
  auto length = axis_interval_length(reverse, 1.0 + gap, 1.0);
  require(length.sign() == 1 && length.rounded().exact
      && length.rounded().value == gap, "Local gap length lost");
  require(axis_interval_length(reverse, 1.0, 1.0 + gap).sign() == -1,
    "Reversed progress was accepted");
  require(axis_interval_length(reverse, 1.0, 1.0).sign() == 0, "True tie nonzero");
  UnitAxisRay adjacent {{1.75, .31, .42}, 0, -1};
  auto left = axis_plane_contact(adjacent, {0, 1.0});
  auto right = axis_plane_contact(adjacent, {0, next});
  require(right.parameter.compare(left.parameter) < 0,
    "Adjacent-double contacts merged");
  require(std::nextafter(1.0, next) == next, "Adjacent fixture has an interior double");
  require(axis_interval_length(adjacent, next, 1.0).rounded().value
      == std::ldexp(1.0, -52), "No-interior-point interval lost");
  UnitAxisRay large {{-1e20, .31, .42}, 0, 1};
  left = axis_plane_contact(large, {0, 1.0});
  right = axis_plane_contact(large, {0, next});
  require(bits(left.parameter.rounded().value) == bits(right.parameter.rounded().value),
    "Rounded-equal absolute parameter fixture invalid");
  require(left.parameter.compare(right.parameter) < 0,
    "Rounded-equal absolute parameters treated as an exact tie");
  require(axis_interval_length(large, 1.0, next).rounded().value
      == std::ldexp(1.0, -52), "Rounded absolute subtraction lost delta");
  for (int axis = 0; axis < 3; ++axis) {
    for (int direction : {-1, 1}) {
      UnitAxisRay ray {{0., 0., 0.}, axis, direction};
      auto origin = axis_plane_contact(ray, {axis, -0.});
      require(origin.status == AxisContactStatus::origin, "Signed zero origin wrong");
      require(axis_plane_limit_side(ray, 0., {axis, 0.}, true) == direction,
        "Outgoing tied side wrong");
      require(axis_plane_limit_side(ray, 0., {axis, 0.}, false) == -direction,
        "Incoming tied side wrong");
      const int parallel_axis = (axis + 1) % 3;
      require(axis_plane_contact(ray, {parallel_axis, 0.}).status
          == AxisContactStatus::coplanar, "Coplanar contact resolved as a point");
      require(axis_plane_limit_side(ray, 0., {parallel_axis, 0.}, true) == 0,
        "Coplanar side resolved by direction");
      require(axis_plane_contact(ray, {parallel_axis, 1.}).status
          == AxisContactStatus::miss, "Parallel miss wrong");
      require(axis_plane_contact(ray, {axis, -static_cast<double>(direction)}).status
          == AxisContactStatus::behind, "Negative parameter clipped to origin");
    }
  }
  const auto subnormal = std::numeric_limits<double>::denorm_min();
  auto small = DyadicDifference::between(subnormal, 0.0);
  require(small.sign() == 1 && bits(small.rounded().value) == 1,
    "Minimum subnormal lost");
  auto big = DyadicDifference::between(std::numeric_limits<double>::max(),
    -std::numeric_limits<double>::max());
  require(big.rounded().status == DyadicRoundingStatus::overflow
      && !big.rounded().exact && big.sign() == 1, "Overflow converted to finite length");
  require(DyadicDifference::between(-0., 0.).sign() == 0, "Signed zero difference wrong");
  require(DyadicDifference::between(-4., -2.).compare(
      DyadicDifference::between(-2., -1.)) < 0, "Negative parameter ordering wrong");
  rejects([] { DyadicDifference::between(INFINITY, 0.); });
  rejects([] { DyadicDifference::between(0., NAN); });
  rejects([] { UnitAxisRay ray {{0., 0., 0.}, 3, 1}; });
  rejects([] { UnitAxisRay ray {{0., 0., 0.}, 0, 0}; });
  rejects([] { UnitAxisRay ray {{INFINITY, 0., 0.}, 0, 1}; });
  rejects([&] { axis_plane_contact(reverse, {3, 1.}); });
  rejects([&] { strict_axis_plane_side(reverse, NAN, {0, 1.}); });
}

void query_stream()
{
  std::string first, second;
  while (std::cin >> first >> second) {
    try {
      auto value = DyadicDifference::between(from_bits(std::stoull(first, nullptr, 16)),
        from_bits(std::stoull(second, nullptr, 16)));
      auto rounded = value.rounded();
      std::cout << std::dec << value.sign() << ' ';
      bool started = false;
      for (std::size_t i = value.magnitude().size(); i-- > 0;) {
        const auto word = value.magnitude()[i];
        if (!started && !word) continue;
        if (started) std::cout << std::setw(16) << std::setfill('0');
        std::cout << std::hex << word;
        started = true;
      }
      if (!started) std::cout << '0';
      std::cout << ' ' << std::hex << bits(rounded.value) << ' ' << std::dec
                << (rounded.status == DyadicRoundingStatus::overflow) << ' '
                << rounded.exact << '\n';
    } catch (const std::invalid_argument&) {
      std::cout << "INVALID\n";
    }
  }
  if (!std::cin.eof()) throw std::runtime_error("Malformed query stream");
}
} // namespace

int main(int argc, char** argv)
{
  try {
    if (argc == 2 && std::string(argv[1]) == "--query") {
      query_stream();
    } else if (argc == 1) {
      for (int mode : {FE_TONEAREST, FE_DOWNWARD, FE_UPWARD, FE_TOWARDZERO}) {
        require(std::fesetround(mode) == 0, "Floating environment mode unavailable");
        // Non-integer fixture construction belongs to the nearest mode;
        // verify integer-backed rounding separately in all four modes.
        const auto rounded = DyadicDifference::between(1., -std::ldexp(1., -53)).rounded();
        require(bits(rounded.value) == bits(1.) && !rounded.exact,
          "Nearest-even depends on caller floating rounding mode");
      }
      std::fesetround(FE_TONEAREST);
      controls();
      std::cout << "PASS dyadic axis-plane controls\n";
    } else {
      return 2;
    }
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
