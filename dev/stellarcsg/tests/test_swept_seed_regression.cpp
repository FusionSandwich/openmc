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
  return failures ? 1 : 0;
}
