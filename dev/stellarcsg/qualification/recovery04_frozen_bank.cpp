// Frozen, unique-query replay harness.  It is deliberately outside production.
// The CSV is the compatibility contract: do not regenerate it when comparing
// implementations.  `distance_reference` is reported separately, never used
// to overwrite a candidate result.
#include "stellarcsg/compiled_swept_surface.hpp"
#include "stellarcsg/performance_counters.hpp"
#include "stellarcsg/sha256.hpp"
#include "stellarcsg/swept_coefficient_file.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using stellarcsg::Vec3;
using Clock = std::chrono::steady_clock;
constexpr double pi = 3.1415926535897932384626433832795;

struct Query {
  std::string id, geometry, coefficient_hash, source_sha256, category, expected, group;
  bool heldout {false};
  double expected_distance {NAN};
  Vec3 origin {}, direction {};
};

std::string hash_data(const stellarcsg::SweptSplineSurfaceData& data)
{
  // FNV-1a is a stable identifier, not a cryptographic attestation.
  std::uint64_t h = 1469598103934665603ULL;
  const auto add = [&h](const void* p, std::size_t n) {
    const auto* b = static_cast<const unsigned char*>(p);
    for (std::size_t i = 0; i < n; ++i) { h ^= b[i]; h *= 1099511628211ULL; }
  };
  add(&data.coil_id, sizeof(data.coil_id));
  for (const auto* values : {&data.centerline_coefficients,
         &data.normal_coefficients, &data.binormal_coefficients,
         &data.major_radius_coefficients, &data.minor_radius_coefficients}) {
    for (double value : *values) add(&value, sizeof(value));
  }
  std::ostringstream out; out << std::hex << h; return out.str();
}

std::string file_sha256(const std::string& filename)
{
  std::ifstream in {filename, std::ios::binary};
  if (!in) throw std::runtime_error("cannot hash source fixture: " + filename);
  stellarcsg::Sha256 hash;
  std::array<char, 4096> buffer {};
  while (in.read(buffer.data(), buffer.size()) || in.gcount())
    hash.update(buffer.data(), static_cast<std::size_t>(in.gcount()));
  return hash.hex_digest();
}

stellarcsg::SweptSplineSurfaceData torus_data(bool rigid)
{
  stellarcsg::SweptSplineSurfaceData data;
  data.coil_id = rigid ? 9041 : 9040;
  data.sample_count = 64; data.length = 2*pi*5.; data.characteristic_length = 5.;
  data.major_radius_coefficients.assign(data.sample_count, .25);
  data.minor_radius_coefficients.assign(data.sample_count, .25);
  for (std::size_t i = 0; i < data.sample_count; ++i) {
    const double a = 2*pi*i/data.sample_count;
    Vec3 c {5*std::cos(a), 5*std::sin(a), 0};
    Vec3 n {0, 0, 1};
    Vec3 b {std::cos(a), std::sin(a), 0};
    if (rigid) { // 3-4-5 rotation about y plus translation.
      c = {0.6*c.x - .8*c.z + 11, c.y - 7, .8*c.x + .6*c.z + 3};
      n = {0.6*n.x - .8*n.z, n.y, .8*n.x + .6*n.z};
      b = {0.6*b.x - .8*b.z, b.y, .8*b.x + .6*b.z};
    }
    for (double x : {c.x,c.y,c.z}) data.centerline_coefficients.push_back(x);
    for (double x : {n.x,n.y,n.z}) data.normal_coefficients.push_back(x);
    for (double x : {b.x,b.y,b.z}) data.binormal_coefficients.push_back(x);
  }
  return data;
}

void write_header(std::ostream& out)
{
  out << "id,geometry,coefficient_hash,source_sha256,category,heldout,expected,expected_distance,group,ox,oy,oz,dx,dy,dz\n";
}

void write_query(std::ostream& out, const Query& q)
{
  out << q.id << ',' << q.geometry << ',' << q.coefficient_hash << ',' << q.source_sha256 << ',' << q.category
      << ',' << (q.heldout ? 1 : 0) << ',' << q.expected << ',';
  if (std::isfinite(q.expected_distance)) out << std::setprecision(17) << q.expected_distance;
  out << ',' << q.group << ',' << q.origin.x << ',' << q.origin.y << ',' << q.origin.z
      << ',' << q.direction.x << ',' << q.direction.y << ',' << q.direction.z << '\n';
}

Query make_query(const std::string& id, const std::string& category, Vec3 o, Vec3 d,
  const std::string& hash, bool heldout = false, std::string expected = "expected_hit",
  double distance = NAN, std::string group = {})
{
  return {id, "torus", hash, "", category, expected, group, heldout, distance, o, d};
}

