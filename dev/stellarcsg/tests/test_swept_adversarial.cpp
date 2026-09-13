// Deterministic, independent nearest-projection and metamorphic ray checks.
// A sampled centerline gives an UPPER bound on the true nearest distance:
// exceeding it proves failure; passing does not certify nearest completeness.
#include "stellarcsg/compiled_swept_surface.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace {
using stellarcsg::Vec3;
constexpr double pi = 3.1415926535897932384626433832795;

Vec3 sample(const stellarcsg::SweptSplineSurfaceData& data, double q)
{
  const auto whole = static_cast<long>(std::floor(q));
  const double u = q - std::floor(q);
  const std::array<double, 4> weights {
    std::pow(1-u, 3)/6, (3*u*u*u-6*u*u+4)/6,
    (-3*u*u*u+3*u*u+3*u+1)/6, u*u*u/6};
  Vec3 p {};
  for (long a = 0; a < 4; ++a) {
    const auto n = static_cast<long>(data.sample_count);
    const auto i = static_cast<std::size_t>((whole+a-1+n)%n);
    const Vec3 control {data.centerline_coefficients[3*i],
      data.centerline_coefficients[3*i+1], data.centerline_coefficients[3*i+2]};
    p = p + weights[static_cast<std::size_t>(a)] * control;
  }
  return p;
}

stellarcsg::SweptSplineSurfaceData make_data(int shape)
{
  stellarcsg::SweptSplineSurfaceData data;
  data.coil_id = 71;
  data.sample_count = shape == 2 ? 16 : 64;
  data.length = 10*pi; // Parameter scale, not measured arc length.
  data.characteristic_length = 9;
  data.major_radius_coefficients.assign(data.sample_count, 0.25);
  data.minor_radius_coefficients.assign(data.sample_count, 0.25);
  for (std::size_t i = 0; i < data.sample_count; ++i) {
    const double q = 2*pi*static_cast<double>(i)/data.sample_count;
    const double r = shape == 2 ? 5 + 3*std::cos(5*q) : 5;
    const double z = shape == 0 ? 0 : 0.4*std::sin(3*q);
    for (double value : {r*std::cos(q), r*std::sin(q), z})
      data.centerline_coefficients.push_back(value);
    for (double value : {0., 0., 1.}) data.normal_coefficients.push_back(value);
    for (double value : {1., 0., 0.}) data.binormal_coefficients.push_back(value);
  }
  return data;
}

void print_vec(Vec3 p)
{
  std::cout << '[' << p.x << ',' << p.y << ',' << p.z << ']';
}

Vec3 rotate(Vec3 p)
{
  return {0.6*p.x-0.8*p.z, p.y, 0.8*p.x+0.6*p.z};
}

void print_error(const std::string& error)
{
  std::cout << '"';
  for (char c : error) {
    if (c == '"' || c == '\\') std::cout << '\\' << c;
    else if (c == '\n') std::cout << "\\n";
    else if (c == '\r') std::cout << "\\r";
    else std::cout << c;
  }
  std::cout << '"';
}
}

