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
    make_query("a07", "grazing", {3, -.25,0}, {1,0,0}, torus_hash, false, "reference_required"),
    make_query("a08", "tangent", {3, .25,0}, {1,0,0}, torus_hash, false, "reference_required"),
    make_query("a09", "direction_scaling", {7,0,0}, {-2,0,0}, torus_hash, false, "reference_required", NAN, "scale_1"),
    make_query("a10", "direction_scaling", {7,0,0}, {-4,0,0}, torus_hash, false, "reference_required", NAN, "scale_2"),
    make_query("a11", "rigid_transform", {15.2,-7,8.6}, {-0.6,0,-.8}, rigid_hash, false, "reference_required", NAN, "rigid_base"),
    make_query("a12", "coincident_out", {knot_radius+.25,0,0}, {1,0,0}, torus_hash, false, "reference_required"),
    make_query("a13", "coincident_in", {knot_radius+.25,0,0}, {-1,0,0}, torus_hash, false, "reference_required"),
    make_query("a14", "near_tangent_plus", {3,.2500001,0}, {1,0,0}, torus_hash, false, "reference_required"),
    make_query("a15", "near_tangent_minus", {3,.2499999,0}, {1,0,0}, torus_hash, false, "reference_required")
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

int replay_bank(const std::string& filename, const std::string& wistell_file, const std::string& wistell_dataset)
{
  const auto bank = read_bank(filename); const auto plain = torus_data(false), rigid = torus_data(true);
  std::map<std::string, stellarcsg::CompiledSweptSplineSurface> surfaces;
  surfaces.emplace("torus", stellarcsg::CompiledSweptSplineSurface {plain, true});
  surfaces.emplace("torus_rigid", stellarcsg::CompiledSweptSplineSurface {rigid, true});
  if (!wistell_file.empty()) surfaces.emplace("wistell_coil031", stellarcsg::CompiledSweptSplineSurface {
    stellarcsg::read_swept_spline_surface_hdf5(wistell_file, wistell_dataset), true});
  const std::string wistell_source_sha = wistell_file.empty() ? "" : file_sha256(wistell_file);
  int candidate_failures=0, reference_disagreements=0, blocked=0;
  std::cout << std::setprecision(17);
  for (const auto& q : bank) {
    const std::string surface_key = q.geometry == "torus_rigid" ? "torus_rigid" : q.geometry;
    auto it = surfaces.find(surface_key); if (it == surfaces.end() || (q.geometry == "wistell_coil031" && q.source_sha256 != wistell_source_sha)) { ++blocked; std::cout << "{\"kind\":\"query\",\"id\":\"" << q.id << "\",\"state\":\"BLOCKED\",\"reason\":\"surface_unavailable_or_fixture_hash_mismatch\"}\n"; continue; }
    auto& surface = it->second; const auto before = stellarcsg::performance_counters_snapshot();
    bool threw=false; std::string error; stellarcsg::DistanceResult candidate {}, reference {};
    double distance_ns=NAN, reference_ns=NAN, evaluate_ns=NAN, normal_ns=NAN;
    try {
      auto t=Clock::now(); candidate=surface.distance(q.origin,q.direction,false); distance_ns=std::chrono::duration<double,std::nano>(Clock::now()-t).count();
      t=Clock::now(); reference=surface.distance_reference(q.origin,q.direction,false); reference_ns=std::chrono::duration<double,std::nano>(Clock::now()-t).count();
      t=Clock::now(); (void)surface.evaluate(q.origin); evaluate_ns=std::chrono::duration<double,std::nano>(Clock::now()-t).count();
      const Vec3 p=candidate.found ? q.origin+candidate.distance*q.direction : q.origin;
      t=Clock::now(); (void)surface.normal(p); normal_ns=std::chrono::duration<double,std::nano>(Clock::now()-t).count();
    } catch (const std::exception& e) { threw=true; error=e.what(); ++blocked; }
    const auto after=stellarcsg::performance_counters_snapshot(); bool candidate_ok=!threw;
    if (!threw && q.expected=="expected_hit") candidate_ok=candidate.found;
    if (!threw && q.expected=="expected_miss") candidate_ok=!candidate.found;
    if (!threw && std::isfinite(q.expected_distance) && candidate.found)
      candidate_ok=candidate_ok && std::abs(candidate.distance-q.expected_distance) <= 3e-7*std::max(1.,q.expected_distance);
    if (!candidate_ok && !threw) ++candidate_failures;
    bool reference_ok=!threw && candidate.found==reference.found;
    if (reference_ok && candidate.found) reference_ok=std::abs(candidate.distance-reference.distance)<=3e-7*std::max(1.,reference.distance);
    if (!reference_ok && !threw) ++reference_disagreements;
    std::cout << "{\"kind\":\"query\",\"id\":\"" << q.id << "\",\"category\":\"" << q.category
      << "\",\"heldout\":" << (q.heldout?"true":"false") << ",\"coefficient_hash\":\"" << q.coefficient_hash << "\",\"source_sha256\":\"" << q.source_sha256
      << "\",\"expected\":\"" << q.expected << "\",\"candidate_found\":" << (candidate.found?"true":"false") << ",\"candidate_distance\":"; number_or_null(candidate.found?candidate.distance:NAN);
    std::cout << ",\"reference_found\":" << (reference.found?"true":"false") << ",\"reference_distance\":"; number_or_null(reference.found?reference.distance:NAN);
    std::cout << ",\"candidate_distance_ns\":"; number_or_null(distance_ns); std::cout << ",\"reference_distance_ns\":"; number_or_null(reference_ns); std::cout << ",\"evaluate_ns\":"; number_or_null(evaluate_ns); std::cout << ",\"normal_ns\":"; number_or_null(normal_ns);
    std::cout << ",\"candidate_ok\":" << (candidate_ok?"true":"false") << ",\"reference_agrees\":" << (reference_ok?"true":"false") << ",\"counter_distance_calls\":" << (after.distance_calls-before.distance_calls) << ",\"counter_cache_hits\":" << (after.cache_hits-before.cache_hits) << ",\"counter_cache_misses\":" << (after.cache_misses-before.cache_misses);
    if (threw) std::cout << ",\"state\":\"BLOCKED\",\"reason\":\"" << error << "\""; else std::cout << ",\"state\":\"" << (candidate_ok?"PASS":"FAIL") << "\""; std::cout << "}\n";
  }
  std::cout << "{\"kind\":\"summary\",\"query_count\":160,\"candidate_failures\":" << candidate_failures << ",\"candidate_nearest_failures\":" << candidate_failures << ",\"reference_disagreements\":" << reference_disagreements << ",\"blocked\":" << blocked << ",\"cache_policy\":\"unique_queries_fresh_process\",\"claim\":\"bounded_replay_not_completeness\"}\n";
  return candidate_failures ? 1 : blocked ? 2 : 0;
}

} // namespace

int main(int argc, char** argv)
{
  try { std::string mode, bank, h5, dataset="/coils/coil_031";
    for (int i=1;i<argc;++i) { const std::string a=argv[i]; if (a=="--freeze"||a=="--replay") { mode=a; bank=argv[++i]; } else if (a=="--wistell-h5") h5=argv[++i]; else if (a=="--wistell-dataset") dataset=argv[++i]; else throw std::runtime_error("unknown argument: "+a); }
    if (mode=="--freeze") return freeze_bank(bank,h5,dataset); if (mode=="--replay") return replay_bank(bank,h5,dataset);
    throw std::runtime_error("usage: recovery04_frozen_bank --freeze BANK --wistell-h5 FILE | --replay BANK [--wistell-h5 FILE]");
  } catch (const std::exception& e) { std::cerr << "recovery04: " << e.what() << '\n'; return 2; }
}
