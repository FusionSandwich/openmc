#include "stellarcsg/compiled_facet_surface_set.hpp"

#include <iostream>
#include <vector>

using stellarcsg::CompiledFacetSurfaceSet;
using stellarcsg::FacetTriangle;
using stellarcsg::Vec3;

static void face(std::vector<FacetTriangle>& triangles,
  Vec3 a, Vec3 b, Vec3 c, Vec3 d)
{
  triangles.push_back({a, b, c, 7});
  triangles.push_back({a, c, d, 7});
}

int main()
{
  const Vec3 p000 {0, 0, 0}, p001 {0, 0, 1}, p010 {0, 1, 0},
    p011 {0, 1, 1}, p100 {1, 0, 0}, p101 {1, 0, 1},
    p110 {1, 1, 0}, p111 {1, 1, 1};
  std::vector<FacetTriangle> triangles;
  face(triangles, p000, p010, p110, p100);
  face(triangles, p001, p101, p111, p011);
  face(triangles, p000, p001, p011, p010);
  face(triangles, p100, p110, p111, p101);
  face(triangles, p000, p100, p101, p001);
  face(triangles, p010, p011, p111, p110);
  const CompiledFacetSurfaceSet surface {triangles};
  const Vec3 points[] {{-1e-13, 0.31, 0.42}, {1 + 1e-13, 0.31, 0.42},
    {0.31, -1e-13, 0.42}, {0.31, 1 + 1e-13, 0.42},
    {0.31, 0.42, -1e-13}, {0.31, 0.42, 1 + 1e-13}};
  for (int index = 0; index < 6; ++index) {
    const auto side = surface.contains(points[index]);
    const auto normal = surface.normal_at(points[index]);
    std::cout << index << ' ' << (side ? (*side ? "inside" : "outside") : "unresolved")
              << ' ' << (normal ? "normal" : "no-normal") << '\n';
  }
}
