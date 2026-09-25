#pragma once
#include "stellarcsg/compiled_swept_surface.hpp"
namespace stellarcsg {
using PeriodicSplineSurfaceData=SweptSplineSurfaceData;
class CompiledPeriodicSplineSurface : public CompiledSweptSplineSurface {
public:
  using CompiledSweptSplineSurface::CompiledSweptSplineSurface;
  DistanceResult distance(const Vec3& p,const Vec3& u,bool c,const RootSearchOptions& o={}) const {
    test_solver_path="layered";
    return CompiledSweptSplineSurface::distance(p,u,c,o);
  }
  DistanceResult distance_reference(const Vec3& p,const Vec3& u,bool c,const RootSearchOptions& o={}) const {
    test_solver_path="reference";
    return CompiledSweptSplineSurface::distance(p,u,c,o);
  }
};
}
