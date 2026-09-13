// Replays original binary64 controls/rays prepared from an immutable JSONL capture.
// Geometry rejection is a per-case BLOCKED result, never a removed test case.
#define main historical_adversarial_main
#include "test_swept_adversarial.cpp"
#undef main
#include <fstream>
#include <memory>
#include <stdexcept>

int main(int argc, char** argv)
{
  if (argc != 2) return 64;
  std::ifstream input(argv[1]);
  if (!input) return 66;
  const auto number = [&]() {
    std::string token;
    if (!(input >> token)) throw std::runtime_error("truncated replay input");
    std::size_t used = 0;
    const double value = std::stod(token, &used);
    if (used != token.size() || !std::isfinite(value))
      throw std::runtime_error("invalid replay binary64 value");
    return value;
  };
  const auto vector = [&]() { const double x=number(), y=number(), z=number(); return Vec3{x,y,z}; };
  std::cout << std::setprecision(17);
  int failed=0, blocked=0, total=0;
  int shapes;
  input >> shapes;
  for (int s=0; s<shapes; ++s) {
    int shape, count, rays;
    input >> shape >> count >> rays;
    auto data=make_data(shape);
    if (count != static_cast<int>(data.sample_count)) throw std::runtime_error("sample count drift");
    const double radius=number();
    data.major_radius_coefficients.assign(count,radius);
    data.minor_radius_coefficients.assign(count,radius);
    for (int i=0;i<count;++i) {
      const auto p=vector();
      data.centerline_coefficients[3*i]=p.x;
      data.centerline_coefficients[3*i+1]=p.y;
      data.centerline_coefficients[3*i+2]=p.z;
    }
    std::cout << "{\"kind\":\"geometry\",\"shape\":" << shape
      << ",\"radius\":" << radius << ",\"controls\":[";
    for (int i=0;i<count;++i) {
      if (i) std::cout << ',';
      print_vec({data.centerline_coefficients[3*i],data.centerline_coefficients[3*i+1],data.centerline_coefficients[3*i+2]});
    }
    std::cout << "]}\n";
    auto rigid=data;
    const Vec3 translation{11,-7,3};
    for (int i=0;i<count;++i) {
      const auto p=rotate({data.centerline_coefficients[3*i],data.centerline_coefficients[3*i+1],data.centerline_coefficients[3*i+2]})+translation;
      const auto n=rotate({0,0,1});
      rigid.centerline_coefficients[3*i]=p.x; rigid.centerline_coefficients[3*i+1]=p.y; rigid.centerline_coefficients[3*i+2]=p.z;
      rigid.normal_coefficients[3*i]=n.x; rigid.normal_coefficients[3*i+1]=n.y; rigid.normal_coefficients[3*i+2]=n.z;
    }
    std::unique_ptr<stellarcsg::CompiledSweptSplineSurface> coil, transformed;
    std::string geometry_error;
    try {
      coil=std::make_unique<stellarcsg::CompiledSweptSplineSurface>(data,true);
      transformed=std::make_unique<stellarcsg::CompiledSweptSplineSurface>(rigid,true);
    } catch (const std::exception& error) { geometry_error=error.what(); }
    for (int j=0;j<rays;++j) {
      int index; input >> index;
      const auto point=vector(), direction=vector();
      ++total;
      std::cout << "{\"kind\":\"ray\",\"shape\":" << shape << ",\"index\":" << index << ",\"origin\":";
      print_vec(point); std::cout << ",\"direction\":"; print_vec(direction);
      try {
        if (!geometry_error.empty()) throw std::runtime_error(geometry_error);
        const auto hit=coil->distance(point,direction,false);
        const auto scaled=coil->distance(point,2*direction,false);
        const auto moved=transformed->distance(rotate(point)+translation,rotate(direction),false);
        bool pass=hit.found==scaled.found && hit.found==moved.found;
        if (hit.found && pass) pass=std::abs(hit.distance-scaled.distance)<2e-8 && std::abs(hit.distance-moved.distance)<2e-8;
        if (index==8 && shape<=1) pass=pass && hit.found && hit.distance<=.002+2e-10;
        if (!pass) ++failed;
        const auto distance=[](const stellarcsg::DistanceResult& value) {
          if (value.found && std::isfinite(value.distance)) std::cout << value.distance;
          else std::cout << "null";
        };
        std::cout << ",\"found\":" << (hit.found?"true":"false") << ",\"distance\":"; distance(hit);
        std::cout << ",\"scaled_distance\":"; distance(scaled);
        std::cout << ",\"rigid_distance\":"; distance(moved);
        std::cout << ",\"state\":\"" << (pass?"PASS":"FAIL") << "\"";
      } catch (const std::exception& error) {
        ++blocked;
        std::cout << ",\"distance\":null,\"rigid_distance\":null,\"state\":\"BLOCKED\",\"block_stage\":\""
          << (geometry_error.empty()?"query":"geometry_certificate") << "\",\"error\":";
        print_error(error.what());
      }
      std::cout << "}\n" << std::flush;
    }
  }
  std::cerr << "rays=" << total << " failures=" << failed << " blocked=" << blocked << '\n';
  return failed?1:blocked?2:0;
}
