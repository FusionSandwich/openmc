#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/performance_counters.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <utility>
#include <gmpxx.h>

// Exact local algebra is deliberately confined to the constant circular tube
// path. Coefficient and root decisions use rational values of the supplied
// binary64 B-spline controls; proxies never determine the authoritative shape.
namespace stellarcsg {
namespace circular_detail {
using Q = mpq_class;
using Poly = std::vector<Q>;
struct Interval { Q lo; Q hi; };

[[noreturn]] void unresolved(const char* reason)
{
  throw std::runtime_error(std::string("STELLARCSG_UNRESOLVED_CIRCULAR_TUBE: ") + reason);
}

Interval operator+(const Interval& a, const Interval& b)
{ return {a.lo + b.lo, a.hi + b.hi}; }
Interval operator-(const Interval& a, const Interval& b)
{ return {a.lo - b.hi, a.hi - b.lo}; }
Interval operator*(const Interval& a, const Interval& b)
{
  const std::array<Q, 4> p {a.lo*b.lo, a.lo*b.hi, a.hi*b.lo, a.hi*b.hi};
  return {*std::min_element(p.begin(), p.end()), *std::max_element(p.begin(), p.end())};
}
Interval operator/(const Interval& a, const Interval& b)
{
  if (b.lo <= 0 && b.hi >= 0) unresolved("interval division contains zero");
  return a * Interval {Q(1)/b.hi, Q(1)/b.lo};
}
Interval square(const Interval& a)
{
  Q upper = std::max(Q(a.lo*a.lo), Q(a.hi*a.hi));
  Q lower = a.lo <= 0 && a.hi >= 0 ? Q(0)
    : std::min(Q(a.lo*a.lo), Q(a.hi*a.hi));
  return {lower, upper};
}
void trim(Poly& p) { while (p.size() > 1 && p.back() == 0) p.pop_back(); }
bool zero(const Poly& p) { return p.size() == 1 && p[0] == 0; }
Poly add(Poly a, const Poly& b, int sign = 1)
{
  a.resize(std::max(a.size(), b.size()));
  for (std::size_t i=0; i<b.size(); ++i) a[i] += sign*b[i];
  trim(a); return a;
}
Poly multiply(const Poly& a, const Poly& b)
{
  Poly out(a.size()+b.size()-1);
  for (std::size_t i=0; i<a.size(); ++i)
    for (std::size_t j=0; j<b.size(); ++j) out[i+j] += a[i]*b[j];
  trim(out); return out;
}
Poly scale(Poly a, const Q& b) { for (auto& x:a) x*=b; trim(a); return a; }
Poly derivative(const Poly& p)
{
  if (p.size()==1) return {0};
  Poly out(p.size()-1);
  for (std::size_t i=1; i<p.size(); ++i) out[i-1]=p[i]*Q(static_cast<unsigned long>(i));
  trim(out); return out;
}
Q value(const Poly& p, const Q& x)
{ Q out=0; for (auto i=p.rbegin(); i!=p.rend(); ++i) out=out*x+*i; return out; }
Interval range(const Poly& p, const Interval& x)
{ Interval out {0,0}; for (auto i=p.rbegin(); i!=p.rend(); ++i) out=out*x+Interval{*i,*i}; return out; }
std::pair<Poly,Poly> divide(Poly a, const Poly& b)
{
  if (zero(b)) unresolved("zero polynomial divisor");
  Poly quotient(a.size()>=b.size() ? a.size()-b.size()+1 : 1);
  while (!zero(a) && a.size()>=b.size()) {
    const auto offset=a.size()-b.size();
    const Q factor=a.back()/b.back(); quotient[offset]+=factor;
    for (std::size_t j=0; j<b.size(); ++j) a[offset+j]-=factor*b[j];
    trim(a);
  }
  trim(quotient); return {quotient,a};
}
Poly monic(Poly p) { if (!zero(p)) p=scale(p,Q(1)/p.back()); return p; }
Poly gcd(Poly a, Poly b)
{ while (!zero(b)) { Poly r=divide(a,b).second; a=std::move(b); b=std::move(r); } return monic(a); }
Poly exact_divide(const Poly& a, const Poly& b)
{
  auto result=divide(a,b);
  if (!zero(result.second)) unresolved("non-exact polynomial division");
  return result.first;
}

// Convert power coefficients to Bernstein coefficients on [a,b]. All
// arithmetic here is exact, including the bounds used to reject candidates.
std::vector<Q> bernstein(const Poly& p, const Q& a=0, const Q& b=1)
{
  const std::size_t n=p.size()-1;
  Poly local {0};
  for (auto i=p.rbegin(); i!=p.rend(); ++i) {
    local=multiply(local,Poly{a,b-a}); local[0]+=*i;
  }
  local.resize(n+1);
  std::vector<Q> out(n+1);
  for (std::size_t i=0; i<=n; ++i) {
    Q ratio=1;
    for (std::size_t k=0; k<=i; ++k) {
      if (k) ratio*=Q(static_cast<unsigned long>(i-k+1),static_cast<unsigned long>(n-k+1));
      out[i]+=local[k]*ratio;
    }
  }
  return out;
}
Interval hull(const Poly& p, const Q& a=0, const Q& b=1)
{
  const auto v=bernstein(p,a,b);
  return {*std::min_element(v.begin(),v.end()),*std::max_element(v.begin(),v.end())};
}

struct Sturm {
  Poly p;
  std::vector<Poly> sequence;
  explicit Sturm(Poly polynomial):p(monic(std::move(polynomial)))
  {
    sequence.push_back(p);
    Poly d=derivative(p);
    if (zero(d)) return;
    sequence.push_back(d);
    while (true) {
      Poly r=scale(divide(sequence[sequence.size()-2],sequence.back()).second,Q(-1));
      if (zero(r)) break;
      // Positive rescaling controls rational growth without changing signs.
      Q magnitude=abs(r.back()); r=scale(r,Q(1)/magnitude);
      sequence.push_back(std::move(r));
    }
  }
  int variations(const Q& x, int side) const
  {
    int previous=0, count=0;
    for (std::size_t i=0; i<sequence.size(); ++i) {
      int sign=sgn(value(sequence[i],x));
      if (i==0 && sign==0 && sequence.size()>1) sign=side*sgn(value(sequence[1],x));
      if (!sign) continue;
      if (previous && previous!=sign) ++count;
      previous=sign;
    }
    return count;
  }
  int count_open(const Q& a,const Q& b) const
  { return variations(a,+1)-variations(b,-1); }
};
struct Root {
  std::shared_ptr<const Sturm> sturm;
  Q lo,hi;
  unsigned refinements {0};
  bool exact() const { return lo==hi; }
  void refine()
  {
    if (exact()) return;
    if (++refinements>256) unresolved("algebraic root refinement budget");
    const Q middle=(lo+hi)/2;
    if (value(sturm->p,middle)==0) { lo=middle; hi=middle; }
    else if (sturm->count_open(lo,middle)>0) hi=middle;
    else lo=middle;
  }
};
std::vector<Root> roots(Poly p)
{
  trim(p);
  if (zero(p)) unresolved("identically zero root polynomial");
  if (p.size()==1) return {};
  const auto bounds=hull(p);
  if (bounds.lo>0 || bounds.hi<0) return {};
  p=exact_divide(p,gcd(p,derivative(p)));
  auto sturm=std::make_shared<Sturm>(p);
  std::vector<Root> out;
  if (value(p,0)==0) out.push_back({sturm,0,0});
  if (value(p,1)==0) out.push_back({sturm,1,1});
  struct Box { Q a,b; int count; };
  std::vector<Box> stack {{0,1,sturm->count_open(0,1)}};
  unsigned visits=0;
  while (!stack.empty()) {
    if (++visits>4096) unresolved("root isolation budget");
    Box item=std::move(stack.back()); stack.pop_back();
    if (!item.count) continue;
    if (item.count==1) { out.push_back({sturm,item.a,item.b}); continue; }
    const Q middle=(item.a+item.b)/2;
    if (value(p,middle)==0) out.push_back({sturm,middle,middle});
    stack.push_back({item.a,middle,sturm->count_open(item.a,middle)});
    stack.push_back({middle,item.b,sturm->count_open(middle,item.b)});
  }
  return out;
}
int sign_at(const Poly& p,Root& root)
{
  if (root.exact()) return sgn(value(p,root.lo));
  auto bounds=range(p,{root.lo,root.hi});
  if (bounds.lo>0) return 1;
  if (bounds.hi<0) return -1;
  const Poly common=gcd(root.sturm->p,p);
  if (common.size()>1 && Sturm(common).count_open(root.lo,root.hi)>0) return 0;
  while (true) {
    root.refine(); bounds=range(p,{root.lo,root.hi});
    if (bounds.lo>0) return 1;
    if (bounds.hi<0) return -1;
    if (root.exact()) return sgn(value(p,root.lo));
  }
}
Interval sqrt_bounds(const Interval& x)
{
  if (x.lo<0) unresolved("negative square-root interval");
  // Scale precision with the argument, including subnormal ray directions.
  const Q positive=x.hi>0?x.hi:Q(1);
  const long exponent=static_cast<long>(mpz_sizeinbase(positive.get_num().get_mpz_t(),2))
    -static_cast<long>(mpz_sizeinbase(positive.get_den().get_mpz_t(),2));
  const unsigned bits=static_cast<unsigned>(std::max(96L,96L-exponent/2));
  const mpz_class denominator=mpz_class(1)<<bits;
  const auto lower_sqrt=[&](const Q& a) {
    mpz_class scaled=(a.get_num()*(mpz_class(1)<<(2*bits)))/a.get_den();
    mpz_class integer; mpz_sqrt(integer.get_mpz_t(),scaled.get_mpz_t());
    Q result(integer,denominator); result.canonicalize(); return result;
  };
  Q lo=lower_sqrt(x.lo), hi=lower_sqrt(x.hi);
  if (hi*hi<x.hi) hi+=Q(1,denominator);
  return {lo,hi};
}

using VectorPoly=std::array<Poly,3>;
using Box=std::array<Interval,3>;
struct Span { VectorPoly c,d,dd,n; Box bounds,tangent_bounds; };
Poly dot(const VectorPoly& a,const VectorPoly& b)
{ Poly out {0}; for (std::size_t i=0;i<3;++i) out=add(out,multiply(a[i],b[i])); return out; }
Box bounds(const VectorPoly& p,const Q& a=0,const Q& b=1)
{ return {hull(p[0],a,b),hull(p[1],a,b),hull(p[2],a,b)}; }
Interval dot_box(const Box& a,const Box& b)
{ Interval out {0,0}; for (std::size_t i=0;i<3;++i) out=out+a[i]*b[i]; return out; }
Interval norm_squared_box(const Box& a)
{ Interval out {0,0}; for (const auto& x:a) out=out+square(x); return out; }
Q box_distance_squared(const Box& a,const Box& b)
{
  Q out=0;
  for (std::size_t i=0;i<3;++i) {
    Q gap=std::max(Q(0),std::max(Q(a[i].lo-b[i].hi),Q(b[i].lo-a[i].hi)));
    out+=gap*gap;
  }
  return out;
}
Box cross_box(const Box& a,const Box& b)
{ return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}; }
} // namespace circular_detail

