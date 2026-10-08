#ifndef OPENMC_AXIS_PLANE_CONTEXT_H
#define OPENMC_AXIS_PLANE_CONTEXT_H

#include <array>
#include <cstdint>
#include "openmc/vector.h"
#include "stellarcsg/dyadic_axis_plane.hpp"

namespace openmc {
struct AxisPlaneContext {
  uint64_t epoch {0};
  bool valid {false};
  bool pending {false};
  bool advanced {false};
  std::array<double, 3> anchor {};
  int axis {0};
  int direction {1};
  double coordinate {0.0}; // committed/consumed coordinate in this epoch
  double event_coordinate {0.0};
  stellarcsg::DyadicDifference parameter {}; // exact anchor -> pending event
  vector<int> contacts; // unsigned native indices, deduplicated, ID sorted
  vector<int> outgoing_sides; // complete strict sides at pending event
  int owner {-1};
  int successor {-1};
  int vacuum_surface {-1};
  int representative {0};
  double length {0.0};

  void reset()
  {
    ++epoch;
    valid = pending = advanced = false;
    contacts.clear();
    outgoing_sides.clear();
  }
};
} // namespace openmc
#endif
