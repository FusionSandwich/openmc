// Absolute-cost control for OpenMC's native ZTorus quartic query kernel.
// This does not compare to swept geometry and makes no qualification claim.
#include "openmc/surface.h"

#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
constexpr double PI = 3.1415926535897932384626433832795;
constexpr double A = 5.0;
constexpr double B = .25;
constexpr double C = .25;

struct Ray { double x, y, z, u, v, w; };

Ray unit_ray(double x, double y, double z, double u, double v, double w)
{
  const double norm = std::sqrt(u*u + v*v + w*w);
  if (!(norm > 0.) || !std::isfinite(norm)) throw std::logic_error("nonunit ray fixture");
  return {x, y, z, u/norm, v/norm, w/norm};
}

std::array<Ray, 64> frozen_bank()
{
  std::array<Ray, 64> bank {};
  // Four deterministic 16-ray strata: radial crossings, internal exits,
  // tangent-neighborhood controls, and broad misses.  Directions are made
  // unit here before any query, and no bank member depends on a result.
  for (int i = 0; i < 16; ++i) {
    const double q = 2.*PI*i/16.;
    const double cx = A*std::cos(q), cy = A*std::sin(q);
    bank[static_cast<std::size_t>(i)] = unit_ray(1.35*cx, 1.35*cy, .03*std::sin(2*q),
      -std::cos(q), -std::sin(q), .02*std::cos(q));
    bank[static_cast<std::size_t>(16 + i)] = unit_ray(cx, cy, .05*std::cos(3*q),
      std::cos(q), std::sin(q), .15*std::sin(q));
    bank[static_cast<std::size_t>(32 + i)] = unit_ray(cx - 2.*std::sin(q),
      cy + 2.*std::cos(q), B + (i - 8)*1.e-10, std::sin(q), -std::cos(q), 0.);
    bank[static_cast<std::size_t>(48 + i)] = unit_ray(9.*std::cos(q), 9.*std::sin(q),
      1.5 + .1*std::sin(q), -std::sin(q), std::cos(q), .05);
  }
  return bank;
}
}

int main(int argc, char** argv)
{
  int banks = 10000;
  for (int i = 1; i < argc; ++i) {
    if (std::string(argv[i]) != "--banks" || ++i >= argc)
      throw std::invalid_argument("usage: native_torus_query_control [--banks positive]");
    banks = std::stoi(argv[i]);
  }
  if (banks < 1) throw std::invalid_argument("banks must be positive");
  const auto bank = frozen_bank();
  volatile double checksum = 0.;
  const auto started = std::chrono::steady_clock::now();
  for (int repeat = 0; repeat < banks; ++repeat)
    for (const auto& ray : bank) {
      const double distance = openmc::torus_distance(ray.x, ray.y, ray.z, ray.u, ray.v, ray.w,
        A, B, C, false);
      checksum += std::isfinite(distance) ? distance : 0.;
    }
  const auto ended = std::chrono::steady_clock::now();
  const auto total_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(ended - started).count();
  const double query_count = static_cast<double>(banks)*bank.size();
  std::cout << std::setprecision(17)
    << "{\"kind\":\"native_ztorus_absolute_control\",\"banks\":" << banks
    << ",\"count\":" << bank.size() << ",\"queries\":" << query_count
    << ",\"ns_per_query\":" << total_ns/query_count
    << ",\"checksum\":" << checksum
    << ",\"geometry\":{\"x0\":0,\"y0\":0,\"z0\":0,\"A\":" << A
    << ",\"B\":" << B << ",\"C\":" << C << "}}\n";
}
