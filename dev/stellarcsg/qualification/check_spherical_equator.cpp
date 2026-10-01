// Deterministic native spherical-mesh equator regression, independent of spline
// geometry.
#include "openmc/constants.h"
#include "openmc/mesh.h"
#include "openmc/position.h"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace {
int checks = 0;
void require(bool condition, const char* message)
{
  ++checks;
  if (!condition)
    throw std::runtime_error(message);
}

openmc::SphericalMesh make_mesh(double angle = openmc::PI / 2,
  openmc::Position origin = {0., 0., 0.}, bool split = true)
{
  std::ostringstream xml;
  xml << std::setprecision(17)
      << "<mesh id='987' type='spherical'><r_grid>0 200</r_grid><theta_grid>0 ";
  if (split)
    xml << angle << ' ';
  xml << openmc::PI << "</theta_grid><phi_grid>0 " << 2 * openmc::PI
      << "</phi_grid><origin>" << origin.x << ' ' << origin.y << ' ' << origin.z
      << "</origin></mesh>";
  pugi::xml_document document;
  require(document.load_string(xml.str().c_str()), "mesh XML");
  return openmc::SphericalMesh(document.child("mesh"));
}
} // namespace

int main()
{
  try {
    auto mesh = make_mesh();
    // This ray's squared-cone discriminant rounds negative in the old code.
    const double norm = std::sqrt(.2 * .2 + .3 * .3 + .3 * .3);
    for (double z : {-.1, .1, -1.3, 1.3}) {
      const openmc::Position r {120., 1., z};
      const openmc::Direction u {
        .2 / norm, .3 / norm, -std::copysign(.3 / norm, z)};
      bool inside;
      auto ijk = mesh.get_indices(r, inside);
      require(inside, "ray outside mesh");
      const double exact = -r.z / u.z;
      const double t =
        mesh.distance_to_grid_boundary(ijk, 1, r, u, 0.).distance;
      require(
        std::abs(t - exact) <= 2e-15, "equator crossing missed or inaccurate");
      require(mesh.distance_to_grid_boundary(ijk, 1, r, u, exact).distance ==
                openmc::INFTY,
        "already traversed equator was repeated");
      openmc::vector<int> bins;
      openmc::vector<double> fractions;
      mesh.bins_crossed(r, r + 2 * exact * u, u, bins, fractions);
      require(
        bins.size() == 2 && bins[0] != bins[1], "equator did not split track");
      require(std::abs(fractions[0] - .5) < 1e-12 &&
                std::abs(fractions[1] - .5) < 1e-12,
        "track fractions not independently equal halves");
    }
    for (double z : {-1e-18, 1e-18}) {
      bool inside;
      const openmc::Position r {120., 1., z};
      const auto ijk = mesh.get_indices(r, inside);
      require(inside && ijk[1] == (z < 0 ? 2 : 1),
        "tiny signed height hemisphere lost");
      const openmc::Direction parallel {1., 0., 0.};
      require(
        mesh.distance_to_grid_boundary(ijk, 1, r, parallel, 0.).distance ==
          openmc::INFTY,
        "parallel ray crossed equator");
      const openmc::Direction grazing {1., 0., -std::copysign(1e-20, z)};
      const double t =
        mesh.distance_to_grid_boundary(ijk, 1, r, grazing, 0.).distance;
      require(std::abs(t - 100.) < 1e-12,
        "tiny nonzero vertical direction discarded");
    }
    const openmc::Position seam {120., 1., 0.};
    bool inside;
    auto ijk = mesh.get_indices(seam, inside);
    require(
      mesh.distance_to_grid_boundary(ijk, 1, seam, {0., 0., 1.}, 0.).distance ==
        openmc::INFTY,
      "coincident origin was counted again");
    auto unsplit = make_mesh(openmc::PI / 2, {}, false);
    require(unsplit
                .distance_to_grid_boundary(
                  {1, 1, 1}, 1, {120., 1., .1}, {0., 0., -1.}, 0.)
                .distance == openmc::INFTY,
      "unsplit theta acquired an equator");
    for (double near : {std::nextafter(openmc::PI / 2, 0.),
           std::nextafter(openmc::PI / 2, openmc::PI)}) {
      auto off = make_mesh(near);
      require(off.distance_to_grid_boundary(
                   {1, 1, 1}, 1, {120., 1., -1e-15}, {1., 0., 1e-16}, 0.)
                  .distance == openmc::INFTY,
        "nearby cone incorrectly used exact-plane specialization");
    }
    auto translated = make_mesh(openmc::PI / 2, {8., -4., 2.});
    openmc::vector<int> bins;
    openmc::vector<double> fractions;
    translated.bins_crossed(
      {128., -3., 2.1}, {128., -3., 1.9}, {0., 0., -1.}, bins, fractions);
    require(bins.size() == 2 && bins[0] != bins[1], "translated equator track");
    require(std::abs(fractions[0] - .5) < 1e-12 &&
              std::abs(fractions[1] - .5) < 1e-12,
      "translated track fractions");
    std::cout << "{\"state\":\"PASS\",\"checks\":" << checks << "}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAILED after " << checks << " checks: " << error.what()
              << '\n';
    return 1;
  }
}
