// Audit binary64 rotate/translate operations from test_swept_adversarial.cpp.
// Input: kind(C=control,O=origin,D=direction) shape index x y z.
// Output uses hexfloat so every resulting binary64 value is retained exactly.
#include <iomanip>
#include <iostream>
int main()
{
  char kind;
  int shape, index;
  double x, y, z;
  while (std::cin >> kind >> shape >> index >> x >> y >> z) {
    const double rx = 0.6*x - 0.8*z;
    const double ry = y;
    const double rz = 0.8*x + 0.6*z;
    std::cout << kind << ' ' << shape << ' ' << index << ' ' << std::hexfloat
      << (kind == 'D' ? rx : rx+11.) << ' '
      << (kind == 'D' ? ry : ry-7.) << ' '
      << (kind == 'D' ? rz : rz+3.) << '\n';
  }
  return std::cin.eof() ? 0 : 1;
}