struct CircularTubeCompletenessData {
  std::vector<circular_detail::Span> spans;
  circular_detail::Q radius;
};
namespace circular_detail {
std::shared_ptr<const CircularTubeCompletenessData> compile(
  const SweptSplineSurfaceData& data)
{
  if (data.sample_count>512) unresolved("geometry certificate sample budget (512)");
  auto out=std::make_shared<CircularTubeCompletenessData>();
  out->radius=Q(data.major_radius_coefficients.front());
  const std::array<std::array<int,4>,4> numerator {{
    {{1,4,1,0}},{{-3,0,3,0}},{{3,-6,3,0}},{{-1,3,-3,1}}}};
  for (std::size_t i=0;i<data.sample_count;++i) {
    Span span;
    for (std::size_t axis=0;axis<3;++axis) {
      span.c[axis].resize(4); span.n[axis].resize(4);
      for (std::size_t power=0;power<4;++power) {
        for (std::size_t k=0;k<4;++k) {
          const auto index=(i+k+data.sample_count-1)%data.sample_count;
          span.c[axis][power]+=Q(data.centerline_coefficients[3*index+axis])*numerator[power][k]/6;
          span.n[axis][power]+=Q(data.normal_coefficients[3*index+axis])*numerator[power][k]/6;
        }
      }
      trim(span.c[axis]); trim(span.n[axis]);
      span.d[axis]=derivative(span.c[axis]); span.dd[axis]=derivative(span.d[axis]);
    }
    span.bounds=bounds(span.c); span.tangent_bounds=bounds(span.d);
    struct Part { Q a,b; unsigned depth; };
    std::vector<Part> pending {{0,1,0}};
    while (!pending.empty()) {
      const auto part=pending.back(); pending.pop_back();
      const auto d=bounds(span.d,part.a,part.b), dd=bounds(span.dd,part.a,part.b);
      const auto n=bounds(span.n,part.a,part.b);
      const Q speed2=norm_squared_box(d).lo;
      const Q cross2=norm_squared_box(cross_box(d,dd)).hi;
      const Q frame2=norm_squared_box(cross_box(d,n)).lo;
      if (speed2>0 && frame2>0 && out->radius*out->radius*cross2<speed2*speed2*speed2) continue;
      if (part.depth>=10) unresolved("regularity, frame, or curvature certificate failed");
      const Q midpoint=(part.a+part.b)/2;
      pending.push_back({part.a,midpoint,part.depth+1});
      pending.push_back({midpoint,part.b,part.depth+1});
    }
    out->spans.push_back(std::move(span));
  }
  // Thickness is limited by curvature and half the doubly-critical self
  // distance. No near-diagonal pairs are omitted: a positive independent
  // tangent-dot enclosure on a connecting arc excludes perpendicular chords
  // by integrating C'(u). Otherwise disjoint center hulls must prove >2r.
  const auto n=out->spans.size();
  for (std::size_t i=0;i<n;++i) {
    for (std::size_t j=i;j<n;++j) {
      if (box_distance_squared(out->spans[i].bounds,out->spans[j].bounds)
          >4*out->radius*out->radius) continue;
      const auto forward=j-i, reverse=n-forward;
      const auto start=forward<=reverse?i:j, steps=std::min(forward,reverse);
      Box cone=out->spans[start].tangent_bounds;
      for (std::size_t step=1;step<=steps;++step) {
        const auto& next=out->spans[(start+step)%n].tangent_bounds;
        for (std::size_t axis=0;axis<3;++axis) {
          cone[axis].lo=std::min(cone[axis].lo,next[axis].lo);
          cone[axis].hi=std::max(cone[axis].hi,next[axis].hi);
        }
      }
      if (dot_box(cone,cone).lo<=0)
        unresolved("embedded circular-tube separation certificate failed");
    }
  }
  return out;
}

std::array<Q,3> exact_vector(const Vec3& p)
{
  if (!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z))
    throw std::invalid_argument("Circular tube queries require finite coordinates");
  return {Q(p.x),Q(p.y),Q(p.z)};
}
VectorPoly subtract_point(VectorPoly p,const std::array<Q,3>& point)
{ for (std::size_t i=0;i<3;++i) p[i][0]-=point[i]; return p; }
Poly dot_direction(const VectorPoly& p,const std::array<Q,3>& d)
{ Poly out {0}; for (std::size_t i=0;i<3;++i) out=add(out,scale(p[i],d[i])); return out; }
bool ray_box(const Box& box,const Q& radius,const std::array<Q,3>& o,
  const std::array<Q,3>& d,const Q& minimum=0)
{
  Q enter=minimum,exit=0; bool bounded=false;
  for (std::size_t i=0;i<3;++i) {
    const Q lo=box[i].lo-radius, hi=box[i].hi+radius;
    if (d[i]==0) { if (o[i]<lo||o[i]>hi) return false; continue; }
    Q a=(lo-o[i])/d[i], b=(hi-o[i])/d[i];
    if (a>b) std::swap(a,b);
    enter=std::max(enter,a);
    exit=bounded?std::min(exit,b):b; bounded=true;
    if (exit<enter) return false;
  }
  return bounded && exit>=minimum;
}

struct RayCandidate { Interval physical_t; double residual; RootKind kind;
  std::size_t knot; int branch; };
