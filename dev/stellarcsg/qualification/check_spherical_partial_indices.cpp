// Supplemental point-index controls; no claim about partial-mesh ray traversal.
#define main full_sphere_regression
#include "check_spherical_equator.cpp"
#undef main

int main()
{
  if (full_sphere_regression() != 0)
    return 1;
  checks = 0;
  try {
    for (bool north : {false, true}) {
      std::ostringstream xml;
      xml << std::setprecision(17)
          << "<mesh id='988' type='spherical'><r_grid>0 200</r_grid>"
          << "<theta_grid>" << (north ? 0. : openmc::PI / 2) << ' '
          << (north ? openmc::PI / 2 : openmc::PI)
          << "</theta_grid><phi_grid>0 " << openmc::PI
          << "</phi_grid><origin>0 0 0</origin></mesh>";
      pugi::xml_document document;
      require(document.load_string(xml.str().c_str()), "partial mesh XML");
      openmc::SphericalMesh mesh(document.child("mesh"));
      for (double z : {-1e-18, 1e-18}) {
        const bool theta_inside = north == (z > 0.);
        bool inside;
        auto indices = mesh.get_indices({120., 1., z}, inside);
        require(
          inside == theta_inside, "partial theta admits wrong hemisphere");
        require(indices[1] == (theta_inside ? 1 : 0),
          "partial theta index ownership");
        mesh.get_indices({220., 1., z}, inside);
        require(!inside, "equator classification admits radial exterior");
        mesh.get_indices({120., -1., z}, inside);
        require(!inside, "equator classification admits phi exterior");
      }
    }
    std::cout << "{\"state\":\"PASS\",\"partial_index_checks\":" << checks
              << "}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAILED after " << checks
              << " partial checks: " << error.what() << '\n';
    return 1;
  }
}
