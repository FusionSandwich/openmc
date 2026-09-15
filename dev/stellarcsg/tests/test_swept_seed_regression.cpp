// A known hit exists at .002 cm; this is not a completeness certificate.
#define main retained_adversarial_main
#include "test_swept_adversarial.cpp"
#undef main

int main()
{
  int failures = 0;
  for (int shape : {0, 1}) {
    const auto data = make_data(shape);
    const stellarcsg::CompiledSweptSplineSurface coil {data, true};
    const auto point = sample(data, 0) + Vec3 {.252, 0, 0};
    for (double scale : {.5, 1., 2.}) {
      const auto hit = coil.distance(point, Vec3 {-scale, 0, 0}, false);
      const bool pass =
        hit.found && hit.distance > 0 && hit.distance <= .002 + 2e-10;
      std::cout << std::setprecision(17) << "shape=" << shape
                << " scale=" << scale << " distance=" << hit.distance
                << " pass=" << pass << '\n';
      failures += pass ? 0 : 1;
    }
  }
  const auto torus_data = make_data(0);
  const stellarcsg::CompiledSweptSplineSurface torus {torus_data, true};
  const double knot_radius = sample(torus_data, 0).x;
  const auto near_tangent = torus.distance(
    Vec3 {knot_radius, -2, .2499999}, Vec3 {0, 1, 0}, false);
  const double expected_near_tangent = 1.9527658734094704;
  const bool near_tangent_pass = near_tangent.found
    && std::abs(near_tangent.distance - expected_near_tangent) <= 2e-8;
  std::cout << std::setprecision(17)
            << "a15 distance=" << near_tangent.distance
            << " pass=" << near_tangent_pass << '\n';
  failures += near_tangent_pass ? 0 : 1;

  bool tangent_unresolved = false;
  try {
    (void) torus.distance(
      Vec3 {knot_radius, -2, .25}, Vec3 {0, 1, 0}, false);
  } catch (const std::runtime_error& error) {
    tangent_unresolved = std::string {error.what()}.find(
      "Swept query unresolved") != std::string::npos;
  }
  std::cout << "a08 unresolved=" << tangent_unresolved << '\n';
  failures += tangent_unresolved ? 0 : 1;
  return failures ? 1 : 0;
}
