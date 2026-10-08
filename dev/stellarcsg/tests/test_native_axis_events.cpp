// Native deterministic events; external Fraction oracle checks every row/bin.
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include "openmc/capi.h"
#include "openmc/cell.h"
#include "openmc/geometry.h"
#include "openmc/particle.h"
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/tallies/tally.h"
#include "pugixml.hpp"

using namespace openmc;

void bins()
{
  std::cout << ",\"scores\":[";
  for (size_t t = 0; t < model::tallies.size(); ++t) {
    if (t) std::cout << ',';
    std::cout << '[';
    for (int b = 0; b < model::tallies[t]->n_filter_bins(); ++b) {
      if (b) std::cout << ',';
      std::cout << model::tallies[t]->results_(b, 0, 0);
    }
    std::cout << ']';
  }
  std::cout << ']';
}

int main(int argc, char** argv)
{
  if (argc != 3) return 2;
  const auto query_file = std::filesystem::absolute(argv[2]);
  std::filesystem::current_path(argv[1]);
  pugi::xml_document geometry;
  if (!geometry.load_file("geometry.xml")) return 3;
  char name[] = "native-axis-test";
  char* args[] = {name};
  int code = openmc_init(1, args, nullptr);
  if (code) return code;
  code = openmc_simulation_init();
  if (code) return code;
  model::active_tracklength_tallies.clear();
  model::active_surface_tallies.clear();
  for (int i = 0; i < static_cast<int>(model::tallies.size()); ++i) {
    auto& t = *model::tallies[i];
    t.active_ = true;
    if (t.type_ == TallyType::SURFACE) model::active_surface_tallies.push_back(i);
    else model::active_tracklength_tallies.push_back(i);
  }
  std::ifstream input(query_file);
  std::cout << std::setprecision(17);
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty()) continue;
    std::istringstream row(line);
    int id, steps, mode, hint;
    SourceSite source;
    row >> id >> source.r.x >> source.r.y >> source.r.z >> source.u.x >> source.u.y
        >> source.u.z >> hint >> steps >> mode;
    if (!row) return 4;
    source.surf_id = hint;
    source.E = 1.e6;
    for (auto& t : model::tallies) t->reset();
    Particle p;
    std::cout << "ROW {\"id\":" << id << ",\"events\":[";
    bool first = true;
    std::string error;
    try {
      p.from_source(&source);
      p.id() = id;
      if (!exhaustive_find_cell(p)) throw std::runtime_error("NO_START_OWNER");
      if (mode == 3) model::cells[p.coord(0).cell()]->material_[0] = 0;
      if (mode == 4) {
        p.axis_plane_context().reset();
        p.r()[0] = -1.7976931348623157e308;
        // A finite opposite extreme plane forces unrepresentable local length.
        for (auto& s : model::surfaces)
          if (auto* x = dynamic_cast<SurfaceXPlane*>(s.get())) x->x0_ = 1.7976931348623157e308;
        p.u() = {1., 0., 0.};
        Region extreme("-1", 0);
        (void) extreme.distance(p.r(), p.u(), SURFACE_NONE);
        throw std::runtime_error("OVERFLOW_GUARD_DID_NOT_REJECT");
      }
      if (mode == 1) p.u()[p.axis_plane_context().axis] *= -1.; // stale epoch
      if (mode == 2) p.event_collide(); // prohibited before any score
      for (int step = 0; step < steps && p.wgt() > 0.; ++step) {
        const int before = model::cells[p.coord(0).cell()]->id_;
        std::string expression;
        for (auto c : geometry.child("geometry").children("cell"))
          if (c.attribute("id").as_int() == before) expression = c.attribute("region").value();
        Region duplicate("(" + expression + ") | (" + expression + ")", before);
        const auto original = model::cells[p.coord(0).cell()]->distance(p.r(), p.u(), p.surface(), &p);
        const auto complex = duplicate.distance(p.r(), p.u(), p.surface());
        if (settings::experimental_axis_plane_events && original != complex)
          throw std::runtime_error("R_UNION_R_DIFFERS");
        p.event_calculate_xs();
        p.event_advance();
        const auto& ctx = p.axis_plane_context();
        if (!first) std::cout << ',';
        first = false;
        const int s = p.boundary().surface();
        std::cout << "{\"before\":" << before << ",\"length\":" << p.boundary().distance()
          << ",\"region_length\":" << original.first << ",\"surface\":"
          << (s > 0 ? 1 : -1) * model::surfaces[std::abs(s)-1]->id_
          << ",\"context\":" << (ctx.valid ? "true" : "false")
          << ",\"coordinate\":" << p.r()[ctx.valid ? ctx.axis : 0]
          << ",\"contacts\":[";
        for (size_t i = 0; i < ctx.contacts.size(); ++i) {
          if (i) std::cout << ',';
          std::cout << model::surfaces[ctx.contacts[i]]->id_;
        }
        std::cout << ']';
        p.event_cross_surface();
        std::cout << ",\"after\":" << (p.wgt() > 0. ? model::cells[p.coord(0).cell()]->id_ : -1)
          << ",\"weight\":" << p.wgt();
        bins();
        std::cout << '}';
      }
    } catch (const std::exception& e) { error = e.what(); }
    std::cout << "],\"error\":" << std::quoted(error);
    bins();
    std::cout << "}\n";
    if (mode == 3) model::cells[p.coord(0).cell()]->material_[0] = MATERIAL_VOID;
    if (!error.empty() && !first) return 5; // partial event output is terminal failure
  }
  return openmc_finalize();
}
