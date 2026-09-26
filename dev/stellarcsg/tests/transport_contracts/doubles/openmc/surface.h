#pragma once
#include <hdf5.h>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
namespace pugi {
struct xml_node { std::map<std::string, std::string> attrs; };
}
namespace openmc {
struct Position { double x, y, z; };
using Direction = Position;
struct BoundingBox {
  Position min, max;
  static BoundingBox infinite() {
    const auto f=std::numeric_limits<double>::infinity();
    return {{-f,-f,-f},{f,f,f}};
  }
};
class Surface {
public:
  explicit Surface(const pugi::xml_node& n) : id_(std::stoi(n.attrs.at("id"))) {}
  virtual ~Surface() = default;
  virtual double evaluate(Position) const=0;
  virtual double distance(Position, Direction, bool) const=0;
  virtual Direction normal(Position) const=0;
  virtual BoundingBox bounding_box(bool) const=0;
  virtual void to_hdf5_inner(hid_t) const=0;
protected:
  int id_;
};
}
