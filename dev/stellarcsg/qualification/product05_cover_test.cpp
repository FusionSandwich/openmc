#include "product05_interval_cover.hpp"
#include <iostream>
int main()
{
  using namespace product05;
  stellarcsg::SweptSplineSurfaceData data;
  data.sample_count=4;
  data.centerline_coefficients={0,0,0,1,0,0,2,0,0,3,0,0};
  data.major_radius_coefficients.assign(4,1);
  data.minor_radius_coefficients.assign(4,1);
  const auto tube=compile(data);
  const auto check=[](bool ok) {if(!ok)throw std::runtime_error("cover test failed");};
  // A collinear periodic spline is a stationary-system arithmetic fixture,
  // not an admitted regular embedded tube. At x=1.5 the side roots are 1,3.
  check(!cover(tube,{1.5,2,0},{0,-1,0}).root_free);
  check(!cover(tube,{1.5,0,0},{0,1,0}).root_free);
  check(!cover(tube,{1.5,-2,1},{0,1,0}).root_free);
  check(cover(tube,{1.5,-2,1.01},{0,1,0}).root_free);
  check(cover(tube,{1.5,2,0},{0,1,0}).root_free);
  check(!cover(tube,{1.5,2,0},{0,-1,0},0).root_free);
  check(!cover(tube,{1.5,2,0},{0,-4,0}).root_free);
  for(std::size_t i=0;i<4;++i)data.centerline_coefficients[3*i]+=1e6;
  check(!cover(compile(data),{1e6+1.5,2,0},{0,-1,0}).root_free);
  check(!excludes_zero(I(0)*I(-infinity,infinity)));
  std::cout<<"9 interval-cover checks PASS; not a root-existence test\n";
}