int main()
{
  std::cout << std::setprecision(17);
  int failures = 0;
  int blocked = 0;
  for (int shape : {0, 1, 2}) {
    const auto data = make_data(shape);
    const stellarcsg::CompiledSweptSplineSurface coil {data, true};
    std::cout << "{\"kind\":\"geometry\",\"shape\":" << shape
      << ",\"radius\":0.25,\"controls\":[";
    for (std::size_t i = 0; i < data.sample_count; ++i) {
      if (i) std::cout << ',';
      print_vec({data.centerline_coefficients[3*i],
        data.centerline_coefficients[3*i+1], data.centerline_coefficients[3*i+2]});
    }
    std::cout << "]}\n";
    auto rigid = data;
    const Vec3 translation {11, -7, 3};
    for (std::size_t i = 0; i < data.sample_count; ++i) {
      const auto center = rotate({data.centerline_coefficients[3*i],
        data.centerline_coefficients[3*i+1], data.centerline_coefficients[3*i+2]})
        + translation;
      rigid.centerline_coefficients[3*i] = center.x;
      rigid.centerline_coefficients[3*i+1] = center.y;
      rigid.centerline_coefficients[3*i+2] = center.z;
      const auto normal = rotate({0, 0, 1});
      rigid.normal_coefficients[3*i] = normal.x;
      rigid.normal_coefficients[3*i+1] = normal.y;
      rigid.normal_coefficients[3*i+2] = normal.z;
    }
    const stellarcsg::CompiledSweptSplineSurface transformed {rigid, true};
    std::vector<Vec3> cloud;
    for (std::size_t i = 0; i < data.sample_count*128; ++i)
      cloud.push_back(sample(data, static_cast<double>(i)/128));
    unsigned long long seed = 0x71c05b31ULL;
    const auto uniform = [&seed]() {
      seed = (1664525ULL*seed + 1013904223ULL) & 0xffffffffULL;
      return static_cast<double>(seed)/4294967296.;
    };
    for (int index = 0; index < 512; ++index) {
      Vec3 point;
      if (index < 128) {
        const auto c = sample(data, data.sample_count*uniform());
        point = c + Vec3 {uniform()-0.5, uniform()-0.5, uniform()-0.5};
      } else {
        point = {18*uniform()-9, 18*uniform()-9, 4*uniform()-2};
      }
      double sampled_squared = 1e300;
      std::size_t nearest = 0;
      for (std::size_t i = 0; i < cloud.size(); ++i) {
        const double d = stellarcsg::norm_squared(point-cloud[i]);
        if (d < sampled_squared) { sampled_squared = d; nearest = i; }
      }
      std::cout << "{\"kind\":\"projection\",\"shape\":" << shape
        << ",\"index\":" << index << ",\"point\":";
      print_vec(point);
      std::cout << ",\"sampled_nearest_point\":";
      print_vec(cloud[nearest]);
      std::cout << ",\"sampled_squared_distance\":" << sampled_squared;
      try {
        const auto local = coil.local_coordinates(point);
        const double actual = stellarcsg::norm_squared(point-local.center);
        const bool pass = actual <= sampled_squared + 1e-10*std::max(1., sampled_squared);
        if (!pass) ++failures;
        std::cout << ",\"returned_squared_distance\":" << actual
          << ",\"state\":\"" << (pass ? "PASS" : "FAIL") << "\"";
      } catch (const std::exception& error) {
        ++blocked;
        std::cout << ",\"state\":\"BLOCKED\",\"error\":";
        print_error(error.what());
      }
      std::cout << "}\n";
      if (index >= 128) continue;
      Vec3 direction = stellarcsg::normalized(cloud[nearest]-point);
      std::string label = "seeded_near_centerline";
      if (index < 7) {
        const auto c = sample(data, static_cast<double>(data.sample_count)/4);
        const std::array<double, 7> offsets {-1e-5, -1e-7, -1e-10,
          0, 1e-10, 1e-7, 1e-5};
        point = c + Vec3 {-2, 0.25 + offsets[static_cast<std::size_t>(index)], 0};
        direction = {1,0,0};
        label = "tangent_ladder";
      } else if (index < 11) {
        const auto c = sample(data, 0);
        if (index == 7) point = c;
        else if (index == 8) point = c + Vec3 {0.252,0,0};
        else if (index == 9) point = {-8,0,0};
        else point = c + Vec3 {0,0,1};
        direction = index == 7 || index == 9 ? Vec3 {1,0,0}
          : index == 8 ? Vec3 {-1,0,0} : Vec3 {0,0,-1};
        label = "inside_proxy_competing_or_vertical";
      }
      std::cout << "{\"kind\":\"ray\",\"shape\":" << shape
        << ",\"index\":" << index << ",\"label\":\"" << label << "\",\"origin\":";
      print_vec(point);
      std::cout << ",\"direction\":";
      print_vec(direction);
      try {
        const auto hit = coil.distance(point, direction, false);
        const auto scaled = coil.distance(point, 2*direction, false);
        const auto moved = transformed.distance(rotate(point)+translation,
          rotate(direction), false);
        bool pass = hit.found == scaled.found && hit.found == moved.found;
        if (hit.found && pass)
          pass = std::abs(hit.distance-scaled.distance) < 2e-8
            && std::abs(hit.distance-moved.distance) < 2e-8;
        // At q=0, symmetry gives c'_x=0. For shapes 0 and 1 the
        // radius-0.25 section therefore contains c(0)+(0.25,0,0).
        // This ray starts at c(0)+(0.252,0,0), heading in -x.
        // Thus a positive surface hit exists at t=0.002 independently of
        // production projection, proxy search, or the polynomial oracle.
        // An even earlier hit would still satisfy this upper-bound test.
        const bool known_hit = index == 8 && shape <= 1;
        if (known_hit)
          pass = pass && hit.found && hit.distance <= 0.002 + 2e-10;
        if (!pass) ++failures;
        std::cout << ",\"found\":" << (hit.found ? "true" : "false")
          << ",\"distance\":";
        if (hit.found && std::isfinite(hit.distance)) std::cout << hit.distance;
        else std::cout << "null";
        std::cout << ",\"scaled_distance\":";
        if (scaled.found && std::isfinite(scaled.distance)) std::cout << scaled.distance;
        else std::cout << "null";
        std::cout << ",\"rigid_distance\":";
        if (moved.found && std::isfinite(moved.distance)) std::cout << moved.distance;
        else std::cout << "null";
        if (known_hit) std::cout << ",\"independent_hit_upper_bound\":0.002";
        std::cout << ",\"state\":\"" << (pass ? "PASS" : "FAIL") << "\"";
      } catch (const std::exception& error) {
        ++blocked;
        std::cout << ",\"state\":\"BLOCKED\",\"error\":";
        print_error(error.what());
      }
      std::cout << "}\n";
    }
  }
  std::cerr << "failures=" << failures << " blocked=" << blocked
    << " projection_samples=1536 rays=384 seed=0x71c05b31\n";
  return failures ? 1 : blocked ? 2 : 0;
}
