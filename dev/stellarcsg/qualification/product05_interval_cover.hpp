#ifndef STELLARCSG_PRODUCT05_INTERVAL_COVER_HPP
#define STELLARCSG_PRODUCT05_INTERVAL_COVER_HPP

// Experimental exclusion only. A retained box is NOT evidence of root existence.
#include "stellarcsg/compiled_swept_surface.hpp"
#include <algorithm>
#include <array>
#include <cfenv>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace product05 {
constexpr double infinity = std::numeric_limits<double>::infinity();
struct I {
  double lo = 0, hi = 0;
  I() = default;
  I(double v) : I(v,v) {}
  I(double l, double h) : lo(l), hi(h) {
    if (std::isnan(l) || std::isnan(h) || l>h) {lo=-infinity;hi=infinity;}
  }
};
inline double down(double x) { return std::nextafter(x, -infinity); }
inline double up(double x) { return std::nextafter(x, infinity); }
inline I operator+(I a, I b) { return {down(a.lo+b.lo), up(a.hi+b.hi)}; }
inline I operator-(I a, I b) { return {down(a.lo-b.hi), up(a.hi-b.lo)}; }
inline I operator*(I a, I b)
{
  const std::array<double,4> v {a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};
  if (std::any_of(v.begin(),v.end(),[](double x){return std::isnan(x);}))
    return {-infinity,infinity};
  return {down(*std::min_element(v.begin(),v.end())),
          up(*std::max_element(v.begin(),v.end()))};
}
inline I divide(I a, double b)
{
  if (b == 0 || !std::isfinite(b)) throw std::invalid_argument("interval divisor");
  if (b > 0) return {down(a.lo/b),up(a.hi/b)};
  return {down(a.hi/b),up(a.lo/b)};
}
inline I square(I a)
{
  const double upper = up(std::max(a.lo*a.lo,a.hi*a.hi));
  return {a.lo <= 0 && a.hi >= 0 ? 0 :
    std::max(0.0,down(std::min(a.lo*a.lo,a.hi*a.hi))), upper};
}
inline bool excludes_zero(I a) { return a.lo > 0 || a.hi < 0; }
using Cubic = std::array<I,4>;
using Curve = std::array<Cubic,3>;
inline void environment()
{
#ifdef __FAST_MATH__
  throw std::runtime_error("UNSUPPORTED_ENVIRONMENT: fast math");
#endif
  if (!std::numeric_limits<double>::is_iec559 || std::fegetround()!=FE_TONEAREST)
    throw std::runtime_error("UNSUPPORTED_ENVIRONMENT: rounding");
  volatile double tiny=std::numeric_limits<double>::min(), one=1;
  volatile double half=tiny*.5, denorm=std::numeric_limits<double>::denorm_min();
  volatile double restored=half*2, subnormal=denorm*one;
  if (half==0 || restored!=tiny || subnormal==0)
    throw std::runtime_error("UNSUPPORTED_ENVIRONMENT: subnormal flushing");
}
inline I hull(const Cubic& p)
{
  I out=p[0];
  for (auto v:p) {out.lo=std::min(out.lo,v.lo);out.hi=std::max(out.hi,v.hi);}
  return out;
}
inline std::pair<Curve,Curve> split(const Curve& curve)
{
  Curve left{},right{};
  for (int a=0;a<3;++a) {
    auto p=curve[a]; left[a][0]=p[0];right[a][3]=p[3];
    for (int level=1;level<=3;++level) {
      for (int i=0;i<=3-level;++i) p[i]=(p[i]+p[i+1])*I(.5);
      left[a][level]=p[0];right[a][3-level]=p[3-level];
    }
  }
  return {left,right};
}
class StationaryTube {
  std::vector<Curve> curves_;
  double radius_;
  StationaryTube(std::vector<Curve> c,double r):curves_(std::move(c)),radius_(r){}
  friend StationaryTube compile(const stellarcsg::SweptSplineSurfaceData&);
public:
  const std::vector<Curve>& curves() const {return curves_;}
  double radius() const {return radius_;}
};
inline StationaryTube compile(const stellarcsg::SweptSplineSurfaceData& d)
{
  environment();
  if (d.sample_count<4 || d.centerline_coefficients.size()!=3*d.sample_count
      || d.major_radius_coefficients.size()!=d.sample_count
      || d.minor_radius_coefficients.size()!=d.sample_count)
    throw std::invalid_argument("UNSUPPORTED_GEOMETRY: coefficient shape");
  const double r=d.major_radius_coefficients[0];
  if (!(r>0) || !std::isfinite(r))
    throw std::invalid_argument("UNSUPPORTED_GEOMETRY: radius");
  for (const auto* values:{&d.major_radius_coefficients,&d.minor_radius_coefficients})
    for (double v:*values) if (v!=r)
      throw std::invalid_argument("UNSUPPORTED_GEOMETRY: nonconstant circular section");
  std::vector<Curve> curves(d.sample_count);
  for (std::size_t i=0;i<d.sample_count;++i) for (int a=0;a<3;++a) {
    std::array<I,4> p;
    for (int k=0;k<4;++k) {
      const double v=d.centerline_coefficients[3*((i+d.sample_count+k-1)%d.sample_count)+a];
      if (!std::isfinite(v)) throw std::invalid_argument("nonfinite control");
      p[k]=I(v);
    }
    curves[i][a]={divide(p[0]+I(4)*p[1]+p[2],6),
      divide(I(2)*p[1]+p[2],3),divide(p[1]+I(2)*p[2],3),
      divide(p[1]+I(4)*p[2]+p[3],6)};
  }
  return StationaryTube(std::move(curves),r);
}
struct Cover {
  bool root_free=false;
  std::size_t nodes=0, excluded=0, possible=0;
  double earliest_possible=infinity;
};
struct Node { Curve c; I t; int depth=0; };
inline Cover cover(const StationaryTube& tube,
  stellarcsg::Vec3 origin,stellarcsg::Vec3 direction,std::size_t budget=256)
{
  environment();
  const auto& curves=tube.curves();
  const auto radius=tube.radius();
  const std::array<double,3> o {origin.x,origin.y,origin.z},
    d {direction.x,direction.y,direction.z};
  bool nonzero=false;
  for(int a=0;a<3;++a) {
    if (!std::isfinite(o[a]) || !std::isfinite(d[a]))
      throw std::invalid_argument("nonfinite ray");
    nonzero=nonzero||d[a]!=0;
  }
  if (!nonzero) throw std::invalid_argument("zero direction");
  Cover result;
  std::vector<Node> pending;
  // Coarse per-span convex hull only; this prototype does not use the old
  // floating AABBs because their rounding is not an exclusion certificate.
  for (const auto& c:curves) {
    I t {0,infinity}; bool miss=false;
    for(int a=0;a<3;++a) {
      const I box=hull(c[a])+I(-radius,radius);
      if(d[a]==0) {if(o[a]<box.lo || o[a]>box.hi) miss=true;}
      else {const I slab=divide(box-I(o[a]),d[a]);
        t.lo=std::max(t.lo,slab.lo);t.hi=std::min(t.hi,slab.hi);}
    }
    if (miss || t.lo>t.hi) ++result.excluded;
    else pending.push_back({c,t,0});
  }
  while(!pending.empty() && result.nodes<budget) {
    const auto n=pending.back();pending.pop_back();++result.nodes;
    I f,g=I(0)-square(I(radius)); double spatial=0;
    for(int a=0;a<3;++a) {
      const I c=hull(n.c[a]);
      I derivative=(n.c[a][1]-n.c[a][0])*I(3);
      for(int k=1;k<3;++k) {const I v=(n.c[a][k+1]-n.c[a][k])*I(3);
        derivative.lo=std::min(derivative.lo,v.lo);
        derivative.hi=std::max(derivative.hi,v.hi);}
      const I radial=I(o[a])+n.t*I(d[a])-c;
      f=f+radial*derivative;g=g+square(radial);
      spatial=std::max(spatial,c.hi-c.lo);
    }
    if(excludes_zero(f)||excludes_zero(g)) {++result.excluded;continue;}
    const double middle=n.t.lo+(n.t.hi-n.t.lo)*.5;
    if(n.depth>=32 || !(middle>n.t.lo && middle<n.t.hi)) {
      ++result.possible;result.earliest_possible=std::min(result.earliest_possible,n.t.lo);
      continue;
    }
    const double travel=(n.t.hi-n.t.lo)*std::max({std::abs(d[0]),std::abs(d[1]),std::abs(d[2])});
    if(travel>spatial) {
      pending.push_back({n.c,{middle,n.t.hi},n.depth+1});
      pending.push_back({n.c,{n.t.lo,middle},n.depth+1});
    } else {
      const auto children=split(n.c);
      pending.push_back({children.second,n.t,n.depth+1});
      pending.push_back({children.first,n.t,n.depth+1});
    }
  }
  for(const auto& n:pending) {
    ++result.possible;result.earliest_possible=std::min(result.earliest_possible,n.t.lo);
  }
  result.root_free=result.possible==0;
  return result;
}
} // namespace product05
#endif
