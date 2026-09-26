#include "stellarcsg/compiled_facet_surface_set.hpp"
#ifdef STELLARCSG_HAS_HDF5
#include "stellarcsg/facet_payload_file.hpp"
#endif

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

using stellarcsg::CompiledFacetSurfaceSet;
using stellarcsg::FacetTriangle;
using stellarcsg::Vec3;

namespace {

void require(bool condition, const char* message)
{
  if (!condition) throw std::runtime_error(message);
}

void face(std::vector<FacetTriangle>& triangles,
  Vec3 a, Vec3 b, Vec3 c, Vec3 d, int component)
{
  triangles.push_back({a, b, c, component});
  triangles.push_back({a, c, d, component});
}

std::vector<FacetTriangle> cube(double x0, int component)
{
  const double x1 = x0 + 1.0;
  const Vec3 p000 {x0, 0.0, 0.0};
  const Vec3 p001 {x0, 0.0, 1.0};
  const Vec3 p010 {x0, 1.0, 0.0};
  const Vec3 p011 {x0, 1.0, 1.0};
  const Vec3 p100 {x1, 0.0, 0.0};
  const Vec3 p101 {x1, 0.0, 1.0};
  const Vec3 p110 {x1, 1.0, 0.0};
  const Vec3 p111 {x1, 1.0, 1.0};
  std::vector<FacetTriangle> triangles;
  face(triangles, p000, p010, p110, p100, component); // -z
  face(triangles, p001, p101, p111, p011, component); // +z
  face(triangles, p000, p001, p011, p010, component); // -x
  face(triangles, p100, p110, p111, p101, component); // +x
  face(triangles, p000, p100, p101, p001, component); // -y
  face(triangles, p010, p011, p111, p110, component); // +y
  return triangles;
}

void accepted_fixture(const char* path)
{
  std::ifstream input {path};
  require(static_cast<bool>(input), "accepted facet fixture opened");
  std::size_t triangle_count = 0;
  input >> triangle_count;
  require(triangle_count == 3348, "accepted facet triangle count");
  std::map<int, std::vector<FacetTriangle>> groups;
  for (std::size_t index = 0; index < triangle_count; ++index) {
    FacetTriangle triangle;
    input >> triangle.component_id
      >> triangle.a.x >> triangle.a.y >> triangle.a.z
      >> triangle.b.x >> triangle.b.y >> triangle.b.z
      >> triangle.c.x >> triangle.c.y >> triangle.c.z;
    require(static_cast<bool>(input), "accepted facet triangle parsed");
    groups[triangle.component_id].push_back(triangle);
  }
  require(groups.size() == 18, "accepted facet component count");
  std::map<int, CompiledFacetSurfaceSet> surfaces;
  for (auto& item : groups)
    surfaces.emplace(item.first, CompiledFacetSurfaceSet {std::move(item.second)});
  std::size_t probe_count = 0;
  input >> probe_count;
  require(probe_count == 108, "accepted facet probe count");
  for (std::size_t index = 0; index < probe_count; ++index) {
    int component = -1;
    int expected_inside = -1;
    Vec3 point;
    input >> component >> expected_inside >> point.x >> point.y >> point.z;
    require(static_cast<bool>(input), "accepted facet probe parsed");
    const auto surface = surfaces.find(component);
    require(surface != surfaces.end(), "accepted facet component found");
    const auto inside = surface->second.contains(point);
    if (inside != (expected_inside == 1)) {
      throw std::runtime_error("accepted facet probe "
        + std::to_string(index) + " classified "
        + (inside ? (*inside ? "inside" : "outside") : "unresolved"));
    }
  }
}

} // namespace