int freeze_bank(const std::string& filename, const std::string& wistell_file,
  const std::string& wistell_dataset)
{
  if (wistell_file.empty()) throw std::runtime_error("--freeze requires --wistell-h5 for real coil031 rays");
  const auto torus_hash = hash_data(torus_data(false));
  const auto rigid_hash = hash_data(torus_data(true));
  const auto wistell = stellarcsg::read_swept_spline_surface_hdf5(wistell_file, wistell_dataset);
  const auto wistell_hash = hash_data(wistell);
  const auto wistell_source_sha = file_sha256(wistell_file);
  std::ofstream out {filename};
  if (!out) throw std::runtime_error("cannot write frozen bank: " + filename);
  out << std::setprecision(17); write_header(out);
  const double knot_radius = 5.0*(2.0/3.0 + std::cos(2*pi/64.0)/3.0);
  const std::array<Query, 16> anchors {{
    make_query("a00", "clear_miss", {0,0,4}, {1,0,0}, torus_hash, false, "expected_miss"),
    make_query("a01", "transverse", {7,0,0}, {-1,0,0}, torus_hash, false, "reference_required"),
    make_query("a02", "inside", {knot_radius,0,0}, {1,0,0}, torus_hash, false, "reference_required"),
    // These two roots use the cardinal-cubic knot value, not the control polygon.
    make_query("a03", "near_entry_002", {knot_radius+.252,0,0}, {-1,0,0}, torus_hash, false, "expected_hit", .002),
    make_query("a04", "near_entry_502", {knot_radius+.752,0,0}, {-1,0,0}, torus_hash, false, "expected_hit", .502),
    make_query("a05", "competing_roots", {-8,0,0}, {1,0,0}, torus_hash, false, "reference_required"),
    make_query("a06", "seam", {knot_radius+.25,0,0}, {0,1,0}, torus_hash, false, "reference_required"),
    // The q=0 centerline tangent is +y.  At z=minor_radius this is a
    // tangency of the spline tube itself, unlike a radial x-axis crossing.
    make_query("a07", "grazing", {knot_radius,-2,.25001}, {0,1,0}, torus_hash, false, "reference_required"),
    make_query("a08", "tangent", {knot_radius,-2,.25}, {0,1,0}, torus_hash, false, "reference_required"),
    make_query("a09", "direction_scaling", {7,0,0}, {-2,0,0}, torus_hash, false, "reference_required", NAN, "scale_1"),
    make_query("a10", "direction_scaling", {7,0,0}, {-4,0,0}, torus_hash, false, "reference_required", NAN, "scale_2"),
    make_query("a11", "rigid_transform", {15.2,-7,8.6}, {-0.6,0,-.8}, rigid_hash, false, "reference_required", NAN, "rigid_base"),
    make_query("a12", "coincident_out", {knot_radius+.25,0,0}, {1,0,0}, torus_hash, false, "reference_required"),
    make_query("a13", "coincident_in", {knot_radius+.25,0,0}, {-1,0,0}, torus_hash, false, "reference_required"),
    make_query("a14", "near_tangent_plus", {knot_radius,-2,.2500001}, {0,1,0}, torus_hash, false, "reference_required"),
    make_query("a15", "near_tangent_minus", {knot_radius,-2,.2499999}, {0,1,0}, torus_hash, false, "reference_required")
  }};
  for (auto q : anchors) {
    if (q.id == "a11") q.geometry = "torus_rigid";
    if (q.id == "a01") q.group = "rigid_base";
    write_query(out, q);
  }
  std::uint64_t state = 0x4a535245434f5634ULL;
  const auto uniform = [&state] { state = state*6364136223846793005ULL + 1442695040888963407ULL;
    return static_cast<double>(state >> 11)/9007199254740992.0; };
  for (int i = 0; i < 136; ++i) {
    const double a = 2*pi*uniform(), z = 1.8*(uniform()-.5), r = 6. + 2*uniform();
    Vec3 o {r*std::cos(a), r*std::sin(a), z};
    Vec3 d {-std::cos(a)+.11*(uniform()-.5), -std::sin(a)+.11*(uniform()-.5), .2*(uniform()-.5)};
    write_query(out, make_query("h" + std::to_string(i), "heldout_unique", o, d, torus_hash, true,
      "reference_required"));
  }
  const auto box = stellarcsg::CompiledSweptSplineSurface {wistell, true}.bounding_box();
  const Vec3 c {(box.lower.x+box.upper.x)/2, (box.lower.y+box.upper.y)/2,
    (box.lower.z+box.upper.z)/2};
  const std::array<Vec3, 8> directions {{{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1},{1,1,.2},{-1,.3,1}}};
  for (std::size_t i = 0; i < directions.size(); ++i) {
    const Vec3 d = directions[i];
    const double reach = 2.5*std::max({box.upper.x-box.lower.x,
      box.upper.y-box.lower.y, box.upper.z-box.lower.z});
    Query q {"w"+std::to_string(i), "wistell_coil031", wistell_hash, wistell_source_sha, "wistell_coil031_real",
      "reference_required", "", true, NAN, c - reach*stellarcsg::normalized(d), d};
    write_query(out, q);
  }
  return 0;
}

