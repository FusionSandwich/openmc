#include "openmc/damage.h"

#include <cmath>

namespace openmc {

//==============================================================================
// Damage model implementation
//==============================================================================

double lindhard_partition(double E, int Z_R, int A_R, int Z_L, int A_L)
{
  if (E <= 0.0 || Z_R <= 0 || A_R <= 0 || Z_L <= 0 || A_L <= 0)
    return 0.0;

  double zr23 = std::pow(Z_R, 2.0 / 3.0);
  double zl23 = std::pow(Z_L, 2.0 / 3.0);
  double zsum = zr23 + zl23;
  double asum = A_R + A_L;

  double E_L =
    30.724 * Z_R * Z_L * std::sqrt(zsum) * asum / A_L;
  double F_L = 0.0793 * zr23 *
               std::sqrt(Z_L * asum * asum * asum /
                         (std::pow(A_R, 3) * A_L)) /
               std::pow(zsum, 0.75);
  double eps = E / E_L;
  double g = 3.4008 * std::pow(eps, 1.0 / 6.0) +
             0.40244 * std::pow(eps, 0.75) + eps;

  return E / (1.0 + F_L * g);
}

} // namespace openmc
