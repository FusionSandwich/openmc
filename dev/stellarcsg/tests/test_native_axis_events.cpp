// Native deterministic events; external Fraction oracle checks every row/bin.
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#ifdef __unix__
#include <dlfcn.h>
#endif
#include "openmc/capi.h"
#include "openmc/cell.h"
#include "openmc/geometry.h"
#include "openmc/particle.h"
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/tallies/tally.h"
#include "pugixml.hpp"

using namespace openmc;

struct FixtureState {
  vector<double> offsets;
  vector<vector<int32_t>> materials;

  static double offset(const Surface& s)
  {
    if (const auto* x = dynamic_cast<const SurfaceXPlane*>(&s)) return x->x0_;
    if (const auto* y = dynamic_cast<const SurfaceYPlane*>(&s)) return y->y0_;
    if (const auto* z = dynamic_cast<const SurfaceZPlane*>(&s)) return z->z0_;
    return 0.;
  }

  FixtureState()
  {
    for (const auto& s : model::surfaces) offsets.push_back(offset(*s));
    for (const auto& c : model::cells) materials.push_back(c->material_);
  }

  void restore() const
  {
    for (size_t i = 0; i < offsets.size(); ++i) {
      auto& s = *model::surfaces[i];
      if (auto* x = dynamic_cast<SurfaceXPlane*>(&s)) x->x0_ = offsets[i];
      if (auto* y = dynamic_cast<SurfaceYPlane*>(&s)) y->y0_ = offsets[i];
      if (auto* z = dynamic_cast<SurfaceZPlane*>(&s)) z->z0_ = offsets[i];
    }
    for (size_t i = 0; i < materials.size(); ++i)
      model::cells[i]->material_ = materials[i];
  }

  bool matches() const
  {
    for (size_t i = 0; i < offsets.size(); ++i)
      if (offset(*model::surfaces[i]) != offsets[i]) return false;
    for (size_t i = 0; i < materials.size(); ++i)
      if (model::cells[i]->material_ != materials[i]) return false;
    return true;
  }

  ~FixtureState() { restore(); }
};

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
#ifdef __unix__
  Dl_info loaded {};
  if (!dladdr(reinterpret_cast<void*>(&openmc_init), &loaded)) return 7;
  std::cout << "META {\"library\":" << std::quoted(loaded.dli_fname)
    << ",\"geometry_state_bytes\":" << sizeof(GeometryState) << "}\n";