std::vector<std::string> split(const std::string& line)
{ std::vector<std::string> fields; std::stringstream s {line}; std::string f; while (std::getline(s,f,',')) fields.push_back(f); return fields; }

std::vector<Query> read_bank(const std::string& filename)
{
  std::ifstream in {filename}; std::string line; std::vector<Query> bank;
  if (!std::getline(in, line)) throw std::runtime_error("empty bank: " + filename);
  while (std::getline(in, line)) { const auto f = split(line); if (f.size() != 15) throw std::runtime_error("malformed frozen row");
    Query q; q.id=f[0]; q.geometry=f[1]; q.coefficient_hash=f[2]; q.source_sha256=f[3]; q.category=f[4]; q.heldout=f[5]=="1"; q.expected=f[6];
    q.expected_distance=f[7].empty()?NAN:std::stod(f[7]); q.group=f[8]; q.origin={std::stod(f[9]),std::stod(f[10]),std::stod(f[11])}; q.direction={std::stod(f[12]),std::stod(f[13]),std::stod(f[14])}; bank.push_back(q); }
  if (bank.size() != 160) throw std::runtime_error("frozen bank must contain exactly 160 unique queries"); return bank;
}

void number_or_null(double x) { if (std::isfinite(x)) std::cout << x; else std::cout << "null"; }
void counter_or_null(bool available, std::uint64_t value)
{ if (available) std::cout << value; else std::cout << "null"; }
const char* disposition_name(stellarcsg::DistanceDisposition disposition)
{
  switch (disposition) {
  case stellarcsg::DistanceDisposition::hit: return "hit";
  case stellarcsg::DistanceDisposition::no_hit: return "no_hit";
  case stellarcsg::DistanceDisposition::unresolved: return "unresolved";
  }
  return "invalid";
}

