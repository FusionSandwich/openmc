// Reuse the immutable fixture parser and constructors, not a production solver.
#define main recovery04_fixture_main
#include "recovery04_frozen_bank.cpp"
#undef main
#include "product05_interval_cover.hpp"

int main(int argc,char** argv)
{
  try {
    if(argc!=3) throw std::invalid_argument("usage: interval-cover bank.csv coils.h5");
    const auto bank=read_bank(argv[1]);
    std::map<std::string,stellarcsg::SweptSplineSurfaceData> data;
    data.emplace("torus",torus_data(false));data.emplace("torus_rigid",torus_data(true));
    data.emplace("wistell_coil031",stellarcsg::read_swept_spline_surface_hdf5(argv[2],"/coils/coil_031"));
    std::map<std::string,product05::StationaryTube> curves;
    for(const auto& item:data) curves.emplace(item.first,product05::compile(item.second));
    const auto source=file_sha256(argv[2]);
    std::cout<<std::setprecision(17);
    for(const auto& q:bank) {
      const auto& shape=data.at(q.geometry);
      if(hash_data(shape)!=q.coefficient_hash || (!q.source_sha256.empty() && source!=q.source_sha256))
        throw std::runtime_error("fixture identity mismatch");
      const auto start=Clock::now();
      // Includes zero deliberately: coincidence association is not implemented.
      const auto result=product05::cover(curves.at(q.geometry),q.origin,q.direction);
      const auto ns=std::chrono::duration<double,std::nano>(Clock::now()-start).count();
      std::cout<<"{\"id\":\""<<q.id<<"\",\"state\":\""<<(result.root_free?"ROOT_FREE":"UNRESOLVED")
        <<"\",\"nodes\":"<<result.nodes<<",\"possible_boxes\":"<<result.possible
        <<",\"earliest_lambda\":";number_or_null(result.earliest_possible);
      std::cout<<",\"probe_ns\":"<<ns<<"}\n";
    }
  } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