DistanceResult distance(const CircularTubeCompletenessData& data,
  const Vec3& origin,const Vec3& direction,bool coincident,const RootSearchOptions& options,
  double characteristic)
{
  const auto o=exact_vector(origin),d=exact_vector(direction);
  Q norm2=0; for (const auto& v:d) norm2+=v*v;
  if (norm2<=0) throw std::invalid_argument("Ray direction must be nonzero");
  if (!std::isfinite(options.absolute_t_tolerance)||options.absolute_t_tolerance<=0
      ||!std::isfinite(options.relative_t_tolerance)||options.relative_t_tolerance<0)
    throw std::invalid_argument("Circular tube distance tolerances are invalid");
  const Interval norm_bounds=sqrt_bounds({norm2,norm2});
  // Ordinary queries isolate every forward root of the supplied binary64 ray.
  // Coincidence is a separate, restricted query contract: the caller asserts
  // that exactly one boundary root is associated with the origin in the window
  // below. We replace only that root by zero. Missing/ambiguous associations
  // fail explicitly. This is not a proof that arbitrary rounded OpenMC points
  // satisfy the assertion; tangent/changed-direction crossing semantics still
  // require separate qualification. A position-error bound alone cannot bound
  // ray-root displacement near a tangent.
  const Q minimum=0;
  const Q coordinate_scale(std::max({characteristic,std::abs(origin.x),
    std::abs(origin.y),std::abs(origin.z)}));
  const Q coincidence_window=Q(options.absolute_t_tolerance)
    +(Q(options.relative_t_tolerance)+Q(16*std::numeric_limits<double>::epsilon()))
      *coordinate_scale;
  bool exact_origin_root=false;
  std::vector<RayCandidate> candidates;
  RootSearchDiagnostics diagnostics;
  diagnostics.solver_path=SolverPath::general_swept_certified;
  diagnostics.fallback_reason=SolverFallbackReason::none;
  for (const auto& span:data.spans) {
    const Q lambda_minimum=coincident?-coincidence_window/norm_bounds.lo:Q(0);
    if (!ray_box(span.bounds,data.radius,o,d,lambda_minimum)) {
      ++diagnostics.certified_excluded_intervals; continue;
    }
    add_performance_counter(PerformanceCounter::candidate_patches_or_segments);
    const auto w=subtract_point(span.c,o);
    const Poly A=dot_direction(span.d,d), B=dot(w,span.d), D=dot_direction(w,d);
    Poly E=dot(w,w); E[0]-=data.radius*data.radius; trim(E);
    Poly resultant=add(add(scale(multiply(B,B),norm2),
      scale(multiply(multiply(A,B),D),Q(-2))),multiply(multiply(A,A),E));
    if (zero(resultant)) unresolved("ray lies on a degenerate tube interval");
    const auto resultant_bounds=hull(resultant);
    if (resultant_bounds.lo>0||resultant_bounds.hi<0) {
      ++diagnostics.certified_excluded_intervals; continue;
    }
    add_performance_counter(PerformanceCounter::local_subdivision_calls);
    Poly squarefree=exact_divide(resultant,gcd(resultant,derivative(resultant)));
    const Poly degenerate=gcd(squarefree,A);
    const Poly regular=exact_divide(squarefree,degenerate);
    const auto retain=[&](Root& root,const auto& lambda_interval,RootKind kind,int branch) {
      for (;;) {
        const Interval physical=lambda_interval(root)*norm_bounds;
        if (!coincident&&physical.hi<=minimum) return;
        if (coincident&&physical.hi < -coincidence_window) return;
        const double upper=physical.hi.get_d();
        if (!std::isfinite(upper)) unresolved("unrepresentable ray distance");
        const Q tolerance(options.absolute_t_tolerance
          +options.relative_t_tolerance*std::abs(upper));
        if ((coincident||physical.lo>minimum) && physical.hi-physical.lo<=tolerance) {
          if (candidates.size()>=8192) unresolved("ray candidate budget");
          const auto index=static_cast<std::size_t>(&span-data.spans.data());
          const auto knot=root.exact()&&(root.lo==0||root.lo==1)
            ?(index+(root.lo==1?1:0))%data.spans.size():data.spans.size();
          candidates.push_back({physical,0.0,kind,knot,branch}); return;
        }
        if (root.exact()) unresolved("distance interval meets admissibility threshold");
        root.refine(); ++diagnostics.subdivided_intervals;
      }
    };
    for (auto root:roots(regular)) {
      if (sign_at(A,root)==0) unresolved("uncancelled singular resultant root");
      if (sign_at(B,root)==0) { exact_origin_root=true; continue; }
      while (true) {
        const auto denominator=range(A,{root.lo,root.hi});
        if (denominator.lo>0||denominator.hi<0) break;
        root.refine();
      }
      const Poly radial_derivative=add(scale(B,norm2),multiply(A,D),-1);
      const RootKind kind=sign_at(radial_derivative,root)==0
        ?RootKind::stationary_tangent:RootKind::sign_change;
      retain(root,[&](const Root& r) {
        return range(B,{r.lo,r.hi})/range(A,{r.lo,r.hi});
      },kind,0);
    }
    for (auto root:roots(degenerate)) {
      if (sign_at(B,root)!=0) unresolved("invalid degenerate resultant root");
      const Poly discriminant=add(multiply(D,D),scale(E,norm2),-1);
      const int discriminant_sign=sign_at(discriminant,root);
      if (discriminant_sign<0) continue;
      if (sign_at(E,root)==0) {
        exact_origin_root=true;
        // The exact quadratic roots are 0 and 2D/Q. Handle zero algebraically
        // instead of inferring its sign from a cancellation-prone square root.
        if (sign_at(D,root)==0) continue;
        retain(root,[&](const Root& r) {
          return range(scale(D,Q(2)/norm2),{r.lo,r.hi});
        },RootKind::sign_change,1);
      } else if (discriminant_sign==0) {
        retain(root,[&](const Root& r) {
          return range(scale(D,Q(1)/norm2),{r.lo,r.hi});
        },RootKind::stationary_tangent,2);
      } else {
        while (range(discriminant,{root.lo,root.hi}).lo<=0) root.refine();
        for (int sign:{-1,1}) {
          auto branch=root;
          retain(branch,[&](const Root& r) {
            const Interval square_root=sqrt_bounds(range(discriminant,{r.lo,r.hi}));
            return (range(D,{r.lo,r.hi})+Interval{Q(sign),Q(sign)}*square_root)
              /Interval{norm2,norm2};
          },RootKind::sign_change,sign<0?3:4);
        }
      }
    }
  }
  if (coincident) {
    std::vector<std::size_t> nearby;
    for (std::size_t i=0;i<candidates.size();++i) {
      const auto& t=candidates[i].physical_t;
      if (t.lo<=coincidence_window&&t.hi>=-coincidence_window) {
        if (t.lo < -coincidence_window||t.hi>coincidence_window)
          unresolved("root enclosure straddles the coincidence window boundary");
        nearby.push_back(i);
      }
    }
    // Only exact shared-knot and quadratic-branch identity proves duplicates.
    // Overlapping numerical enclosures alone never establish root identity.
    if (!nearby.empty()) {
      const auto& first=candidates[nearby.front()];
      bool one_root=true;
      for (auto i:nearby) {
        if (i==nearby.front()) continue;
        const auto& candidate=candidates[i];
        if (first.knot==data.spans.size()||candidate.knot!=first.knot
            ||candidate.branch!=first.branch) one_root=false;
      }
      if (exact_origin_root||!one_root)
        unresolved("multiple roots in the coincidence uncertainty interval");
      for (auto i:nearby) candidates[i].physical_t={-1,-1};
    }
    else if (!exact_origin_root)
      unresolved("coincidence assertion has no origin-associated root");
    candidates.erase(std::remove_if(candidates.begin(),candidates.end(),
      [](const RayCandidate& candidate) { return candidate.physical_t.hi<=0; }),candidates.end());
    for (const auto& candidate:candidates)
      if (candidate.physical_t.lo<=0) unresolved("unresolved forward root sign after coincidence");
  }
  if (candidates.empty()) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {false,std::numeric_limits<double>::infinity(),RootKind::sign_change,
      std::numeric_limits<double>::infinity(),diagnostics};
  }
  // Every candidate span has been exhausted. The minimum of the root lower
  // bounds and the minimum of their upper bounds enclose the nearest root.
  Q lo=candidates.front().physical_t.lo,hi=candidates.front().physical_t.hi;
  RootKind kind=candidates.front().kind;
  for (const auto& candidate:candidates) {
    lo=std::min(lo,candidate.physical_t.lo);
    if (candidate.physical_t.hi<hi) { hi=candidate.physical_t.hi; kind=candidate.kind; }
  }
  const Q midpoint=(lo+hi)/2;
  const double returned=midpoint.get_d();
  const Q rounded(returned);
  const Q error=std::max(abs(rounded-lo),abs(hi-rounded));
  const Q requested(options.absolute_t_tolerance
    +options.relative_t_tolerance*std::abs(returned));
  if (error>requested) unresolved("requested distance precision is below output resolution");
  // Distance-to-a-closed-curve is 1-Lipschitz. This bounds the dimensionless
  // circular implicit residual at the rounded ray point, not just interval width.
  const Q residual=(2*data.radius*error+error*error)/(data.radius*data.radius);
  double residual_bound=residual.get_d();
  if (Q(residual_bound)<residual)
    residual_bound=std::nextafter(residual_bound,std::numeric_limits<double>::infinity());
  add_performance_counter(PerformanceCounter::accepted_roots);
  return {true,returned,kind,residual_bound,diagnostics};
}

