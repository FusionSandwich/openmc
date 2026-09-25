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
    const auto scaled = surface.distance({-1.0, 0.31, 0.42},
      {4.0, 0.0, 0.0});
    require(scaled.found && std::abs(scaled.distance - 1.0) < 1e-12,
      "distance independent of direction scale");

    const auto miss = surface.distance({-1.0, 2.0, 0.42},
      {1.0, 0.0, 0.0});
    require(!miss.found && !miss.terminal_unresolved,
      "resolved miss");

    const auto seam = surface.distance({-1.0, 0.5, 0.5},
      {1.0, 0.0, 0.0});
    require(seam.terminal_unresolved,
      "shared triangle edge must fail closed");

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
    }
#endif

    std::cout << "facet surface tests passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