int main()
{
  try {
    auto triangles = cube(0.0, 7);
    auto second = cube(3.0, 8);
    triangles.insert(triangles.end(), second.begin(), second.end());
    const CompiledFacetSurfaceSet surface {triangles};
    require(surface.triangle_count() == 24, "triangle count");
    require(surface.periodic_cap_count(0) == 2
      && surface.periodic_cap_count(1) == 4,
      "outward zero-plane cap counts");
    require(surface.contains({0.25, 0.31, 0.42}) == true,
      "first cube inside");
    require(surface.contains({3.25, 0.31, 0.42}) == true,
      "second cube inside");
    require(surface.contains({2.0, 0.31, 0.42}) == false,
      "gap outside");

    const auto first = surface.distance({-1.0, 0.31, 0.42},
      {1.0, 0.0, 0.0});
    require(first.found && !first.terminal_unresolved,
      "unambiguous nearest hit");
    require(first.component_id == 7 && std::abs(first.distance - 1.0) < 1e-12,
      "nearest hit distance and component");
    require(first.outward_normal.x < -0.999,
      "outward normal orientation");
    const auto face_normal = surface.normal_at({0.0, 0.31, 0.42});
    require(face_normal && face_normal->x < -0.999,
      "normal on unique face interior");
    const auto next_from_face = surface.distance(
      {0.0, 0.31, 0.42}, {1.0, 0.0, 0.0}, true);
    require(next_from_face.found && !next_from_face.terminal_unresolved
      && std::abs(next_from_face.distance - 1.0) < 1e-12,
      "coincident origin skips only zero-distance self hit");
    require(surface.normal_at({0.0, 0.5, 0.5}).has_value(),
      "coplanar triangle seam has shared normal");
    const auto scaled = surface.distance({-1.0, 0.31, 0.42},
      {4.0, 0.0, 0.0});
    require(scaled.found && std::abs(scaled.distance - 1.0) < 1e-12,
      "distance independent of direction scale");
    const auto cap_hit = surface.distance(
      {0.25, 0.31, 0.42}, {-1.0, 0.0, 0.0});
    const auto cap_delegated = surface.distance(
      {0.25, 0.31, 0.42}, {-1.0, 0.0, 0.0}, false, true, false);
    require(cap_hit.found && std::abs(cap_hit.distance - 0.25) < 1e-12
      && !cap_delegated.found && !cap_delegated.terminal_unresolved,
      "explicit x-cap delegation leaves parity geometry intact");

    const auto miss = surface.distance({-1.0, 2.0, 0.42},
      {1.0, 0.0, 0.0});
    require(!miss.found && !miss.terminal_unresolved,
      "resolved miss");

    const auto seam = surface.distance({-1.0, 0.5, 0.5},
      {1.0, 0.0, 0.0});
    require(seam.found && !seam.terminal_unresolved
      && std::abs(seam.distance - 1.0) < 1e-12
      && seam.outward_normal.x < -0.999,
      "coplanar triangulation seam has a unique crossing");
    const auto crease = surface.distance({-1.0, 0.0, 0.42},
      {1.0, 0.0, 0.0});
    require(crease.terminal_unresolved,
      "noncoplanar facet crease must fail closed");

    auto open = cube(0.0, 7);
    open.pop_back();
    bool rejected_open = false;
    try { (void) CompiledFacetSurfaceSet {open}; }
    catch (const std::invalid_argument&) { rejected_open = true; }
    require(rejected_open, "open component rejected");

    auto reversed = cube(0.0, 7);
    std::swap(reversed[0].b, reversed[0].c);
    bool rejected_reversed = false;
    try { (void) CompiledFacetSurfaceSet {reversed}; }
    catch (const std::invalid_argument&) { rejected_reversed = true; }
    require(rejected_reversed, "inconsistent orientation rejected");

    auto inward_shell = cube(0.0, 7);
    for (auto& triangle : inward_shell)
      std::swap(triangle.b, triangle.c);
    bool rejected_inward_shell = false;
    try { (void) CompiledFacetSurfaceSet {inward_shell}; }
    catch (const std::invalid_argument&) { rejected_inward_shell = true; }
    require(rejected_inward_shell, "globally inward winding rejected");

    const CompiledFacetSurfaceSet aligned_cap {cube(1e-13, 7)};
    const CompiledFacetSurfaceSet displaced_cap {cube(5e-11, 7)};
    require(aligned_cap.periodic_cap_count(0) == 2
      && displaced_cap.periodic_cap_count(0) == 0,
      "delegated cap must align within coincidence budget");

    if (const char* fixture = std::getenv("STELLARCSG_FACET_FIXTURE"))
      accepted_fixture(fixture);

#ifdef STELLARCSG_HAS_HDF5
    if (const char* payload = std::getenv("STELLARCSG_FACET_PAYLOAD")) {
      const char* expected = std::getenv("STELLARCSG_FACET_CONTENT_ID");
      require(expected != nullptr, "facet payload test requires expected ID");
      const auto data = stellarcsg::read_facet_payload_hdf5(
        payload, "/facets/one_period", expected);
      require(data.triangles.size() == 3348, "accepted payload triangle count");
      const CompiledFacetSurfaceSet loaded {data.triangles};
      require(loaded.triangle_count() == 3348,
        "accepted payload compiles as a closed oriented facet set");
      require(loaded.periodic_cap_count(0) == 80
        && loaded.periodic_cap_count(1) == 80,
        "accepted payload zero-plane caps identified");
    }
#endif

    std::cout << "facet surface tests passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