struct Projection {
  std::size_t span;
  Root root;
  Poly squared_distance;
  Interval squared_bounds;
};
struct Nearest {
  std::size_t span;
  double parameter;
  Vec3 center,tangent,normal;
  double classification;
};
Nearest nearest(const CircularTubeCompletenessData& data,const Vec3& point,
  double characteristic,bool require_projection=true)
{
  const auto p=exact_vector(point);
  const Box point_box {{{p[0],p[0]},{p[1],p[1]},{p[2],p[2]}}};
  std::vector<Projection> candidates;
  Q best_upper;
  bool have_upper=false;
  const Q position_tolerance=std::min(Q(1.0e-12*std::max(1.0,characteristic)),
    Q(data.radius*Q(1.0e-10)));
  const auto retain=[&](std::size_t index,Root root,const Poly& squared) {
    Interval interval;
    for (;;) {
      interval=range(squared,{root.lo,root.hi});
      const auto box=bounds(data.spans[index].c,root.lo,root.hi);
      Q widest=0;
      for (const auto& axis:box) widest=std::max(widest,Q(axis.hi-axis.lo));
      if (root.exact()||widest<=position_tolerance) break;
      root.refine();
    }
    if (!have_upper||interval.hi<best_upper) { best_upper=interval.hi; have_upper=true; }
    if (candidates.size()>=8192) unresolved("projection candidate budget");
    candidates.push_back({index,std::move(root),squared,interval});
  };
  for (std::size_t index=0;index<data.spans.size();++index) {
    const auto& span=data.spans[index];
    if (have_upper&&box_distance_squared(span.bounds,point_box)>best_upper) continue;
    const auto w=subtract_point(span.c,p);
    const Poly squared=dot(w,w), stationary=dot(w,span.d);
    retain(index,{nullptr,0,0},squared);
    retain(index,{nullptr,1,1},squared);
    for (auto root:roots(stationary)) retain(index,std::move(root),squared);
  }
  if (candidates.empty()) unresolved("empty projection candidate set");
  std::size_t best=0;
  int classification_sign=1;
  const Q radius2=data.radius*data.radius;
  for (std::size_t i=0;i<candidates.size();++i) {
    auto& candidate=candidates[i];
    if (candidate.squared_bounds.hi<candidates[best].squared_bounds.hi) best=i;
    if (classification_sign<0||candidate.squared_bounds.lo>radius2) continue;
    Poly difference=candidate.squared_distance; difference[0]-=radius2; trim(difference);
    classification_sign=std::min(classification_sign,sign_at(difference,candidate.root));
  }
  if (require_projection) {
    best=0;
    std::vector<std::size_t> tied;
    const auto same_exact_point=[&](const Projection& a,const Projection& b) {
      if (!a.root.exact()||!b.root.exact()) return false;
      for (std::size_t axis=0;axis<3;++axis)
        if (value(data.spans[a.span].c[axis],a.root.lo)
            !=value(data.spans[b.span].c[axis],b.root.lo)) return false;
      return true;
    };
    for (std::size_t i=1;i<candidates.size();++i) {
      for (;;) {
        auto& a=candidates[best]; auto& b=candidates[i];
        a.squared_bounds=range(a.squared_distance,{a.root.lo,a.root.hi});
        b.squared_bounds=range(b.squared_distance,{b.root.lo,b.root.hi});
        if (a.squared_bounds.hi<b.squared_bounds.lo||same_exact_point(a,b)) break;
        if (b.squared_bounds.hi<a.squared_bounds.lo) { best=i; tied.clear(); break; }
        if (a.root.exact()||b.root.exact()) {
          const bool a_exact=a.root.exact();
          const Q exact_distance=a_exact?value(a.squared_distance,a.root.lo)
            :value(b.squared_distance,b.root.lo);
          auto& variable=a_exact?b:a;
          Poly difference=variable.squared_distance; difference[0]-=exact_distance;
          const int sign=sign_at(difference,variable.root);
          if (!sign) { tied.push_back(i); break; }
          if ((a_exact&&sign<0)||(!a_exact&&sign>0)) { best=i; tied.clear(); }
          break;
        }
        a.root.refine(); b.root.refine();
      }
    }
    if (!tied.empty()) unresolved("nonunique nearest center outside the tubular neighborhood");
  }

  auto& chosen=candidates[best];
  const Q parameter=(chosen.root.lo+chosen.root.hi)/2;
  const auto& span=data.spans[chosen.span];
  const auto sample=[&](const VectorPoly& poly) {
    return Vec3 {value(poly[0],parameter).get_d(),value(poly[1],parameter).get_d(),
      value(poly[2],parameter).get_d()};
  };
  const Vec3 center=sample(span.c),tangent=normalized(sample(span.d));
  const Vec3 supplied=sample(span.n);
  const Vec3 normal=normalized(supplied-dot(supplied,tangent)*tangent);
  Q approximate=(value(chosen.squared_distance,parameter)-radius2)/radius2;
  double classification=std::abs(approximate.get_d());
  if (classification_sign==0) classification=0;
  else classification=classification_sign*std::max(classification,std::numeric_limits<double>::denorm_min());
  return {chosen.span,parameter.get_d(),center,tangent,normal,classification};
}
} // namespace circular_detail
} // namespace stellarcsg

