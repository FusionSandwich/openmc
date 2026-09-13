#include "stellarcsg/compiled_swept_surface.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

namespace {
using stellarcsg::Vec3;
constexpr double pi=3.1415926535897932384626433832795;
int failures=0;
void check(bool pass,const std::string& label)
{ if (!pass) { ++failures; std::cerr<<"FAIL: "<<label<<'\n'; } }
stellarcsg::SweptSplineSurfaceData fixture(double amplitude,std::size_t n=64)
{
  stellarcsg::SweptSplineSurfaceData data;
  data.coil_id=71; data.sample_count=n; data.length=10*pi;
  data.characteristic_length=9;
  data.major_radius_coefficients.assign(n,0.25);
  data.minor_radius_coefficients.assign(n,0.25);
  for (std::size_t i=0;i<n;++i) {
    const double q=2*pi*static_cast<double>(i)/static_cast<double>(n);
    for (double value:{5*std::cos(q),5*std::sin(q),amplitude*std::sin(3*q)})
      data.centerline_coefficients.push_back(value);
    for (double value:{0.,0.,1.}) data.normal_coefficients.push_back(value);
    for (double value:{1.,0.,0.}) data.binormal_coefficients.push_back(value);
  }
  return data;
}
Vec3 knot(const stellarcsg::SweptSplineSurfaceData& data,std::size_t i)
{
  Vec3 value;
  for (int offset=-1;offset<=1;++offset) {
    const auto n=static_cast<long>(data.sample_count);
    const auto index=static_cast<std::size_t>((static_cast<long>(i)+offset+n)%n);
    const double weight=offset==0?4./6:1./6;
    value+=weight*Vec3{data.centerline_coefficients[3*index],
      data.centerline_coefficients[3*index+1],data.centerline_coefficients[3*index+2]};
  }
  return value;
}
Vec3 rotate(Vec3 p) { return {0.6*p.x-0.8*p.z,p.y,0.8*p.x+0.6*p.z}; }
template<class F> void must_throw(F operation,const std::string& label)
{
  try { operation(); check(false,label); }
  catch (const std::exception& e) { std::cout<<"EXPLICIT_REJECTION "<<label<<": "<<e.what()<<'\n'; }
}
}
int main()
{
  try {
    for (double amplitude:{0.0,0.4}) {
      const auto data=fixture(amplitude);
      const stellarcsg::CompiledSweptSplineSurface surface(data,true);
      check(!surface.exact_torus_specialization(),"forced general path remains enabled");
      const Vec3 center=knot(data,0);
      for (double scale:{1.,3.,1.0e-200,1.0e200}) {
        const auto hit=surface.distance(center+Vec3{.252,0,0},{-scale,0,0},false);
        check(hit.found&&std::abs(hit.distance-.002)<2e-9,"nearest entry inside capsule");
      }
      const auto inside=surface.distance(center,{1,0,0},false);
      check(inside.found&&std::abs(inside.distance-.25)<2e-9,"centerline start exits tube");
      const auto coincident=surface.distance(center+Vec3{.25,0,0},{-1,0,0},true);
      check(coincident.found&&std::abs(coincident.distance-.5)<2e-9,"coincident next boundary");
      const Vec3 entry_origin=center+Vec3{.252,.031,.017};
      const Vec3 entry_direction{-1,0,0};
      const auto first=surface.distance(entry_origin,entry_direction,false);
      check(first.found,"sequential entry exists");
      const auto next=surface.distance(entry_origin+first.distance*entry_direction,
        entry_direction,true);
      check(next.found&&next.distance>.4,"rounded sequential entry advances to exit");
      const auto after_exit=surface.distance(entry_origin
        +(first.distance+next.distance)*entry_direction,entry_direction,true);
      check(after_exit.found&&after_exit.distance>8,
        "rounded sequential exit advances across torus hole");
      check(surface.evaluate(center)<0,"centerline classification is inside");
      check(surface.evaluate(center+Vec3{.252,0,0})>0,"near-boundary classification is outside");
      const auto local=surface.local_coordinates(center+Vec3{.252,0,0});
      check(stellarcsg::norm(local.center-center)<2e-9,"global closest-center projection");
      const auto normal=surface.normal(center+Vec3{.25,0,0});
      check(stellarcsg::norm(normal-Vec3{1,0,0})<2e-8,"normal matches circular tube boundary");
      // Independent exact-rational neutral oracle bounds the actual binary64
      // nominal-tangent near-double pair at this value, not at exactly t=2.
      const auto tangent=surface.distance(knot(data,16)+Vec3{-2,.25,0},{1,0,0},false);
      check(tangent.found&&std::abs(tangent.distance-1.9999999119446658)<2e-8,
        "near-double nominal tangent returns earlier algebraic root");
      const auto miss=surface.distance(knot(data,16)+Vec3{-2,.250001,0},{1,0,0},false);
      check(!miss.found,"outside tangent ladder has no root");
      auto rigid=data;
      const Vec3 translation{11,-7,3};
      for (std::size_t i=0;i<data.sample_count;++i) {
        for (auto* vector:{&rigid.centerline_coefficients,&rigid.normal_coefficients,
                           &rigid.binormal_coefficients}) {
          auto p=rotate({(*vector)[3*i],(*vector)[3*i+1],(*vector)[3*i+2]});
          if (vector==&rigid.centerline_coefficients) p+=translation;
          (*vector)[3*i]=p.x; (*vector)[3*i+1]=p.y; (*vector)[3*i+2]=p.z;
        }
      }
      const stellarcsg::CompiledSweptSplineSurface transformed(rigid,true);
      const auto placed=transformed.distance(rotate(center+Vec3{.252,0,0})+translation,
        rotate({-1,0,0}),false);
      check(placed.found&&std::abs(placed.distance-.002)<2e-9,"rigid circular tube nearest root");
      const Vec3 placed_origin=rotate(entry_origin)+translation;
      const Vec3 placed_direction=rotate(entry_direction);
      const auto placed_first=transformed.distance(placed_origin,placed_direction,false);
      const auto placed_next=transformed.distance(placed_origin
        +placed_first.distance*placed_direction,placed_direction,true);
      check(placed_first.found&&placed_next.found&&placed_next.distance>.4,
        "rigid rounded sequential crossing advances");
      must_throw([&] { (void)surface.distance({100,0,0},{1,0,0},true); },
        "missing coincidence association is explicit");
    }
    auto ellipse=fixture(0.4); ellipse.minor_radius_coefficients.assign(64,.16);
    const stellarcsg::CompiledSweptSplineSurface unsupported(ellipse,true);
    must_throw([&] { (void)unsupported.distance({6,0,0},{-1,0,0},false); },"ellipse distance unsupported");
    must_throw([&] { (void)unsupported.evaluate({6,0,0}); },"ellipse classification unsupported");
    auto rational=fixture(0);
    for (double& coordinate:rational.centerline_coefficients)
      coordinate=3*std::round(coordinate*1024)/1024;
    const stellarcsg::CompiledSweptSplineSurface exact_tangent(rational,true);
    const Vec3 exact_center {
      (rational.centerline_coefficients[45]+4*rational.centerline_coefficients[48]
        +rational.centerline_coefficients[51])/6,
      (rational.centerline_coefficients[46]+4*rational.centerline_coefficients[49]
        +rational.centerline_coefficients[52])/6,0};
    const auto double_root=exact_tangent.distance(exact_center+Vec3{-2,.25,0},
      {1,0,0},false);
    check(double_root.found&&std::abs(double_root.distance-2)<2e-9
      &&double_root.kind==stellarcsg::RootKind::stationary_tangent,
      "exact dyadic tangent multiplicity and distance");
    auto thick=fixture(0.4); thick.major_radius_coefficients.assign(64,6);
    thick.minor_radius_coefficients.assign(64,6);
    must_throw([&] { stellarcsg::CompiledSweptSplineSurface rejected(thick,true); },"tube curvature certificate");
    auto nonfinite=fixture(0); nonfinite.centerline_coefficients[0]=std::numeric_limits<double>::infinity();
    must_throw([&] { stellarcsg::CompiledSweptSplineSurface rejected(nonfinite,true); },"nonfinite payload");
    const auto excessive=fixture(0.4,513);
    must_throw([&] { stellarcsg::CompiledSweptSplineSurface rejected(excessive,true); },"explicit geometry capacity");
  } catch (const std::exception& error) {
    ++failures; std::cerr<<"UNEXPECTED: "<<error.what()<<'\n';
  }
  if (failures) return 1;
  std::cout<<"All circular tube completeness tests passed\n";
}
