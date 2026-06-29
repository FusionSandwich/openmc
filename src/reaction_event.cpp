#include "openmc/reaction_event.h"

#include <algorithm>
#include <string>
#include <unordered_set>

#include <fmt/format.h>

#include "openmc/bank.h"
#include "openmc/bank_io.h"
#include "openmc/cell.h"
#include "openmc/constants.h"
#include "openmc/error.h"
#include "openmc/file_utils.h"
#include "openmc/hdf5_interface.h"
#include "openmc/material.h"
#include "openmc/message_passing.h"
#include "openmc/nuclide.h"
#include "openmc/output.h"
#include "openmc/particle.h"
#include "openmc/particle_type.h"
#include "openmc/settings.h"
#include "openmc/simulation.h"
#include "openmc/universe.h"

#ifdef OPENMC_MPI
#include <mpi.h>
#endif

namespace openmc {

namespace {

constexpr int REACTION_EVENT_PROVENANCE_ELASTIC_EXACT {1};

template<typename T>
vector<T> sorted_filter_values(const std::unordered_set<T>& values)
{
  vector<T> result {values.begin(), values.end()};
  std::sort(result.begin(), result.end());
  return result;
}

std::string joined_string_filter(const std::unordered_set<std::string>& values)
{
  auto sorted = sorted_filter_values(values);
  std::string result;
  for (const auto& value : sorted) {
    if (!result.empty())
      result += ",";
    result += value;
  }
  return result;
}

hid_t h5_reaction_event_type()
{
  hid_t postype = H5Tcreate(H5T_COMPOUND, sizeof(Position));
  H5Tinsert(postype, "x", HOFFSET(Position, x), H5T_NATIVE_DOUBLE);
  H5Tinsert(postype, "y", HOFFSET(Position, y), H5T_NATIVE_DOUBLE);
  H5Tinsert(postype, "z", HOFFSET(Position, z), H5T_NATIVE_DOUBLE);

  hid_t eventtype = H5Tcreate(H5T_COMPOUND, sizeof(ReactionEventSite));
  H5Tinsert(eventtype, "event_id", HOFFSET(ReactionEventSite, event_id),
    H5T_NATIVE_INT64);
  H5Tinsert(eventtype, "history_id", HOFFSET(ReactionEventSite, history_id),
    H5T_NATIVE_INT64);
  H5Tinsert(eventtype, "particle_id", HOFFSET(ReactionEventSite, particle_id),
    H5T_NATIVE_INT64);
  H5Tinsert(eventtype, "parent_id", HOFFSET(ReactionEventSite, parent_id),
    H5T_NATIVE_INT64);
  H5Tinsert(eventtype, "cell_id", HOFFSET(ReactionEventSite, cell_id),
    H5T_NATIVE_INT);
  H5Tinsert(eventtype, "cell_instance",
    HOFFSET(ReactionEventSite, cell_instance), H5T_NATIVE_INT);
  H5Tinsert(eventtype, "material_id", HOFFSET(ReactionEventSite, material_id),
    H5T_NATIVE_INT);
  H5Tinsert(eventtype, "universe_id", HOFFSET(ReactionEventSite, universe_id),
    H5T_NATIVE_INT);
  H5Tinsert(eventtype, "target_za", HOFFSET(ReactionEventSite, target_za),
    H5T_NATIVE_INT);
  H5Tinsert(eventtype, "reaction_mt", HOFFSET(ReactionEventSite, reaction_mt),
    H5T_NATIVE_INT);
  H5Tinsert(eventtype, "incident_particle",
    HOFFSET(ReactionEventSite, incident_particle), H5T_NATIVE_INT);
  H5Tinsert(eventtype, "incident_energy",
    HOFFSET(ReactionEventSite, incident_energy), H5T_NATIVE_DOUBLE);
  H5Tinsert(eventtype, "incident_direction",
    HOFFSET(ReactionEventSite, incident_direction), postype);
  H5Tinsert(eventtype, "outgoing_neutron_energy",
    HOFFSET(ReactionEventSite, outgoing_neutron_energy), H5T_NATIVE_DOUBLE);
  H5Tinsert(eventtype, "outgoing_neutron_direction",
    HOFFSET(ReactionEventSite, outgoing_neutron_direction), postype);
  H5Tinsert(eventtype, "recoil_za", HOFFSET(ReactionEventSite, recoil_za),
    H5T_NATIVE_INT);
  H5Tinsert(eventtype, "recoil_energy",
    HOFFSET(ReactionEventSite, recoil_energy), H5T_NATIVE_DOUBLE);
  H5Tinsert(eventtype, "recoil_direction",
    HOFFSET(ReactionEventSite, recoil_direction), postype);
  H5Tinsert(eventtype, "event_weight",
    HOFFSET(ReactionEventSite, event_weight), H5T_NATIVE_DOUBLE);
  H5Tinsert(
    eventtype, "time", HOFFSET(ReactionEventSite, time), H5T_NATIVE_DOUBLE);
  H5Tinsert(eventtype, "provenance", HOFFSET(ReactionEventSite, provenance),
    H5T_NATIVE_INT);

  H5Tclose(postype);
  return eventtype;
}

bool matches_reaction_event_filters(
  int cell_id, int material_id, const std::string& nuclide, int mt)
{
  auto matches_filter = [](const auto& filter_set, const auto& value) {
    return filter_set.empty() || filter_set.count(value) > 0;
  };

  const auto& cfg = settings::reaction_event_output;
  return simulation::current_batch > settings::n_inactive &&
         !simulation::reaction_event_bank.full() &&
         matches_filter(cfg.cell_ids, cell_id) &&
         matches_filter(cfg.material_ids, material_id) &&
         matches_filter(cfg.nuclides, nuclide) &&
         matches_filter(cfg.mt_numbers, mt);
}

void write_reaction_event_bank(hid_t group_id,
  openmc::span<ReactionEventSite> event_bank,
  const openmc::vector<int64_t>& bank_index)
{
  hid_t eventtype = h5_reaction_event_type();
#ifdef OPENMC_MPI
  write_bank_dataset("events", group_id, event_bank, bank_index, eventtype,
    eventtype, mpi::reaction_event_site);
#else
  write_bank_dataset(
    "events", group_id, event_bank, bank_index, eventtype, eventtype);
#endif

  H5Tclose(eventtype);
}

void write_reaction_event_metadata(hid_t group_id)
{
  const auto& cfg = settings::reaction_event_output;
  auto material_filters = sorted_filter_values(cfg.material_ids);
  auto cell_filters = sorted_filter_values(cfg.cell_ids);
  auto reaction_filters = sorted_filter_values(cfg.mt_numbers);
  auto nuclide_filters = joined_string_filter(cfg.nuclides);

  hid_t metadata_group = create_group(group_id, "metadata");
  write_attribute(metadata_group, "schema_version", VERSION_REACTION_EVENTS);
  write_attribute(metadata_group, "max_events", cfg.max_events);
  write_attribute(metadata_group, "filename", cfg.filename);
  write_attribute(metadata_group, "write_products", cfg.write_products);
  write_attribute(metadata_group, "write_unsupported", cfg.write_unsupported);
  write_attribute(
    metadata_group, "balance_diagnostics", cfg.balance_diagnostics);
  write_attribute(metadata_group, "n_material_filters",
    static_cast<int>(material_filters.size()));
  write_attribute(
    metadata_group, "n_cell_filters", static_cast<int>(cell_filters.size()));
  write_attribute(metadata_group, "n_nuclide_filters",
    static_cast<int>(cfg.nuclides.size()));
  write_attribute(metadata_group, "n_reaction_filters",
    static_cast<int>(reaction_filters.size()));
  if (!material_filters.empty()) {
    write_attribute(metadata_group, "material_filters", material_filters);
  }
  if (!cell_filters.empty()) {
    write_attribute(metadata_group, "cell_filters", cell_filters);
  }
  if (!nuclide_filters.empty()) {
    write_attribute(metadata_group, "nuclide_filters", nuclide_filters);
  }
  if (!reaction_filters.empty()) {
    write_attribute(metadata_group, "reaction_filters", reaction_filters);
  }
  write_attribute(metadata_group, "tracking_method", "surface");
  write_attribute(metadata_group, "provenance_1", "elastic_exact");
  close_group(metadata_group);
}

void write_h5_reaction_events(const std::string& filename,
  openmc::span<ReactionEventSite> event_bank,
  const openmc::vector<int64_t>& bank_index)
{
#ifdef PHDF5
  bool parallel = true;
#else
  bool parallel = false;
#endif

  std::string filename_ = filename.empty() ? "reaction_events.h5" : filename;
  const auto extension = get_file_extension(filename_);
  if (extension.empty()) {
    filename_.append(".h5");
  } else if (extension != "h5") {
    warning("reaction_event_output filename has an extension other than .h5; "
            "an HDF5 file will still be written.");
  }

  hid_t file_id {-1};
  hid_t event_group {-1};
  if (mpi::master || parallel) {
    file_id = file_open(filename_.c_str(), 'w', true);
    write_attribute(file_id, "filetype", "reaction_events");
    write_attribute(file_id, "version", VERSION_REACTION_EVENTS);
    write_attribute(file_id, "openmc_version", VERSION);
#ifdef GIT_SHA1
    write_attribute(file_id, "git_sha1", GIT_SHA1);
#endif

    event_group = create_group(file_id, "reaction_events");
    write_attribute(event_group, "schema_version", VERSION_REACTION_EVENTS);
    write_attribute(event_group, "provenance_1", "elastic_exact");
    write_reaction_event_metadata(event_group);
  }

  write_reaction_event_bank(event_group, event_bank, bank_index);

  if (mpi::master || parallel) {
    close_group(event_group);
    file_close(file_id);
  }
}

} // namespace

void reaction_event_reserve_bank()
{
  simulation::reaction_event_bank.reserve(
    settings::reaction_event_output.max_events);
}

void reaction_event_flush_bank()
{
  if (!settings::reaction_event_output.enabled)
    return;

  auto size = simulation::reaction_event_bank.size();
  auto reaction_event_work_index = mpi::calculate_parallel_index_vector(size);
  openmc::span<ReactionEventSite> eventspan(
    simulation::reaction_event_bank.begin(), size);

  std::string filename =
    settings::path_output + settings::reaction_event_output.filename;
  write_message("Creating {}...", filename, 4);
  write_h5_reaction_events(filename, eventspan, reaction_event_work_index);

  simulation::reaction_event_bank.clear();
}

void reaction_event_record_elastic(Particle& p, const Nuclide& nuc,
  double E_in, Direction u_in, double E_recoil, Direction u_recoil)
{
  if (!settings::reaction_event_output.enabled)
    return;

  int cell_index = p.lowest_coord().cell();
  int material_index = p.material();
  int universe_index = p.lowest_coord().universe();
  if (cell_index == C_NONE || material_index == C_NONE ||
      universe_index == C_NONE)
    return;

  int cell_id = model::cells[cell_index]->id_;
  int material_id = model::materials[material_index]->id_;
  std::string nuclide = nuc.name_;
  if (!matches_reaction_event_filters(cell_id, material_id, nuclide, ELASTIC))
    return;

  ReactionEventSite site;
  site.history_id = p.id();
  site.particle_id = p.id();
  site.parent_id = p.id();
  site.cell_id = cell_id;
  site.cell_instance = p.cell_instance();
  site.material_id = material_id;
  site.universe_id = model::universes[universe_index]->id_;
  site.target_za = 1000 * nuc.Z_ + nuc.A_;
  site.reaction_mt = ELASTIC;
  site.incident_particle = PDG_NEUTRON;
  site.incident_energy = E_in;
  site.incident_direction = u_in;
  site.outgoing_neutron_energy = p.E();
  site.outgoing_neutron_direction = p.u();
  site.recoil_za = site.target_za;
  site.recoil_energy = E_recoil;
  site.recoil_direction = u_recoil;
  site.event_weight = p.wgt();
  site.time = p.time();
  site.provenance = REACTION_EVENT_PROVENANCE_ELASTIC_EXACT;

  int64_t idx = simulation::reaction_event_bank.thread_safe_append(site);
  if (idx >= 0) {
    simulation::reaction_event_bank[idx].event_id =
      p.id() * 1000000 + p.n_collision();
  }
}

} // namespace openmc