namespace stellarcsg {
namespace {

constexpr double two_pi =
  2.0 * 3.141592653589793238462643383279502884;

constexpr std::array<std::array<double, 4>, 4> bspline_to_power {{
  {{1.0 / 6.0, 4.0 / 6.0, 1.0 / 6.0, 0.0}},
  {{-0.5, 0.0, 0.5, 0.0}},
  {{0.5, -1.0, 0.5, 0.0}},
  {{-1.0 / 6.0, 0.5, -0.5, 1.0 / 6.0}}}};

std::atomic<std::uint64_t> next_swept_surface_instance {1};

struct SweptEvaluationCache {
  std::uint64_t instance_id {0};
  Vec3 point {};
  double value {0.0};
  bool valid {false};
};

thread_local SweptEvaluationCache swept_evaluation_cache;

std::vector<double> component(
  const std::vector<double>& values, std::size_t count, std::size_t axis)
{
  if (values.size() != 3 * count) {
    throw std::invalid_argument("Swept-spline vector coefficient shape is invalid");
  }
  std::vector<double> result(count);
  for (std::size_t i = 0; i < count; ++i) result[i] = values[3 * i + axis];
  return result;
}

void validate(const SweptSplineSurfaceData& data)
{
  if (data.sample_count < 8) {
    throw std::invalid_argument("Swept-spline surface requires at least eight samples");
  }
  if (data.centerline_coefficients.size() != 3 * data.sample_count
      || data.normal_coefficients.size() != 3 * data.sample_count
      || data.binormal_coefficients.size() != 3 * data.sample_count
      || data.major_radius_coefficients.size() != data.sample_count
      || data.minor_radius_coefficients.size() != data.sample_count) {
    throw std::invalid_argument("Swept-spline coefficient dimensions are inconsistent");
  }
  if (!(data.length > 0.0) || !(data.characteristic_length > 0.0)
      || !std::isfinite(data.length) || !std::isfinite(data.characteristic_length)) {
    throw std::invalid_argument("Swept-spline length scales must be positive");
  }
  for (const double radius : data.major_radius_coefficients) {
    if (!(radius > 0.0)||!std::isfinite(radius)) throw std::invalid_argument("Major radii must be finite and positive");
  }
  for (const double radius : data.minor_radius_coefficients) {
    if (!(radius > 0.0)||!std::isfinite(radius)) throw std::invalid_argument("Minor radii must be finite and positive");
  }
  for (const auto* values:{&data.centerline_coefficients,&data.normal_coefficients,
                          &data.binormal_coefficients})
    for (double value:*values) if (!std::isfinite(value))
      throw std::invalid_argument("Swept vector coefficients must be finite");
}

double wrap(double angle)
{
  double value = std::fmod(angle, two_pi);
  if (value < 0.0) value += two_pi;
  return value;
}

std::size_t wrap_index(long index, std::size_t size)
{
  const long signed_size = static_cast<long>(size);
  long wrapped = index % signed_size;
  if (wrapped < 0) wrapped += signed_size;
  return static_cast<std::size_t>(wrapped);
}

BoundingBox empty_box()
{
  return {{std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity()},
          {-std::numeric_limits<double>::infinity(),
            -std::numeric_limits<double>::infinity(),
            -std::numeric_limits<double>::infinity()}};
}

void extend(BoundingBox& box, const Vec3& point)
{
  box.lower.x = std::min(box.lower.x, point.x);
  box.lower.y = std::min(box.lower.y, point.y);
  box.lower.z = std::min(box.lower.z, point.z);
  box.upper.x = std::max(box.upper.x, point.x);
  box.upper.y = std::max(box.upper.y, point.y);
  box.upper.z = std::max(box.upper.z, point.z);
}

void extend(BoundingBox& box, const BoundingBox& other)
{
  extend(box, other.lower);
  extend(box, other.upper);
}

Vec3 centroid(const BoundingBox& box)
{
  return 0.5 * (box.lower + box.upper);
}

double point_box_distance_squared(const Vec3& point, const BoundingBox& box)
{
  const auto axis_distance = [](double value, double lower, double upper) {
    if (value < lower) return lower - value;
    if (value > upper) return value - upper;
    return 0.0;
  };
  const double dx = axis_distance(point.x, box.lower.x, box.upper.x);
  const double dy = axis_distance(point.y, box.lower.y, box.upper.y);
  const double dz = axis_distance(point.z, box.lower.z, box.upper.z);
  return dx * dx + dy * dy + dz * dz;
}

} // namespace

CompiledSweptSplineSurface::CompiledSweptSplineSurface(
  SweptSplineSurfaceData data, bool force_general_solver)
  : data_ {[&data]() { validate(data); return std::move(data); }()}
  , center_x_ {data_.sample_count, 1,
      component(data_.centerline_coefficients, data_.sample_count, 0)}
  , center_y_ {data_.sample_count, 1,
      component(data_.centerline_coefficients, data_.sample_count, 1)}
  , center_z_ {data_.sample_count, 1,
      component(data_.centerline_coefficients, data_.sample_count, 2)}
  , normal_x_ {data_.sample_count, 1,
      component(data_.normal_coefficients, data_.sample_count, 0)}
  , normal_y_ {data_.sample_count, 1,
      component(data_.normal_coefficients, data_.sample_count, 1)}
  , normal_z_ {data_.sample_count, 1,
      component(data_.normal_coefficients, data_.sample_count, 2)}
  , binormal_x_ {data_.sample_count, 1,
      component(data_.binormal_coefficients, data_.sample_count, 0)}
  , binormal_y_ {data_.sample_count, 1,
      component(data_.binormal_coefficients, data_.sample_count, 1)}
  , binormal_z_ {data_.sample_count, 1,
      component(data_.binormal_coefficients, data_.sample_count, 2)}
  , major_radius_ {data_.sample_count, 1, data_.major_radius_coefficients}
  , minor_radius_ {data_.sample_count, 1, data_.minor_radius_coefficients}
{
  instance_id_ = next_swept_surface_instance.fetch_add(
    1, std::memory_order_relaxed);
  circular_radius_ = data_.major_radius_coefficients.front();
  const double circular_tolerance = std::max(
    64.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length,
    1.0e-12 * data_.characteristic_length);
  circular_cross_section_ = std::all_of(
    data_.major_radius_coefficients.begin(),
    data_.major_radius_coefficients.end(), [&](double value) {
      return std::abs(value - circular_radius_) <= circular_tolerance;
    }) && std::all_of(data_.minor_radius_coefficients.begin(),
      data_.minor_radius_coefficients.end(), [&](double value) {
        return std::abs(value - circular_radius_) <= circular_tolerance;
      });
  const double radius_max = std::max(
    *std::max_element(data_.major_radius_coefficients.begin(),
      data_.major_radius_coefficients.end()),
    *std::max_element(data_.minor_radius_coefficients.begin(),
      data_.minor_radius_coefficients.end()));
  bounds_ = {{std::numeric_limits<double>::infinity(),
               std::numeric_limits<double>::infinity(),
               std::numeric_limits<double>::infinity()},
             {-std::numeric_limits<double>::infinity(),
               -std::numeric_limits<double>::infinity(),
               -std::numeric_limits<double>::infinity()}};
  for (std::size_t i = 0; i < data_.sample_count; ++i) {
    bounds_.lower.x = std::min(bounds_.lower.x,
      data_.centerline_coefficients[3 * i]);
    bounds_.lower.y = std::min(bounds_.lower.y,
      data_.centerline_coefficients[3 * i + 1]);
    bounds_.lower.z = std::min(bounds_.lower.z,
      data_.centerline_coefficients[3 * i + 2]);
    bounds_.upper.x = std::max(bounds_.upper.x,
      data_.centerline_coefficients[3 * i]);
    bounds_.upper.y = std::max(bounds_.upper.y,
      data_.centerline_coefficients[3 * i + 1]);
    bounds_.upper.z = std::max(bounds_.upper.z,
      data_.centerline_coefficients[3 * i + 2]);
  }
  bounds_.lower = bounds_.lower - Vec3 {radius_max, radius_max, radius_max};
  bounds_.upper = bounds_.upper + Vec3 {radius_max, radius_max, radius_max};
  build_spans();

  double radius_sum = 0.0;
  double z_sum = 0.0;
  double cross_sum = 0.0;
  bool circular = true;
  const std::size_t checks = std::max<std::size_t>(64, data_.sample_count);
  for (std::size_t i = 0; i < checks; ++i) {
    const double angle = two_pi * static_cast<double>(i)
                         / static_cast<double>(checks);
    const auto frame_value = frame(angle);
    const double radius = std::hypot(frame_value.center.x, frame_value.center.y);
    radius_sum += radius;
    z_sum += frame_value.center.z;
    cross_sum += frame_value.major_radius;
  }
  const double mean_radius = radius_sum / static_cast<double>(checks);
  const double mean_z = z_sum / static_cast<double>(checks);
  const double mean_cross = cross_sum / static_cast<double>(checks);
  const double tolerance = 1.0e-6 * data_.characteristic_length;
  for (std::size_t i = 0; i < checks; ++i) {
    const auto value = frame(two_pi * static_cast<double>(i)
                             / static_cast<double>(checks));
    circular = circular
      && std::abs(std::hypot(value.center.x, value.center.y) - mean_radius)
           <= tolerance
      && std::abs(value.center.z - mean_z) <= tolerance
      && std::abs(value.major_radius - mean_cross) <= tolerance
      && std::abs(value.minor_radius - mean_cross) <= tolerance;
  }
  if (circular && !force_general_solver) {
    PeriodicSplineSurfaceData torus;
    torus.content_id = "swept-exact-torus-specialization";
    torus.axis_r_coefficients.assign(8, mean_radius);
    torus.axis_z_coefficients.assign(8, mean_z);
    torus.n_theta = 12;
    torus.n_phi = 8;
    torus.radius_coefficients.assign(torus.n_theta * torus.n_phi, mean_cross);
    torus.characteristic_length = mean_radius + mean_cross;
    exact_torus_ = std::make_unique<CompiledPeriodicSplineSurface>(std::move(torus));
  }
  const bool exact_constant_radius=std::all_of(
    data_.major_radius_coefficients.begin(),data_.major_radius_coefficients.end(),
    [&](double r) { return r==circular_radius_; })&&std::all_of(
    data_.minor_radius_coefficients.begin(),data_.minor_radius_coefficients.end(),
    [&](double r) { return r==circular_radius_; });
  if (!exact_torus_&&exact_constant_radius)
    circular_completeness_=circular_detail::compile(data_);
  if (circular_completeness_) {
    bounds_=empty_box();
    for (const auto& span:circular_completeness_->spans) {
      std::array<double,3> lo,hi;
      for (std::size_t axis=0;axis<3;++axis) {
        const circular_detail::Q lower=span.bounds[axis].lo-circular_completeness_->radius;
        const circular_detail::Q upper=span.bounds[axis].hi+circular_completeness_->radius;
        lo[axis]=lower.get_d(); hi[axis]=upper.get_d();
        if (circular_detail::Q(lo[axis])>lower)
          lo[axis]=std::nextafter(lo[axis],-std::numeric_limits<double>::infinity());
        if (circular_detail::Q(hi[axis])<upper)
          hi[axis]=std::nextafter(hi[axis],std::numeric_limits<double>::infinity());
      }
      extend(bounds_,{lo[0],lo[1],lo[2]}); extend(bounds_,{hi[0],hi[1],hi[2]});
    }
  } else if (exact_torus_) bounds_=exact_torus_->bounding_box();
}

SweptLocalCoordinates CompiledSweptSplineSurface::frame(double angle) const
{
  const double q = wrap(angle);
  const auto cx = center_x_.sample(q);
  const auto cy = center_y_.sample(q);
  const auto cz = center_z_.sample(q);
  Vec3 tangent = normalized({cx.derivative, cy.derivative, cz.derivative});
  Vec3 normal_value {normal_x_.sample(q).value, normal_y_.sample(q).value,
    normal_z_.sample(q).value};
  normal_value = normal_value - dot(normal_value, tangent) * tangent;
  normal_value = normalized(normal_value);
  Vec3 binormal_value = normalized(cross(tangent, normal_value));
  normal_value = cross(binormal_value, tangent);
  return {data_.coil_id, q * data_.length / two_pi, 0.0, 0.0,
    {cx.value, cy.value, cz.value}, tangent, normal_value, binormal_value,
    major_radius_.sample(q).value, minor_radius_.sample(q).value};
}

SweptLocalCoordinates CompiledSweptSplineSurface::frame_in_span(
  const SweptSpan& span, double angle) const
{
  const double coordinate_scale = 1.0 / (span.angle_max - span.angle_min);
  const double u = (angle - span.angle_min) * coordinate_scale;
  std::array<double, 8> value {};
  std::array<double, 3> derivative {};
  for (std::size_t field = 0; field < value.size(); ++field) {
    const double c0 = span.power[4 * field];
    const double c1 = span.power[4 * field + 1];
    const double c2 = span.power[4 * field + 2];
    const double c3 = span.power[4 * field + 3];
    value[field] = ((c3 * u + c2) * u + c1) * u + c0;
    if (field < derivative.size()) {
      derivative[field] = ((3.0 * c3 * u + 2.0 * c2) * u + c1)
                          * coordinate_scale;
    }
  }
  Vec3 tangent = normalized({derivative[0], derivative[1], derivative[2]});
  Vec3 normal_value {value[3], value[4], value[5]};
  normal_value = normalized(normal_value - dot(normal_value, tangent) * tangent);
  Vec3 binormal_value = normalized(cross(tangent, normal_value));
  normal_value = cross(binormal_value, tangent);
  return {data_.coil_id, wrap(angle) * data_.length / two_pi, 0.0, 0.0,
    {value[0], value[1], value[2]}, tangent, normal_value, binormal_value,
    value[6], value[7]};
}

double CompiledSweptSplineSurface::squared_distance(
  const Vec3& point, double angle) const
{
  const auto value = frame(angle);
  return norm_squared(point - value.center);
}

Vec3 CompiledSweptSplineSurface::surface_point(
  const SweptSpan& span, double angle, double alpha) const
{
  const auto value = frame_in_span(span, angle);
  return value.center
    + value.major_radius * std::cos(alpha) * value.normal
    + value.minor_radius * std::sin(alpha) * value.binormal;
}

void CompiledSweptSplineSurface::center_derivatives(const SweptSpan& span,
  double angle, Vec3& center, Vec3& first, Vec3& second) const
{
  const double scale = 1.0 / (span.angle_max - span.angle_min);
  const double u = (angle - span.angle_min) * scale;
  for (std::size_t axis = 0; axis < 3; ++axis) {
    const double* coefficient = span.power.data() + 4 * axis;
    const double value = ((coefficient[3] * u + coefficient[2]) * u
      + coefficient[1]) * u + coefficient[0];
    const double derivative = (coefficient[1]
      + 2.0 * coefficient[2] * u + 3.0 * coefficient[3] * u * u)
      * scale;
    const double second_derivative = (2.0 * coefficient[2]
      + 6.0 * coefficient[3] * u) * scale * scale;
    if (axis == 0) {
      center.x = value;
      first.x = derivative;
      second.x = second_derivative;
    } else if (axis == 1) {
      center.y = value;
      first.y = derivative;
      second.y = second_derivative;
    } else {
      center.z = value;
      first.z = derivative;
      second.z = second_derivative;
    }
  }
}

void CompiledSweptSplineSurface::surface_derivatives(const SweptSpan& span,
  double angle, double alpha, Vec3& position, Vec3& dangle,
  Vec3& dalpha) const
{
  const double scale = 1.0 / (span.angle_max - span.angle_min);
  const double u = (angle - span.angle_min) * scale;
  std::array<double, 8> value {};
  std::array<double, 8> derivative {};
  std::array<double, 3> second_derivative {};
  for (std::size_t field = 0; field < value.size(); ++field) {
    const double* coefficient = span.power.data() + 4 * field;
    value[field] = ((coefficient[3] * u + coefficient[2]) * u
                     + coefficient[1]) * u + coefficient[0];
    derivative[field] = (coefficient[1] + 2.0 * coefficient[2] * u
                          + 3.0 * coefficient[3] * u * u) * scale;
    if (field < second_derivative.size()) {
      second_derivative[field] = (2.0 * coefficient[2]
        + 6.0 * coefficient[3] * u) * scale * scale;
    }
  }
  const Vec3 center {value[0], value[1], value[2]};
  const Vec3 center_d {derivative[0], derivative[1], derivative[2]};
  const Vec3 center_dd {
    second_derivative[0], second_derivative[1], second_derivative[2]};
  const double speed = norm(center_d);
  const Vec3 tangent = center_d / speed;
  const Vec3 tangent_d = (center_dd - tangent * dot(tangent, center_dd))
                         / speed;
  const Vec3 supplied_normal {value[3], value[4], value[5]};
  const Vec3 supplied_normal_d {
    derivative[3], derivative[4], derivative[5]};
  const double projection = dot(supplied_normal, tangent);
  const double projection_d = dot(supplied_normal_d, tangent)
                              + dot(supplied_normal, tangent_d);
  const Vec3 normal_raw = supplied_normal - projection * tangent;
  const Vec3 normal_raw_d = supplied_normal_d - projection_d * tangent
                            - projection * tangent_d;
  const double normal_length = norm(normal_raw);
  Vec3 normal_value = normal_raw / normal_length;
  Vec3 normal_d = (normal_raw_d
    - normal_value * dot(normal_value, normal_raw_d)) / normal_length;
  const Vec3 binormal_raw = cross(tangent, normal_value);
  const Vec3 binormal_raw_d = cross(tangent_d, normal_value)
                              + cross(tangent, normal_d);
  const double binormal_length = norm(binormal_raw);
  const Vec3 binormal_value = binormal_raw / binormal_length;
  const Vec3 binormal_d = (binormal_raw_d
    - binormal_value * dot(binormal_value, binormal_raw_d))
    / binormal_length;
  normal_value = cross(binormal_value, tangent);
  normal_d = cross(binormal_d, tangent) + cross(binormal_value, tangent_d);
  const double cosine = std::cos(alpha);
  const double sine = std::sin(alpha);
  const double major = value[6];
  const double minor = value[7];
  position = center + major * cosine * normal_value
             + minor * sine * binormal_value;
  dangle = center_d
           + cosine * (derivative[6] * normal_value + major * normal_d)
           + sine * (derivative[7] * binormal_value + minor * binormal_d);
  dalpha = -major * sine * normal_value
           + minor * cosine * binormal_value;
}

void CompiledSweptSplineSurface::build_spans()
{
  const double step = two_pi / static_cast<double>(data_.sample_count);
  const double rounding = std::max(
    64.0 * std::numeric_limits<double>::epsilon()
      * data_.characteristic_length,
    1.0e-12 * data_.characteristic_length);
  constexpr std::size_t subdivisions = 1;
  spans_.clear();
  spans_.reserve(subdivisions * data_.sample_count);
  for (std::size_t i = 0; i < data_.sample_count; ++i) {
    std::array<double, 32> base_power {};
    const auto coefficient_value = [&](std::size_t field,
                                      std::size_t control) {
      if (field < 3) return data_.centerline_coefficients[3 * control + field];
      if (field < 6) return data_.normal_coefficients[
        3 * control + (field - 3)];
      return field == 6 ? data_.major_radius_coefficients[control]
                        : data_.minor_radius_coefficients[control];
    };
    for (std::size_t field = 0; field < 8; ++field) {
      for (std::size_t power = 0; power < 4; ++power) {
        double coefficient = 0.0;
        for (std::size_t a = 0; a < 4; ++a) {
          const std::size_t control = wrap_index(
            static_cast<long>(i) + static_cast<long>(a) - 1,
            data_.sample_count);
          coefficient += bspline_to_power[power][a]
                         * coefficient_value(field, control);
        }
        base_power[4 * field + power] = coefficient;
      }
    }
    for (std::size_t subdivision = 0;
         subdivision < subdivisions; ++subdivision) {
      SweptSpan span;
      const double a = static_cast<double>(subdivision)
                       / static_cast<double>(subdivisions);
      const double h = 1.0 / static_cast<double>(subdivisions);
      span.angle_min = step * (static_cast<double>(i) + a);
      span.angle_max = span.angle_min + step * h;
      for (std::size_t field = 0; field < 8; ++field) {
        const double* source = base_power.data() + 4 * field;
        double* target = span.power.data() + 4 * field;
        target[0] = ((source[3] * a + source[2]) * a + source[1]) * a
                    + source[0];
        target[1] = h * (source[1] + 2.0 * source[2] * a
                         + 3.0 * source[3] * a * a);
        target[2] = h * h * (source[2] + 3.0 * source[3] * a);
        target[3] = h * h * h * source[3];
      }
      span.proxy_start = frame_in_span(span, span.angle_min).center;
      span.proxy_end = frame_in_span(span, span.angle_max).center;
      BoundingBox center_bounds = empty_box();
      double radius_bound = 0.0;
      for (std::size_t bezier = 0; bezier < 4; ++bezier) {
        Vec3 center_control;
        for (std::size_t field = 0; field < 8; ++field) {
          const double* power = span.power.data() + 4 * field;
          const double value = bezier == 0 ? power[0]
            : bezier == 1 ? power[0] + power[1] / 3.0
            : bezier == 2 ? power[0] + 2.0 * power[1] / 3.0
                            + power[2] / 3.0
            : power[0] + power[1] + power[2] + power[3];
          if (field == 0) center_control.x = value;
          else if (field == 1) center_control.y = value;
          else if (field == 2) center_control.z = value;
          else if (field >= 6) radius_bound = std::max(radius_bound, value);
        }
        extend(center_bounds, center_control);
      }
      span.radius_bound = radius_bound;
      const Vec3 second_start {
        2.0 * span.power[2], 2.0 * span.power[6],
        2.0 * span.power[10]};
      const Vec3 second_end {
        2.0 * span.power[2] + 6.0 * span.power[3],
        2.0 * span.power[6] + 6.0 * span.power[7],
        2.0 * span.power[10] + 6.0 * span.power[11]};
      const double centerline_error = std::max(
        norm(second_start), norm(second_end)) / 8.0;
      span.proxy_radius = radius_bound + centerline_error + rounding;
      const double inflation = radius_bound + rounding;
      span.centerline_bbox = center_bounds;
      span.conservative_bbox = {
        center_bounds.lower - Vec3 {inflation, inflation, inflation},
        center_bounds.upper + Vec3 {inflation, inflation, inflation}};
      spans_.push_back(span);
    }
  }
  span_indices_.resize(spans_.size());
  std::iota(span_indices_.begin(), span_indices_.end(), 0U);
  span_bvh_.clear();
  span_bvh_.reserve(2 * spans_.size());
  if (!spans_.empty()) {
    (void) build_span_bvh_node(0U,
      static_cast<std::uint32_t>(spans_.size()));
    bounds_ = span_bvh_.front().bbox;
  }
}

std::uint32_t CompiledSweptSplineSurface::build_span_bvh_node(
  std::uint32_t first, std::uint32_t last)
{
  const std::uint32_t node_index = static_cast<std::uint32_t>(span_bvh_.size());
  span_bvh_.push_back({});
  BoundingBox bounds = empty_box();
  BoundingBox centerline_bounds = empty_box();
  BoundingBox centroids = empty_box();
  for (std::uint32_t i = first; i < last; ++i) {
    const auto& span = spans_[span_indices_[i]];
    const auto& box = span.conservative_bbox;
    extend(bounds, box);
    extend(centerline_bounds, span.centerline_bbox);
    extend(centroids, centroid(box));
  }
  span_bvh_[node_index].centerline_bbox = centerline_bounds;
  span_bvh_[node_index].bbox = bounds;
  const std::uint32_t count = last - first;
  constexpr std::uint32_t leaf_size = 4;
  if (count <= leaf_size) {
    span_bvh_[node_index].first = first;
    span_bvh_[node_index].count = static_cast<std::uint16_t>(count);
    return node_index;
  }
  const Vec3 extent = centroids.upper - centroids.lower;
  const int axis = extent.y > extent.x ? (extent.z > extent.y ? 2 : 1)
                                      : (extent.z > extent.x ? 2 : 0);
  const auto component_value = [](const Vec3& value, int selected) {
    return selected == 0 ? value.x : (selected == 1 ? value.y : value.z);
  };
  const std::uint32_t middle = first + count / 2;
  std::nth_element(span_indices_.begin() + first,
    span_indices_.begin() + middle, span_indices_.begin() + last,
    [&](std::uint32_t lhs, std::uint32_t rhs) {
      return component_value(centroid(spans_[lhs].conservative_bbox), axis)
             < component_value(centroid(spans_[rhs].conservative_bbox), axis);
    });
  span_bvh_[node_index].left = build_span_bvh_node(first, middle);
  span_bvh_[node_index].right = build_span_bvh_node(middle, last);
  return node_index;
}

double CompiledSweptSplineSurface::evaluate_in_span(
  const Vec3& point, const SweptSpan& span, double* angle) const
{
  const auto local_squared_distance = [&](double candidate) {
    const double coordinate_scale = 1.0
      / (span.angle_max - span.angle_min);
    const double u = (candidate - span.angle_min) * coordinate_scale;
    Vec3 center;
    for (std::size_t axis = 0; axis < 3; ++axis) {
      const double* coefficient = span.power.data() + 4 * axis;
      const double value = ((coefficient[3] * u + coefficient[2]) * u
                             + coefficient[1]) * u + coefficient[0];
      if (axis == 0) center.x = value;
      else if (axis == 1) center.y = value;
      else center.z = value;
    }
    return norm_squared(point - center);
  };
  double left = span.angle_min;
  double right = span.angle_max;
  constexpr double ratio = 0.6180339887498948482;
  double c = right - ratio * (right - left);
  double d = left + ratio * (right - left);
  double fc = local_squared_distance(c);
  double fd = local_squared_distance(d);
  for (int iteration = 0; iteration < 8; ++iteration) {
    if (fc < fd) {
      right = d;
      d = c;
      fd = fc;
      c = right - ratio * (right - left);
      fc = local_squared_distance(c);
    } else {
      left = c;
      c = d;
      fc = fd;
      d = left + ratio * (right - left);
      fd = local_squared_distance(d);
    }
  }
  double q = 0.5 * (left + right);
  for (int iteration = 0; iteration < 5; ++iteration) {
    Vec3 center;
    Vec3 first;
    Vec3 second;
    center_derivatives(span, q, center, first, second);
    const Vec3 offset = center - point;
    const double gradient = dot(offset, first);
    const double hessian = norm_squared(first) + dot(offset, second);
    if (!(hessian > 0.0) || !std::isfinite(hessian)) break;
    const double next = std::clamp(q - gradient / hessian, left, right);
    if (std::abs(next - q) <= 1.0e-14) {
      q = next;
      break;
    }
    q = next;
  }
  if (angle) *angle = q;
  const auto value = frame_in_span(span, q);
  const Vec3 offset = point - value.center;
  const double u = dot(offset, value.normal) / value.major_radius;
  const double v = dot(offset, value.binormal) / value.minor_radius;
  return u * u + v * v - 1.0;
}

SweptLocalCoordinates CompiledSweptSplineSurface::local_coordinates(
  const Vec3& point) const
{
  if (circular_completeness_) {
    const auto result=circular_detail::nearest(*circular_completeness_,point,
      data_.characteristic_length);
    const double fraction=(static_cast<double>(result.span)+result.parameter)
      /static_cast<double>(data_.sample_count);
    const auto binormal=cross(result.tangent,result.normal);
    const auto offset=point-result.center;
    return {data_.coil_id,fraction*data_.length,dot(offset,result.normal),
      dot(offset,binormal),result.center,result.tangent,result.normal,binormal,
      circular_radius_,circular_radius_};
  }
  if (!exact_torus_) circular_detail::unresolved("nonconstant or elliptical sections are unsupported");
  struct StackEntry { std::uint32_t node; double lower_bound; };
  std::array<StackEntry, 64> stack {};
  std::size_t stack_size = 0;
  double best_angle = 0.0;
  std::size_t refined_span = 0;
  double refined_distance = std::numeric_limits<double>::infinity();
  if (!span_bvh_.empty()) {
    stack[stack_size++] = {
      0U, point_box_distance_squared(point, span_bvh_[0].centerline_bbox)};
  }
  while (stack_size != 0) {
    const auto entry = stack[--stack_size];
    if (entry.lower_bound >= refined_distance) continue;
    const auto& node = span_bvh_[entry.node];
    if (node.leaf()) {
      for (std::uint32_t local = 0; local < node.count; ++local) {
        const std::size_t candidate = span_indices_[node.first + local];
        const auto& span = spans_[candidate];
        if (point_box_distance_squared(point, span.centerline_bbox)
            >= refined_distance) continue;
        double angle = 0.0;
        (void) evaluate_in_span(point, span, &angle);
        const double distance = norm_squared(
          point - frame_in_span(span, angle).center);
        if (distance < refined_distance) {
          refined_distance = distance;
          best_angle = angle;
          refined_span = candidate;
        }
      }
      continue;
    }
    const double left_bound = point_box_distance_squared(
      point, span_bvh_[node.left].centerline_bbox);
    const double right_bound = point_box_distance_squared(
      point, span_bvh_[node.right].centerline_bbox);
    const bool left_first = left_bound <= right_bound;
    const StackEntry near_entry = left_first
      ? StackEntry {node.left, left_bound}
      : StackEntry {node.right, right_bound};
    const StackEntry far_entry = left_first
      ? StackEntry {node.right, right_bound}
      : StackEntry {node.left, left_bound};
    if (far_entry.lower_bound < refined_distance)
      stack[stack_size++] = far_entry;
    if (near_entry.lower_bound < refined_distance)
      stack[stack_size++] = near_entry;
  }
  auto result = frame_in_span(spans_[refined_span], best_angle);
  const Vec3 offset = point - result.center;
  result.u = dot(offset, result.normal);
  result.v = dot(offset, result.binormal);
  return result;
}

double CompiledSweptSplineSurface::evaluate(const Vec3& point) const
{
  add_performance_counter(PerformanceCounter::evaluate_calls);
  auto& cache = swept_evaluation_cache;
  if (cache.valid && cache.instance_id == instance_id_
      && cache.point.x == point.x && cache.point.y == point.y
      && cache.point.z == point.z) {
    add_performance_counter(PerformanceCounter::cache_hits);
    return cache.value;
  }
  add_performance_counter(PerformanceCounter::cache_misses);
  double value;
  if (exact_torus_) {
    value = exact_torus_->evaluate(point);
  } else {
    if (!circular_completeness_) circular_detail::unresolved("nonconstant or elliptical sections are unsupported");
    value=circular_detail::nearest(*circular_completeness_,point,
      data_.characteristic_length,false).classification;
  }
  cache = {instance_id_, point, value, true};
  return value;
}

Vec3 CompiledSweptSplineSurface::normal(const Vec3& point) const
{
  add_performance_counter(PerformanceCounter::normal_calls);
  if (exact_torus_) return exact_torus_->normal(point);
  if (circular_completeness_) {
    const auto closest=circular_detail::nearest(*circular_completeness_,point,
      data_.characteristic_length);
    return normalized(point-closest.center);
  }
  circular_detail::unresolved("nonconstant or elliptical sections are unsupported");
}

DistanceResult CompiledSweptSplineSurface::distance_reference(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  add_performance_counter(PerformanceCounter::distance_calls);
  add_performance_counter(PerformanceCounter::global_reference_calls);
  if (coincident) add_performance_counter(PerformanceCounter::coincident_cases);
  [[maybe_unused]] ScopedDistanceTimer timer;
  if (exact_torus_) {
    const auto result = exact_torus_->distance(origin, direction, coincident, options);
    add_performance_counter(result.found ? PerformanceCounter::accepted_roots
                                         : PerformanceCounter::no_hit_returns);
    if (result.found) record_residual(result.residual, data_.characteristic_length);
    return result;
  }
  const double direction_norm = norm(direction);
  if (!(direction_norm > 0.0)) {
    throw std::invalid_argument("Ray direction must be non-zero");
  }
  const Vec3 u = direction / direction_norm;
  const auto interval = bounds_.ray_interval(origin, u);
  if (!interval) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {};
  }
  double t_min = std::max(0.0, interval->enter);
  const double push = 8.0 * options.absolute_t_tolerance;
  if (coincident || std::abs(evaluate(origin)) <= options.absolute_f_tolerance)
    t_min = std::max(t_min, push);
  if (!(interval->exit > t_min)) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {};
  }
  const auto function = [&](double t) { return evaluate(origin + t * u); };
  const auto derivative = [&](double t) {
    const double h = std::sqrt(std::numeric_limits<double>::epsilon())
                     * data_.characteristic_length;
    return (function(t + h) - function(t - h)) / (2.0 * h);
  };
  const auto root = find_nearest_root_reference(
    function, derivative, t_min, interval->exit, options);
  if (!root.found) {
    add_performance_counter(PerformanceCounter::no_hit_returns);
    return {false, std::numeric_limits<double>::infinity(),
      RootKind::sign_change, std::numeric_limits<double>::infinity(),
      root.diagnostics};
  }
  add_performance_counter(PerformanceCounter::accepted_roots);
  record_residual(root.root.residual, data_.characteristic_length);
  return {true, root.root.t, root.root.kind, root.root.residual,
    root.diagnostics};
}

DistanceResult CompiledSweptSplineSurface::distance(
  const Vec3& origin, const Vec3& direction, bool coincident,
  const RootSearchOptions& options) const
{
  add_performance_counter(PerformanceCounter::distance_calls);
  if (coincident) add_performance_counter(PerformanceCounter::coincident_cases);
  [[maybe_unused]] ScopedDistanceTimer timer;
  if (exact_torus_) {
    return exact_torus_->distance(origin, direction, coincident, options);
  }
  if (circular_completeness_) return circular_detail::distance(
    *circular_completeness_,origin,direction,coincident,options,data_.characteristic_length);
  circular_detail::unresolved("nonconstant or elliptical sections are unsupported");
}

} // namespace stellarcsg
