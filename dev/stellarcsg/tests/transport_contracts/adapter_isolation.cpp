// Compile actual adapters and collection traversal against controlled members.
// This is NOT a native OpenMC transport or spline-solver qualification test.
#include "openmc/surface_periodic_spline.h"
#include "openmc/surface_swept_spline.h"
#include "openmc/settings.h"
#include "openmc/hdf5_interface.h"
#include "stellarcsg/compiled_swept_surface_set.hpp"

#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

namespace {
using namespace stellarcsg;
std::string observed;
int failures=0;
int checks=0;
std::string output_file;

std::string number(double value) {
  if(std::isinf(value)) return value>0?"+infinity":"-infinity";
  if(std::isnan(value)) return "NaN";
  std::ostringstream out; out<<std::setprecision(17)<<value; return out.str();
}
std::string quoted(const std::string& s) {
  std::string out="\"";
  for(char c:s) {
    if(c=='\"'||c=='\\') out+='\\';
    if(c=='\n') out+="\\n"; else out+=c;
  }
  return out+'\"';
}
SweptSplineSurfaceData member(int id, Vec3 center={},double r=1,
  TestFault fault=TestFault::none) {
  return {id,"member-"+std::to_string(id),center,r,fault};
}
pugi::xml_node single() {
  return {{{"id","901"},{"data_file","sub/../payload.h5"},
    {"dataset","/member"},{"content_id","member-7"},{"units","cm"}}};
}
pugi::xml_node collection() {
  return {{{"id","902"},{"data_file","payload.h5"},
    {"dataset_prefix","/members/"},{"dataset_start","10"},
    {"dataset_count","2"},{"units","cm"}}};
}
pugi::xml_node indexed_collection() {
  return {{{"id","903"},{"data_file","payload.h5"},
    {"dataset_prefix","/members/"},{"dataset_indices","30 10"},
    {"units","cm"}}};
}
void reset() {
  observed.clear(); test_calls.clear(); test_reads.clear(); test_payloads.clear();
  test_payloads["/member"]=member(7);
  test_payloads["/members/010"]=member(7);
  test_payloads["/members/011"]=member(42,{4,0,0});
  test_payloads["/members/030"]=member(99,{8,0,0});
  openmc::settings::path_input="/fixture/input";
}
template<class F> bool throws_any(F f) {
  try { f(); } catch(const std::exception& e) { observed=e.what(); return true; }
  observed="accepted without exception"; return false;
}
template<class F> bool unresolved(F f,int id=7) {
  try { f(); } catch(const UnresolvedTestError& e) {
    observed=std::string(e.what())+" member="+std::to_string(e.member);
    return e.member==id;
  }
  observed="no unresolved exception"; return false;
}
void check(const std::string& name,const std::string& blocker,
  const std::function<bool()>& f) {
  reset(); bool ok=false;
  try { ok=f(); } catch(const std::exception& e) { observed="unexpected: "+std::string(e.what()); }
  ++checks; if(!ok) ++failures;
  std::cout<<"{\"case\":"<<quoted(name)<<",\"passed\":"<<(ok?"true":"false")
    <<",\"observed\":"<<quoted(observed)<<",\"block_code\":"
    <<(ok?"null":quoted(blocker))<<"}\n";
}
}
int main(int argc,char** argv) {
  if(argc!=2) { std::cerr<<"usage: adapter_isolation OUTPUT.h5\n"; return 2; }
  output_file=argv[1];
  check("single_signed_classification","BLOCKED_CLASSIFICATION",[] {
    openmc::SurfaceSweptSpline s(single());
    return s.evaluate({0,0,0})==-1 && s.evaluate({1,0,0})==0 && s.evaluate({2,0,0})==3;
  });
  check("single_distance_normal_consistency","BLOCKED_DISTANCE_NORMAL",[] {
    openmc::SurfaceSweptSpline s(single());
    const auto d=s.distance({2,0,0},{-1,0,0},false);
    const auto p=openmc::Position{2-d,0,0}; const auto n=s.normal(p);
    observed="distance="+number(d)+" evaluate(hit)="+number(s.evaluate(p));
    return d==1 && s.evaluate(p)==0 && n.x==1 && n.y==0 && n.z==0;
  });
  check("single_inside_exit","BLOCKED_INSIDE_EXIT",[] {
    openmc::SurfaceSweptSpline s(single()); return s.distance({0,0,0},{1,0,0},false)==1;
  });
  check("geometric_origin_contact_outward","BLOCKED_ORIGIN_CONTACT",[] {
    openmc::SurfaceSweptSpline s(single()); return s.distance({1,0,0},{1,0,0},false)==0;
  });
  check("tracking_origin_suppression_outward","BLOCKED_TRACKING_POLICY",[] {
    openmc::SurfaceSweptSpline s(single()); return std::isinf(s.distance({1,0,0},{1,0,0},true));
  });
  check("geometric_origin_contact_inward","BLOCKED_ORIGIN_CONTACT",[] {
    openmc::SurfaceSweptSpline s(single()); return s.distance({1,0,0},{-1,0,0},false)==0;
  });
  check("tracking_origin_suppression_keeps_far_exit","BLOCKED_TRACKING_POLICY",[] {
    openmc::SurfaceSweptSpline s(single()); return s.distance({1,0,0},{-1,0,0},true)==2;
  });
  check("origin_tangent_contact_vs_tracking","BLOCKED_TANGENCY_POLICY",[] {
    openmc::SurfaceSweptSpline s(single());
    return s.distance({1,0,0},{0,1,0},false)==0 && std::isinf(s.distance({1,0,0},{0,1,0},true));
  });
  check("positive_near_origin_hit_not_removed_by_adapter","BLOCKED_TRACKING_POLICY",[] {
    openmc::SurfaceSweptSpline s(single()); const auto e=std::ldexp(1.0,-20);
    return s.distance({1+e,0,0},{-1,0,0},true)==e;
  });
  check("single_direction_positive_scaling","BLOCKED_DIRECTION_SCALING",[] {
    openmc::SurfaceSweptSpline s(single());
    for(double k:{0.25,1.0,8.0}) if(s.distance({2,0,0},{-k,0,0},false)!=1) return false;
    return true;
  });
  check("nonzero_direction_required","BLOCKED_DIRECTION_VALIDATION",[] {
    openmc::SurfaceSweptSpline s(single()); return throws_any([&]{s.distance({2,0,0},{0,0,0},false);});
  });
  check("nonfinite_direction_required","BLOCKED_DIRECTION_VALIDATION",[] {
    openmc::SurfaceSweptSpline s(single());
    return throws_any([&]{s.distance({2,0,0},{std::numeric_limits<double>::infinity(),0,0},false);});
  });
  check("rigid_translation_and_axis_rotation","BLOCKED_TRANSFORM",[] {
    test_payloads["/member"]=member(7,{3,4,5});
    openmc::SurfaceSweptSpline s(single());
    const auto d=s.distance({3,6,5},{0,-1,0},false); const auto n=s.normal({3,5,5});
    return d==1 && s.evaluate({3,5,5})==0 && n.x==0 && n.y==1 && n.z==0;
  });
  check("negative_finite_positive_infinite_bounds","BLOCKED_BOUNDS",[] {
    openmc::SurfaceSweptSpline s(single()); const auto b=s.bounding_box(false),p=s.bounding_box(true);
    return b.min.x==-1 && b.max.x==1 && b.min.y==-1 && b.max.z==1
      && std::isinf(p.min.x) && p.min.x<0 && std::isinf(p.max.z) && p.max.z>0;
  });
  check("relative_input_path_resolution","BLOCKED_PATH",[] {
    openmc::SurfaceSweptSpline s(single()); observed=test_reads.at(0).first;
    return observed=="/fixture/input/payload.h5";
  });
  check("collection_finite_member_dataset_window","BLOCKED_FINITE_SELECTION",[] {
    openmc::SurfaceSweptSpline s(collection());
    return test_reads.size()==2 && test_reads[0].second=="/members/010"
      && test_reads[1].second=="/members/011" && s.distance({-2,0,0},{1,0,0},false)==1;
  });
  check("collection_union_disjoint_classification","BLOCKED_UNION_CLASSIFICATION",[] {
    openmc::SurfaceSweptSpline s(collection());
    return s.evaluate({0,0,0})<0 && s.evaluate({4,0,0})<0 && s.evaluate({2,0,0})>0;
  });
  check("member_id_not_vector_or_dataset_index","BLOCKED_MEMBER_ID",[] {
    CompiledSweptSplineSurfaceSet s({member(42,{4,0,0}),member(7)});
    const auto hit=s.distance({-2,0,0},{1,0,0},false);
    observed="id="+std::to_string(hit.coil_id)+" index="+std::to_string(hit.coil_index);
    return hit.root.found && hit.root.distance==1 && hit.coil_id==7 && hit.coil_index==1;
  });
  check("bvh_member_attribution_after_partition","BLOCKED_MEMBER_ID",[] {
    CompiledSweptSplineSurfaceSet s({member(42,{4,0,0}),member(99,{-4,0,0}),member(7)});
    const auto hit=s.distance({-6,0,0},{1,0,0},false);
    return hit.root.distance==1 && hit.coil_id==99 && hit.coil_index==1;
  });
  check("empty_member_set_rejected","BLOCKED_EMPTY_SET",[] {
    return throws_any([]{ CompiledSweptSplineSurfaceSet s({}); });
  });
  check("missing_dataset_rejected","BLOCKED_XML_SELECTOR",[] {
    auto n=single(); n.attrs.erase("dataset"); return throws_any([&]{openmc::SurfaceSweptSpline s(n);});
  });
  check("single_plus_complete_collection_rejected","BLOCKED_XML_SELECTOR",[] {
    auto n=single(); n.attrs["dataset_prefix"]="/members/"; n.attrs["dataset_count"]="2";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);});
  });
  check("single_plus_partial_collection_rejected","BLOCKED_PARTIAL_SELECTOR",[] {
    auto n=single(); n.attrs["dataset_prefix"]="/members/";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);});
  });
  check("dataset_count_must_consume_entire_integer","BLOCKED_SELECTOR_INTEGER",[] {
    auto n=collection(); n.attrs["dataset_count"]="2garbage";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);});
  });
  check("duplicate_member_ids_rejected","BLOCKED_DUPLICATE_ID",[] {
    return throws_any([]{CompiledSweptSplineSurfaceSet s({member(7),member(7,{4,0,0})});});
  });
  check("coincident_ownership_stable_under_permutation","BLOCKED_BOUNDARY_OWNERSHIP",[] {
    // Proposed bookkeeping owner=min(stable member IDs), not a unique normal proof.
    const auto a=member(42,{-1,0,0}),b=member(7,{1,0,0});
    CompiledSweptSplineSurfaceSet ab({a,b}),ba({b,a});
    const auto x=ab.distance({0,0,0},{0,1,0},false);
    const auto y=ba.distance({0,0,0},{0,1,0},false);
    observed="owners="+std::to_string(x.coil_id)+","+std::to_string(y.coil_id);
    return x.coil_id==7 && y.coil_id==7;
  });
  check("true_overlap_not_an_exterior_union_hit","BLOCKED_MATERIAL_OVERLAP",[] {
    CompiledSweptSplineSurfaceSet s({member(7,{},2),member(42,{1,0,0},2)});
    const auto hit=s.distance({0,0,0},{1,0,0},false);
    observed="distance="+number(hit.root.distance)+" union_value="+number(s.evaluate({hit.root.distance,0,0}))+" expected_exit=3";
    return hit.root.found && hit.root.distance==3 && s.evaluate({3,0,0})==0;
  });
  check("indexed_collection_selects_exact_members_in_order","BLOCKED_EXPLICIT_SELECTION",[] {
    openmc::SurfaceSweptSpline s(indexed_collection());
    return test_reads.size()==2 && test_reads[0].second=="/members/030"
      && test_reads[1].second=="/members/010"
      && s.distance({-2,0,0},{1,0,0},false)==1;
  });
  check("indexed_collection_binds_ordered_member_ids","BLOCKED_COLLECTION_IDENTITY",[] {
    auto n=indexed_collection();
    n.attrs["member_content_ids"]="member-99 member-7";
    openmc::SurfaceSweptSpline s(n);
    return test_reads.size()==2 && test_reads[0].second=="/members/030"
      && test_reads[1].second=="/members/010";
  });
  check("indexed_collection_rejects_swapped_member_ids","BLOCKED_COLLECTION_IDENTITY",[] {
    auto n=indexed_collection();
    n.attrs["member_content_ids"]="member-7 member-99";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);})
      && test_reads.size()==1;
  });
  check("indexed_collection_rejects_wrong_id_count","BLOCKED_COLLECTION_IDENTITY",[] {
    auto n=indexed_collection(); n.attrs["member_content_ids"]="member-99";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);})
      && test_reads.empty();
  });
  check("indexed_collection_rejects_duplicate_indices","BLOCKED_EXPLICIT_SELECTION",[] {
    auto n=indexed_collection(); n.attrs["dataset_indices"]="10 10";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);}) && test_reads.empty();
  });
  check("indexed_collection_rejects_invalid_index","BLOCKED_EXPLICIT_SELECTION",[] {
    auto n=indexed_collection(); n.attrs["dataset_indices"]="10 -1";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);}) && test_reads.empty();
  });
  check("indexed_collection_rejects_mixed_window","BLOCKED_EXPLICIT_SELECTION",[] {
    auto n=indexed_collection(); n.attrs["dataset_count"]="2";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);}) && test_reads.empty();
  });
  check("masked_entry_then_same_member_exterior_exit","BLOCKED_UNION_REENTRY",[] {
    // The first A root is inside B; B's exit is then inside A.  A's second
    // root is the first union exterior boundary.
    CompiledSweptSplineSurfaceSet s({member(7,{3,0,0},2),member(42,{},4)});
    const auto hit=s.distance({0,0,0},{1,0,0},false);
    observed="distance="+number(hit.root.distance)+" id="+std::to_string(hit.coil_id);
    return hit.root.found && hit.root.distance==5 && hit.coil_id==7
      && s.evaluate({5,0,0})==0;
  });
  check("distance_exception_preserved_single","BLOCKED_EXCEPTION",[] {
    test_payloads["/member"].fault=TestFault::distance_exception;
    openmc::SurfaceSweptSpline s(single()); return unresolved([&]{s.distance({-2,0,0},{1,0,0},false);});
  });
  check("classification_exception_preserved_single","BLOCKED_EXCEPTION",[] {
    test_payloads["/member"].fault=TestFault::evaluate_exception;
    openmc::SurfaceSweptSpline s(single()); return unresolved([&]{s.evaluate({1,0,0});});
  });
  check("normal_exception_preserved_single","BLOCKED_EXCEPTION",[] {
    test_payloads["/member"].fault=TestFault::normal_exception;
    openmc::SurfaceSweptSpline s(single()); return unresolved([&]{s.normal({1,0,0});});
  });
  check("distance_exception_preserved_collection","BLOCKED_EXCEPTION",[] {
    test_payloads["/members/010"].fault=TestFault::distance_exception;
    openmc::SurfaceSweptSpline s(collection()); return unresolved([&]{s.distance({-2,0,0},{1,0,0},false);});
  });
  check("returned_unresolved_not_single_no_hit","BLOCKED_TERMINAL_STATUS",[] {
    test_payloads["/member"].fault=TestFault::returned_unresolved;
    openmc::SurfaceSweptSpline s(single());
    try { observed="distance="+number(s.distance({-2,0,0},{1,0,0},false)); }
    catch(const std::exception&) {return true;} return false;
  });
  check("historical_unresolved_count_can_be_resolved","BLOCKED_TERMINAL_STATUS",[] {
    test_payloads["/member"].fault=TestFault::resolved_historical;
    openmc::SurfaceSweptSpline s(single());
    return s.distance({-2,0,0},{1,0,0},false)==1;
  });
  check("earlier_returned_unresolved_not_farther_hit","BLOCKED_TERMINAL_STATUS",[] {
    test_payloads["/members/010"].fault=TestFault::returned_unresolved;
    openmc::SurfaceSweptSpline s(collection());
    try { observed="distance="+number(s.distance({-2,0,0},{1,0,0},false)); }
    catch(const std::exception&) {return true;} return false;
  });
  check("nonfinite_hit_rejected","BLOCKED_INVALID_HIT",[] {
    test_payloads["/member"].fault=TestFault::nan_hit;
    openmc::SurfaceSweptSpline s(single());
    try { observed="distance="+number(s.distance({-2,0,0},{1,0,0},false)); }
    catch(const std::exception&) {return true;} return false;
  });
  check("periodic_solver_dispatch","BLOCKED_DISPATCH",[] {
    auto n=single(); n.attrs["solver"]="reference";
    openmc::SurfacePeriodicSpline ref(n); const auto a=ref.distance({2,0,0},{-1,0,0},false);
    const bool first=test_solver_path=="reference";
    n.attrs["solver"]="layered"; openmc::SurfacePeriodicSpline fast(n);
    const auto b=fast.distance({2,0,0},{-1,0,0},false);
    return a==1 && b==1 && first && test_solver_path=="layered";
  });
  check("periodic_exception_preserved","BLOCKED_EXCEPTION",[] {
    test_payloads["/member"].fault=TestFault::distance_exception;
    openmc::SurfacePeriodicSpline s(single()); return unresolved([&]{s.distance({-2,0,0},{1,0,0},false);});
  });
  check("periodic_returned_unresolved_not_no_hit","BLOCKED_TERMINAL_STATUS",[] {
    test_payloads["/member"].fault=TestFault::returned_unresolved;
    openmc::SurfacePeriodicSpline s(single());
    try { observed="distance="+number(s.distance({-2,0,0},{1,0,0},false)); }
    catch(const std::exception&) {return true;} return false;
  });
  check("invalid_units_rejected","BLOCKED_UNITS",[] {
    auto n=single(); n.attrs["units"]="m";
    return throws_any([&]{openmc::SurfaceSweptSpline s(n);})
      && throws_any([&]{openmc::SurfacePeriodicSpline s(n);});
  });
  check("unsupported_periodic_policy_rejected","BLOCKED_POLICY",[] {
    auto n=single(); n.attrs["solver"]="invented";
    return throws_any([&]{openmc::SurfacePeriodicSpline s(n);});
  });
  check("source_options_not_inflated_by_adapter","BLOCKED_OPTIONS",[] {
    openmc::SurfaceSweptSpline s(single()); s.distance({2,0,0},{-1,0,0},false);
    const auto o=test_calls.back().options;
    openmc::SurfacePeriodicSpline p(single()); p.distance({2,0,0},{-1,0,0},false);
    const auto q=test_calls.back().options;
    return o.initial_subdivisions==48 && o.max_refinement_levels==6
      && q.initial_subdivisions==96 && q.max_refinement_levels==7
      && o.absolute_t_tolerance==1e-11 && q.absolute_t_tolerance==1e-11;
  });
  check("negative_dataset_start_rejected","BLOCKED_SELECTOR_INTEGER",[] {
    auto node=collection(); node.attrs["dataset_start"]="-1";
    return throws_any([&] { openmc::SurfaceSweptSpline s(node); }) && test_reads.empty();
  });
  check("overflowing_dataset_range_rejected","BLOCKED_SELECTOR_INTEGER",[] {
    auto node=collection(); node.attrs["dataset_start"]="2147483647";
    return throws_any([&] { openmc::SurfaceSweptSpline s(node); }) && test_reads.empty();
  });
  check("single_plus_start_rejected","BLOCKED_PARTIAL_SELECTOR",[] {
    auto node=single(); node.attrs["dataset_start"]="0";
    return throws_any([&] { openmc::SurfaceSweptSpline s(node); });
  });
  check("empty_collection_rejected","BLOCKED_SELECTOR_INTEGER",[] {
    auto node=collection(); node.attrs["dataset_count"]="0";
    return throws_any([&] { openmc::SurfaceSweptSpline s(node); });
  });
  check("periodic_nonfinite_hit_rejected","BLOCKED_INVALID_HIT",[] {
    test_payloads["/member"].fault=TestFault::nan_hit;
    openmc::SurfacePeriodicSpline s(single());
    return throws_any([&] { (void)s.distance({2,0,0},{-1,0,0},false); });
  });
  check("nonfinite_member_hit_not_collection_no_hit","BLOCKED_INVALID_MEMBER_HIT",[] {
    test_payloads["/members/010"].fault=TestFault::nan_hit;
    openmc::SurfaceSweptSpline s(collection());
    return throws_any([&] { (void)s.distance({-2,0,0},{1,0,0},false); });
  });
  check("adapter_serialization_real_hdf5_file","BLOCKED_SERIALIZATION",[] {
    const hid_t f=H5Fcreate(output_file.c_str(),H5F_ACC_TRUNC,H5P_DEFAULT,H5P_DEFAULT);
    if(f<0) return false;
    openmc::SurfaceSweptSpline s(single()),c(collection());
    auto pn=single(); pn.attrs["solver"]="reference"; openmc::SurfacePeriodicSpline p(pn);
    int i=901;
    for(const openmc::Surface* item:std::vector<const openmc::Surface*>{&s,&c,&p}) {
      const auto label="surface "+std::to_string(i++);
      const hid_t g=H5Gcreate2(f,label.c_str(),H5P_DEFAULT,H5P_DEFAULT,H5P_DEFAULT);
      openmc::write_string(g,"name","analytic-contract-fixture",false);
      openmc::write_string(g,"boundary_type","transmission",false);
      item->to_hdf5_inner(g); H5Gclose(g);
    }
    openmc::SurfaceSweptSpline indexed(indexed_collection());
    const hid_t indexed_group=H5Gcreate2(f,"surface 904",H5P_DEFAULT,
      H5P_DEFAULT,H5P_DEFAULT);
    indexed.to_hdf5_inner(indexed_group);
    const bool shape=H5Lexists(indexed_group,"dataset_indices",H5P_DEFAULT)>0
      && H5Lexists(indexed_group,"dataset_count",H5P_DEFAULT)==0
      && H5Lexists(indexed_group,"member_content_ids",H5P_DEFAULT)>0;
    const hid_t indices=H5Dopen2(indexed_group,"dataset_indices",H5P_DEFAULT);
    const hid_t indices_type=indices>=0 ? H5Dget_type(indices) : -1;
    char values[5]{};
    const bool bytes=indices_type>=0 && H5Dread(indices,indices_type,
      H5S_ALL,H5S_ALL,H5P_DEFAULT,values)>=0
      && std::string(values,5)=="30 10";
    if(indices_type>=0) H5Tclose(indices_type);
    if(indices>=0) H5Dclose(indices);
    H5Gclose(indexed_group);
    const auto rc=H5Fclose(f); observed=output_file;
    return rc>=0 && shape && bytes;
  });
  std::cerr<<"checks="<<checks<<" passed="<<checks-failures<<" failed="<<failures
    <<" evidence=actual-adapters-with-test-doubles; native-transport=NOT_RUN\n";
  return failures?1:0;
}