int replay_bank(const std::string& filename, const std::string& wistell_file,
  const std::string& wistell_dataset, bool with_reference)
{
  const auto bank = read_bank(filename); const auto plain = torus_data(false), rigid = torus_data(true);
  std::map<std::string, stellarcsg::CompiledSweptSplineSurface> surfaces;
  // Separate instances make each timed operation cold with respect to the
  // thread-local one-entry evaluate cache while retaining identical payloads.
  std::map<std::string, stellarcsg::CompiledSweptSplineSurface> evaluators, normalizers;
  std::map<std::string, std::string> coefficient_hashes;
  surfaces.emplace("torus", stellarcsg::CompiledSweptSplineSurface {plain, true});
  surfaces.emplace("torus_rigid", stellarcsg::CompiledSweptSplineSurface {rigid, true});
  evaluators.emplace("torus", stellarcsg::CompiledSweptSplineSurface {plain, true});
  evaluators.emplace("torus_rigid", stellarcsg::CompiledSweptSplineSurface {rigid, true});
  normalizers.emplace("torus", stellarcsg::CompiledSweptSplineSurface {plain, true});
  normalizers.emplace("torus_rigid", stellarcsg::CompiledSweptSplineSurface {rigid, true});
  coefficient_hashes.emplace("torus", hash_data(plain));
  coefficient_hashes.emplace("torus_rigid", hash_data(rigid));
  if (!wistell_file.empty()) {
    const auto wistell = stellarcsg::read_swept_spline_surface_hdf5(wistell_file, wistell_dataset);
    coefficient_hashes.emplace("wistell_coil031", hash_data(wistell));
    surfaces.emplace("wistell_coil031", stellarcsg::CompiledSweptSplineSurface {wistell, true});
    evaluators.emplace("wistell_coil031", stellarcsg::CompiledSweptSplineSurface {wistell, true});
    normalizers.emplace("wistell_coil031", stellarcsg::CompiledSweptSplineSurface {wistell, true});
  }
  const std::string wistell_source_sha = wistell_file.empty() ? "" : file_sha256(wistell_file);
  int candidate_failures=0, reference_disagreements=0, blocked=0;
  const bool counters_available = stellarcsg::performance_counters_enabled();
  std::cout << std::setprecision(17);
  for (std::size_t query_index = 0; query_index < bank.size(); ++query_index) {
    const auto& q = bank[query_index];
    const std::string surface_key = q.geometry == "torus_rigid" ? "torus_rigid" : q.geometry;
    auto it = surfaces.find(surface_key); if (it == surfaces.end() || coefficient_hashes[surface_key] != q.coefficient_hash || (q.geometry == "wistell_coil031" && q.source_sha256 != wistell_source_sha)) { ++blocked; std::cout << "{\"kind\":\"query\",\"id\":\"" << q.id << "\",\"state\":\"BLOCKED\",\"reason\":\"surface_unavailable_or_coefficient_or_fixture_hash_mismatch\"}\n"; continue; }
    auto& surface = it->second; const auto before = stellarcsg::performance_counters_snapshot();
    bool candidate_blocked=false, reference_blocked=false, evaluate_blocked=false, normal_blocked=false;
    std::string candidate_error, reference_error, evaluate_error, normal_error;
    stellarcsg::DistanceResult candidate {}, reference {};
    double distance_ns=NAN, reference_ns=NAN, evaluate_ns=NAN, normal_ns=NAN;
    try { auto t=Clock::now(); candidate=surface.distance(q.origin,q.direction,q.category.find("coincident_") == 0); distance_ns=std::chrono::duration<double,std::nano>(Clock::now()-t).count(); }
    catch (const std::exception& e) { candidate_blocked=true; candidate_error=e.what(); ++blocked; }
    if (!candidate_blocked && candidate.disposition()
          == stellarcsg::DistanceDisposition::unresolved) {
      candidate_blocked=true;
      candidate_error="terminal_unresolved";
      ++blocked;
    }
    const auto after_candidate = stellarcsg::performance_counters_snapshot();
    try {
      // A distinct point per query keeps the one-entry evaluation cache from
      // turning evaluate/normal timing into a repeated-origin measurement.
      const double offset = 1.0e-3*static_cast<double>(query_index + 1);
      const Vec3 evaluate_point = q.origin + Vec3 {offset, -2*offset, 3*offset};
      const auto t=Clock::now(); (void)evaluators.at(surface_key).evaluate(evaluate_point); evaluate_ns=std::chrono::duration<double,std::nano>(Clock::now()-t).count();
    } catch (const std::exception& e) { evaluate_blocked=true; evaluate_error=e.what(); }
    try {
      const Vec3 normal_point = candidate.found ? q.origin + candidate.distance*stellarcsg::normalized(q.direction) : q.origin;
      const auto t=Clock::now(); (void)normalizers.at(surface_key).normal(normal_point); normal_ns=std::chrono::duration<double,std::nano>(Clock::now()-t).count();
    } catch (const std::exception& e) { normal_blocked=true; normal_error=e.what(); }
    if (with_reference) try { const auto t=Clock::now(); reference=surface.distance_reference(q.origin,q.direction,q.category.find("coincident_") == 0); reference_ns=std::chrono::duration<double,std::nano>(Clock::now()-t).count(); }
    catch (const std::exception& e) { reference_blocked=true; reference_error=e.what(); }
    bool candidate_ok=!candidate_blocked;
    if (!candidate_blocked && q.expected=="expected_hit") candidate_ok=candidate.found;
    if (!candidate_blocked && q.expected=="expected_miss") candidate_ok=!candidate.found;
    if (!candidate_blocked && std::isfinite(q.expected_distance) && candidate.found)
      candidate_ok=candidate_ok && std::abs(candidate.distance-q.expected_distance) <= 3e-7*std::max(1.,q.expected_distance);
    if (!candidate_ok && !candidate_blocked) ++candidate_failures;
    bool reference_ok=with_reference && !candidate_blocked && !reference_blocked && candidate.found==reference.found;
    if (reference_ok && candidate.found) reference_ok=std::abs(candidate.distance-reference.distance)<=2e-8;
    if (with_reference && !reference_ok && !candidate_blocked && !reference_blocked) ++reference_disagreements;
    std::cout << "{\"kind\":\"query\",\"id\":\"" << q.id << "\",\"category\":\"" << q.category
      << "\",\"heldout\":" << (q.heldout?"true":"false") << ",\"coefficient_hash\":\"" << q.coefficient_hash << "\",\"source_sha256\":\"" << q.source_sha256
      << "\",\"expected\":\"" << q.expected << "\",\"candidate_disposition\":\"" << disposition_name(candidate.disposition()) << "\",\"candidate_found\":" << (candidate.found?"true":"false") << ",\"candidate_distance\":"; number_or_null(candidate.found?candidate.distance:NAN);
    std::cout << ",\"reference_available\":" << (with_reference?"true":"false") << ",\"reference_found\":" << (reference.found?"true":"false") << ",\"reference_distance\":"; number_or_null(with_reference && reference.found?reference.distance:NAN);
    std::cout << ",\"candidate_distance_ns\":"; number_or_null(distance_ns); std::cout << ",\"reference_distance_ns\":"; number_or_null(reference_ns); std::cout << ",\"evaluate_ns\":"; number_or_null(evaluate_ns); std::cout << ",\"normal_ns\":"; number_or_null(normal_ns);
    std::cout << ",\"candidate_ok\":" << (candidate_ok?"true":"false") << ",\"reference_agrees\":"; if (with_reference && !reference_blocked) std::cout << (reference_ok?"true":"false"); else std::cout << "null"; std::cout << ",\"counter_distance_calls\":"; counter_or_null(counters_available, after_candidate.distance_calls-before.distance_calls); std::cout << ",\"counter_cache_hits\":"; counter_or_null(counters_available, after_candidate.cache_hits-before.cache_hits); std::cout << ",\"counter_cache_misses\":"; counter_or_null(counters_available, after_candidate.cache_misses-before.cache_misses); std::cout << ",\"candidate_spans\":"; counter_or_null(counters_available, after_candidate.candidate_patches_or_segments-before.candidate_patches_or_segments); std::cout << ",\"candidate_newton\":"; counter_or_null(counters_available, after_candidate.newton_iterations-before.newton_iterations); std::cout << ",\"candidate_subdivision\":"; counter_or_null(counters_available, after_candidate.local_subdivision_nodes-before.local_subdivision_nodes);
    std::cout << ",\"candidate_state\":\"" << (candidate_blocked?"BLOCKED":candidate_ok?"PASS":"FAIL") << "\",\"reference_state\":\"" << (!with_reference?"SKIPPED":reference_blocked?"BLOCKED":reference_ok?"AGREE":"DISAGREE") << "\",\"telemetry_state\":\"" << (evaluate_blocked || normal_blocked?"BLOCKED":"PASS") << "\"";
    if (candidate_blocked) std::cout << ",\"candidate_error\":\"" << candidate_error << "\""; if (reference_blocked) std::cout << ",\"reference_error\":\"" << reference_error << "\""; if (evaluate_blocked) std::cout << ",\"evaluate_error\":\"" << evaluate_error << "\""; if (normal_blocked) std::cout << ",\"normal_error\":\"" << normal_error << "\""; std::cout << ",\"state\":\"" << (candidate_blocked?"BLOCKED":candidate_ok?"PASS":"FAIL") << "\"}\n";
  }
  std::cout << "{\"kind\":\"summary\",\"query_count\":160,\"candidate_failures\":" << candidate_failures << ",\"candidate_nearest_failures\":" << candidate_failures << ",\"reference_disagreements\":" << reference_disagreements << ",\"blocked\":" << blocked << ",\"cache_policy\":\"unique_queries_fresh_process\",\"claim\":\"bounded_replay_not_completeness\"}\n";
  return candidate_failures ? 1 : blocked ? 2 : 0;
}

} // namespace

int main(int argc, char** argv)
{
  try { std::string mode, bank, h5, dataset="/coils/coil_031"; bool with_reference=true;
    for (int i=1;i<argc;++i) { const std::string a=argv[i]; if (a=="--freeze"||a=="--replay") { if (++i == argc) throw std::runtime_error("missing bank path"); mode=a; bank=argv[i]; } else if (a=="--wistell-h5") { if (++i == argc) throw std::runtime_error("missing HDF5 path"); h5=argv[i]; } else if (a=="--wistell-dataset") { if (++i == argc) throw std::runtime_error("missing dataset"); dataset=argv[i]; } else if (a=="--skip-reference") with_reference=false; else if (a=="--with-reference") with_reference=true; else throw std::runtime_error("unknown argument: "+a); }
    if (mode=="--freeze") return freeze_bank(bank,h5,dataset); if (mode=="--replay") return replay_bank(bank,h5,dataset,with_reference);
    throw std::runtime_error("usage: recovery04_frozen_bank --freeze BANK --wistell-h5 FILE | --replay BANK [--wistell-h5 FILE]");
  } catch (const std::exception& e) { std::cerr << "recovery04: " << e.what() << '\n'; return 2; }
}