#endif
  for (int cycle = 0; cycle < 2; ++cycle) {
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
    {
      std::ifstream input(query_file);
      std::cout << std::setprecision(17);
      std::string line;
      Particle p; // Reuse the same object across sources, including failed queries.
      const FixtureState baseline;
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
        if (!baseline.matches()) return 8;
        const FixtureState query_state;
        bool source_reset = false;
        std::cout << "ROW {\"id\":" << id << ",\"cycle\":" << cycle << ",\"events\":[";
        bool first = true;
        std::string error;
        try {
#ifdef OPENMC_EXPERIMENTAL_AXIS_PLANES
          const auto previous_epoch = p.axis_plane_context().epoch;
#endif
          p.from_source(&source);
#ifdef OPENMC_EXPERIMENTAL_AXIS_PLANES
          const auto& reset = p.axis_plane_context();
          source_reset = !reset.valid && !reset.pending && !reset.advanced &&
            reset.contacts.empty() && reset.outgoing_sides.empty() &&
            reset.epoch == previous_epoch + 1;
          if (!source_reset) throw std::runtime_error("SOURCE_CONTEXT_NOT_RESET");
#else
          source_reset = true;
#endif
          p.id() = id;
          if (!exhaustive_find_cell(p)) throw std::runtime_error("NO_START_OWNER");
          if (mode == 3) model::cells[p.coord(0).cell()]->material_[0] = 0;
          if (mode == 4) {
#ifdef OPENMC_EXPERIMENTAL_AXIS_PLANES
            p.axis_plane_context().reset();
#endif
            p.r()[0] = -1.7976931348623157e308;
            // Keep a valid common enclosure and ordered slabs while making the
            // first interval 1.5*DBL_MAX. Restore every offset even on exception.
            const double maximum = 1.7976931348623157e308;
            for (auto& s : model::surfaces) {
              if (auto* x = dynamic_cast<SurfaceXPlane*>(s.get())) {
                switch (s->id_) {
                case 1: x->x0_ = -maximum; break;
                case 2: x->x0_ = maximum; break;
                case 10: x->x0_ = maximum/2; break;
                case 11: x->x0_ = maximum*.75; break;
                case 20: x->x0_ = maximum*.875; break;
                case 21: x->x0_ = maximum; break;
                case 30: x->x0_ = maximum*.25; break;
                }
              }
            }
            p.u() = {1., 0., 0.};
            Region extreme("-10", 0);
            (void) extreme.distance(p.r(), p.u(), SURFACE_NONE);
            throw std::runtime_error("OVERFLOW_GUARD_DID_NOT_REJECT");
          }
#ifdef OPENMC_EXPERIMENTAL_AXIS_PLANES
          if (mode == 1) p.u()[p.axis_plane_context().axis] *= -1.; // stale epoch
#endif
          if (mode == 2) p.event_collide(); // prohibited before any score
          for (int step = 0; step < steps && p.wgt() > 0.; ++step) {
            const int before = model::cells[p.coord(0).cell()]->id_;
            std::string expression;
            for (auto c : geometry.child("geometry").children("cell"))
              if (c.attribute("id").as_int() == before) expression = c.attribute("region").value();
            Region duplicate("(" + expression + ") | (" + expression + ")", before);
            const auto original = model::cells[p.coord(0).cell()]->distance(p.r(), p.u(), p.surface(), &p);
            const auto complex = duplicate.distance(p.r(), p.u(), p.surface());
#ifdef OPENMC_EXPERIMENTAL_AXIS_PLANES
            if (settings::experimental_axis_plane_events && original != complex)
              throw std::runtime_error("R_UNION_R_DIFFERS");
#endif
            p.event_calculate_xs();
            p.event_advance();
#ifdef OPENMC_EXPERIMENTAL_AXIS_PLANES
            const auto& ctx = p.axis_plane_context();
            const bool context_valid = ctx.valid;
            const auto contacts = ctx.contacts;
            const int active_axis = ctx.valid ? ctx.axis :
              (p.u().x != 0. ? 0 : (p.u().y != 0. ? 1 : 2));
#else
            const bool context_valid = false;
            const vector<int> contacts;
            const int active_axis = p.u().x != 0. ? 0 : (p.u().y != 0. ? 1 : 2);
#endif
            if (!first) std::cout << ',';
            first = false;
            const int s = p.boundary().surface();
            std::cout << "{\"before\":" << before << ",\"length\":" << p.boundary().distance()
              << ",\"region_length\":" << original.first << ",\"surface\":"
              << (s > 0 ? 1 : -1) * model::surfaces[std::abs(s)-1]->id_
              << ",\"context\":" << (context_valid ? "true" : "false")
              << ",\"coordinate\":" << p.r()[active_axis]
              << ",\"contacts\":[";
            for (size_t i = 0; i < contacts.size(); ++i) {
              if (i) std::cout << ',';
              std::cout << model::surfaces[contacts[i]]->id_;
            }
            std::cout << ']';
            p.event_cross_surface();
            std::cout << ",\"after\":" << (p.wgt() > 0. ? model::cells[p.coord(0).cell()]->id_ : -1)
              << ",\"weight\":" << p.wgt();
            bins();
            std::cout << '}';
          }
        } catch (const std::exception& e) { error = e.what(); }
        query_state.restore();
        const bool restored = query_state.matches() && baseline.matches();
        std::cout << "],\"error\":" << std::quoted(error);
        std::cout << ",\"fixture_restored\":" << (restored ? "true" : "false")
          << ",\"source_reset\":" << (source_reset ? "true" : "false")
          << ",\"source_position_unchanged\":" <<
            (p.r().x == source.r.x && p.r().y == source.r.y && p.r().z == source.r.z ? "true" : "false");
        bins();
        std::cout << "}\n";
        if (!restored) return 9;
        if (!error.empty() && !first) return 5; // partial event output is terminal failure
      }
    } // Restore/checkpoint objects die while the model is still initialized.
    code = openmc_finalize();
    if (code) return code;
#ifdef OPENMC_EXPERIMENTAL_AXIS_PLANES
    if (settings::experimental_axis_plane_events) return 10;
#endif
  }
  return 0;
}
