#include "stellarcsg/compiled_facet_surface_set.hpp"

#include <chrono>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>

using stellarcsg::CompiledFacetSurfaceSet;
using stellarcsg::FacetTriangle;
using stellarcsg::Vec3;

int main(int argc, char** argv)
{
  if (argc != 2) return 2;
  std::ifstream input {argv[1]};
  std::size_t triangle_count = 0;
  input >> triangle_count;
  if (triangle_count != 3348) return 3;
  std::map<int, std::vector<FacetTriangle>> groups;
  for (std::size_t i = 0; i < triangle_count; ++i) {
    FacetTriangle triangle;
    input >> triangle.component_id
      >> triangle.a.x >> triangle.a.y >> triangle.a.z
      >> triangle.b.x >> triangle.b.y >> triangle.b.z
      >> triangle.c.x >> triangle.c.y >> triangle.c.z;
    groups[triangle.component_id].push_back(triangle);
  }
  std::map<int, CompiledFacetSurfaceSet> surfaces;
  for (auto& [id, facets] : groups)
    surfaces.emplace(id, CompiledFacetSurfaceSet {std::move(facets)});
  std::size_t point_count = 0;
  input >> point_count;
  if (point_count != 108 || surfaces.size() != 18) return 4;
  std::vector<Vec3> points;
  for (std::size_t i = 0; i < point_count; ++i) {
    int component, expected;
    Vec3 point;
    input >> component >> expected >> point.x >> point.y >> point.z;
    points.push_back(point);
  }
  if (!input) return 5;

  std::size_t outside_bounds = 0;
  for (const auto& [id, surface] : surfaces) {
    (void) id;
    const auto& box = surface.bounding_box();
    for (const auto& point : points)
      outside_bounds += point.x < box.lower.x || point.x > box.upper.x
        || point.y < box.lower.y || point.y > box.upper.y
        || point.z < box.lower.z || point.z > box.upper.z;
  }
  constexpr int repeats = 100;
  std::size_t inside = 0, outside = 0, unresolved = 0;
  const auto start = std::chrono::steady_clock::now();
  for (int repeat = 0; repeat < repeats; ++repeat) {
    for (const auto& [id, surface] : surfaces) {
      (void) id;
      for (const auto& point : points) {
        const auto result = surface.contains(point);
        if (!result) ++unresolved;
        else if (*result) ++inside;
        else ++outside;
      }
    }
  }
  const double elapsed = std::chrono::duration<double>(
    std::chrono::steady_clock::now() - start).count();
  std::cout << "queries=" << repeats * point_count * surfaces.size()
            << " outside_bounds_per_sweep=" << outside_bounds
            << " inside=" << inside << " outside=" << outside
            << " unresolved=" << unresolved << " elapsed_s=" << elapsed
            << '\n';
}
