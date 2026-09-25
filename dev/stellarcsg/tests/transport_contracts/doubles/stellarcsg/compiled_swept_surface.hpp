#pragma once
// Deliberately substitutes analytic member geometry, not production coil math.
#include "stellarcsg/periodic_radial_surface.hpp"
#include <algorithm>
#include <cmath>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
namespace stellarcsg {
struct UnresolvedTestError : std::runtime_error {
  int member;
  explicit UnresolvedTestError(int id) : std::runtime_error("UNRESOLVED_TEST"),member(id) {}
};
enum class TestFault { none, distance_exception, evaluate_exception,
  normal_exception, returned_unresolved, nan_hit };
struct SweptSplineSurfaceData {
  int coil_id=0;
  std::string content_id="test-content-id";
  Vec3 center{};
  double radius=1.0;
  TestFault fault=TestFault::none;
};
struct TestCall { int id; Vec3 origin, direction; bool coincident; RootSearchOptions options; };
inline std::vector<TestCall> test_calls;
inline std::vector<std::pair<std::string,std::string>> test_reads;
inline std::map<std::string,SweptSplineSurfaceData> test_payloads;
inline std::string test_solver_path;
class CompiledSweptSplineSurface {
public:
  explicit CompiledSweptSplineSurface(SweptSplineSurfaceData d) : data_(std::move(d)) {
    const Vec3 r{data_.radius,data_.radius,data_.radius};
    bounds_={data_.center-r,data_.center+r};
  }
  double evaluate(const Vec3& p) const {
    if(data_.fault==TestFault::evaluate_exception) throw UnresolvedTestError(data_.coil_id);
    return norm_squared(p-data_.center)-data_.radius*data_.radius;
  }
  Vec3 normal(const Vec3& p) const {
    if(data_.fault==TestFault::normal_exception) throw UnresolvedTestError(data_.coil_id);
    return normalized(p-data_.center);
  }
  DistanceResult distance(const Vec3& p,const Vec3& u,bool coincident,
    const RootSearchOptions& opts={}) const {
    test_calls.push_back({data_.coil_id,p,u,coincident,opts});
    if(data_.fault==TestFault::distance_exception) throw UnresolvedTestError(data_.coil_id);
    DistanceResult out;
    if(data_.fault==TestFault::returned_unresolved) {
      out.root_diagnostics.unresolved_intervals=1;
      out.root_diagnostics.fallback_reason=SolverFallbackReason::interval_budget_exhausted;
      return out;
    }
    if(data_.fault==TestFault::nan_hit) {
      out.found=true; out.distance=std::numeric_limits<double>::quiet_NaN(); return out;
    }
    const auto v=normalized(u);
    const auto q=p-data_.center;
    const auto b=dot(q,v);
    const auto c=dot(q,q)-data_.radius*data_.radius;
    const auto discr=b*b-c;
    if(discr<0) return out;
    const auto root=std::sqrt(discr);
    for(const double t : {-b-root,-b+root}) {
      if(t<0 || (coincident && t==0.0)) continue;
      out.found=true; out.distance=t; out.residual=0;
      out.kind=discr==0?RootKind::stationary_tangent:RootKind::sign_change;
      return out;
    }
    return out;
  }
  const BoundingBox& bounding_box() const noexcept { return bounds_; }
private:
  SweptSplineSurfaceData data_;
  BoundingBox bounds_;
};
inline SweptSplineSurfaceData read_test_payload(const std::string& file,
  const std::string& group,const std::string& expected) {
  test_reads.emplace_back(file,group);
  auto data=test_payloads.at(group);
  if(!expected.empty() && data.content_id!=expected)
    throw std::runtime_error("test reader: content ID mismatch");
  return data;
}
}
