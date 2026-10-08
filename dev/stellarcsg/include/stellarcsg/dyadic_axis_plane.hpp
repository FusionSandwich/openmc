#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace stellarcsg {

enum class DyadicRoundingStatus { finite, overflow };

struct RoundedDyadic {
  double value;
  DyadicRoundingStatus status;
  bool exact;
};

// Exact difference of two finite IEEE binary64 values, in units of 2^-1074.
// Maximum magnitude <2^2099 units; 33 words (2112 bits) suffice. No heap use.
class DyadicDifference {
public:
  static constexpr std::size_t word_count = 33;
  static DyadicDifference between(double end, double begin);
  int sign() const { return sign_; }
  int compare(const DyadicDifference& other) const;
  RoundedDyadic rounded() const;
  const std::array<std::uint64_t, word_count>& magnitude() const
  {
    return magnitude_;
  }

private:
  std::array<std::uint64_t, word_count> magnitude_ {};
  int sign_ {0};
};

struct AxisPlane {
  int axis;
  double offset;
};

class UnitAxisRay {
public:
  UnitAxisRay(std::array<double, 3> anchor, int axis, int direction);
  const std::array<double, 3>& anchor() const { return anchor_; }
  int axis() const { return axis_; }
  int direction() const { return direction_; }

private:
  std::array<double, 3> anchor_;
  int axis_;
  int direction_;
};

enum class AxisContactStatus { future, origin, behind, miss, coplanar };

struct AxisContact {
  AxisContactStatus status;
  DyadicDifference parameter;
};

// Parameters are lengths for the declared unit axis ray; equality is exact.
AxisContact axis_plane_contact(const UnitAxisRay& ray, AxisPlane plane);

// Side of the logical event point whose varying coordinate is event_coordinate.
// -1 / 0 / +1 denote negative / exactly on / positive plane side. No tolerance.
int strict_axis_plane_side(
  const UnitAxisRay& ray, double event_coordinate, AxisPlane plane);

// One-sided limits. Coplanar probes return 0: they are not resolved by direction.
int axis_plane_limit_side(const UnitAxisRay& ray, double event_coordinate,
  AxisPlane plane, bool after);

// Local interval from coordinate to coordinate, not rounded absolute t1-t0.
// Sign <0 rejects reversed progress at the caller; sign 0 denotes a true tie.
DyadicDifference axis_interval_length(
  const UnitAxisRay& ray, double begin_coordinate, double end_coordinate);

} // namespace stellarcsg
