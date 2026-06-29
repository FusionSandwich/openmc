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
#include "openmc/endf.h"
#include "openmc/file_utils.h"
#include "openmc/hdf5_interface.h"
#include "openmc/material.h"
#include "openmc/message_passing.h"
#include "openmc/nuclide.h"
#include "openmc/output.h"
#include "openmc/particle.h"
#include "openmc/particle_type.h"
#include "openmc/reaction.h"
#include "openmc/settings.h"
#include "openmc/simulation.h"
#include "openmc/universe.h"

#ifdef OPENMC_MPI
#include <mpi.h>
#endif

namespace openmc {

namespace {

constexpr int REACTION_EVENT_PROVENANCE_ELASTIC_EXACT {1};
constexpr int REACTION_EVENT_PROVENANCE_PRODUCT_DISTRIBUTION_SAMPLED {2};
constexpr int REACTION_EVENT_PROVENANCE_RESIDUAL_MOMENTUM_BALANCE {3};
constexpr int REACTION_EVENT_PROVENANCE_CAPTURE_GAMMA_APPROX {4};
constexpr int REACTION_EVENT_PROVENANCE_ENERGY_BALANCE_ONLY {5};
constexpr int REACTION_EVENT_PROVENANCE_UNSUPPORTED {6};

constexpr int REACTION_PRODUCT_SOURCE_SAMPLED_PRODUCT {1};

int64_t reaction_event_id(const Particle& p)
{
  return p.id() * 1000000 + p.n_collision();
}

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
  H5Tinsert(eventtype, "n_products", HOFFSET(ReactionEventSite, n_products),
    H5T_NATIVE_INT);
  H5Tinsert(eventtype, "first_product_index",
    HOFFSET(ReactionEventSite, first_product_index), H5T_NATIVE_INT64);
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

hid_t h5_reaction_event_product_type()
{
  hid_t postype = H5Tcreate(H5T_COMPOUND, sizeof(Position));
  H5Tinsert(postype, "x", HOFFSET(Position, x), H5T_NATIVE_DOUBLE);
  H5Tinsert(postype, "y", HOFFSET(Position, y), H5T_NATIVE_DOUBLE);
  H5Tinsert(postype, "z", HOFFSET(Position, z), H5T_NATIVE_DOUBLE);

  hid_t producttype =
    H5Tcreate(H5T_COMPOUND, sizeof(ReactionEventProductSite));
  H5Tinsert(producttype, "event_id",
    HOFFSET(ReactionEventProductSite, event_id), H5T_NATIVE_INT64);
  H5Tinsert(producttype, "product_index",
    HOFFSET(ReactionEventProductSite, product_index), H5T_NATIVE_INT);
  H5Tinsert(producttype, "product_particle",
    HOFFSET(ReactionEventProductSite, product_particle), H5T_NATIVE_INT);
  H5Tinsert(producttype, "product_za_or_pdg",
    HOFFSET(ReactionEventProductSite, product_za_or_pdg), H5T_NATIVE_INT);
  H5Tinsert(producttype, "product_energy",
    HOFFSET(ReactionEventProductSite, product_energy), H5T_NATIVE_DOUBLE);
  H5Tinsert(producttype, "product_direction",
    HOFFSET(ReactionEventProductSite, product_direction), postype);
  H5Tinsert(producttype, "product_weight",
    HOFFSET(ReactionEventProductSite, product_weight), H5T_NATIVE_DOUBLE);
  H5Tinsert(producttype, "product_source",
    HOFFSET(ReactionEventProductSite, product_source), H5T_NATIVE_INT);
  H5Tinsert(producttype, "product_provenance",
    HOFFSET(ReactionEventProductSite, product_provenance), H5T_NATIVE_INT);

  H5Tclose(postype);
  return producttype;
}

bool matches_reaction_event_filters(
  int cell_id, int material_id, const std::string& nuclide, int mt)
{
  auto matches_filter = [](const auto& filter_set, const auto& value) {
    return filter_set.empty() || filter_set.count(value) > 0;
  };
  auto matches_mt_filter = [](const auto& filter_set, int value) {
    if (filter_set.empty())
      return true;
    for (int mt : filter_set) {
      if (mt_matches(value, mt))
        return true;
    }
    return false;
  };

  const auto& cfg = settings::reaction_event_output;
  return simulation::current_batch > settings::n_inactive &&
         !simulation::reaction_event_bank.full() &&
         matches_filter(cfg.cell_ids, cell_id) &&
         matches_filter(cfg.material_ids, material_id) &&
         matches_filter(cfg.nuclides, nuclide) &&
         matches_mt_filter(cfg.mt_numbers, mt);
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

void write_reaction_event_product_bank(hid_t group_id,
  openmc::span<ReactionEventProductSite> product_bank,
  const openmc::vector<int64_t>& bank_index)
{
  hid_t producttype = h5_reaction_event_product_type();
#ifdef OPENMC_MPI
  write_bank_dataset("products", group_id, product_bank, bank_index,
    producttype, producttype, mpi::reaction_event_product_site);
#else
  write_bank_dataset(
    "products", group_id, product_bank, bank_index, producttype, producttype);
#endif

  H5Tclose(producttype);
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
  write_attribute(
    metadata_group, "provenance_2", "product_distribution_sampled");
  write_attribute(
    metadata_group, "provenance_3", "residual_momentum_balance");
  write_attribute(metadata_group, "provenance_4", "capture_gamma_approx");
  write_attribute(metadata_group, "provenance_5", "energy_balance_only");
  write_attribute(metadata_group, "provenance_6", "unsupported");
  write_attribute(metadata_group, "product_source_1", "sampled_product");
  close_group(metadata_group);
}

void write_h5_reaction_events(const std::string& filename,
  openmc::span<ReactionEventSite> event_bank,
  const openmc::vector<int64_t>& event_bank_index,
  openmc::span<ReactionEventProductSite> product_bank,
  const openmc::vector<int64_t>& product_bank_index)
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

  write_reaction_event_bank(event_group, event_bank, event_bank_index);
  if (settings::reaction_event_output.write_products) {
    write_reaction_event_product_bank(
      event_group, product_bank, product_bank_index);
  }

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
  if (settings::reaction_event_output.write_products) {
    simulation::reaction_event_product_bank.reserve(
      settings::reaction_event_output.max_events);
  }
}

void reaction_event_flush_bank()
{
  if (!settings::reaction_event_output.enabled)
    return;

  auto size = simulation::reaction_event_bank.size();
  auto product_size = simulation::reaction_event_product_bank.size();
  auto reaction_event_work_index = mpi::calculate_parallel_index_vector(size);
  auto reaction_product_work_index =
    mpi::calculate_parallel_index_vector(product_size);
  openmc::span<ReactionEventSite> eventspan(
    simulation::reaction_event_bank.begin(), size);
  openmc::span<ReactionEventProductSite> productspan(
    simulation::reaction_event_product_bank.begin(), product_size);

  std::string filename =
    settings::path_output + settings::reaction_event_output.filename;
  write_message("Creating {}...", filename, 4);
  write_h5_reaction_events(filename, eventspan, reaction_event_work_index,
    productspan, reaction_product_work_index);

  simulation::reaction_event_bank.clear();
  simulation::reaction_event_product_bank.clear();
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
  site.event_id = reaction_event_id(p);

  simulation::reaction_event_bank.thread_safe_append(site);
}

void reaction_event_record_neutron_product(Particle& p, const Nuclide& nuc,
  const Reaction& rx, double E_in, Direction u_in, int n_products,
  double E_recoil, Direction u_recoil, bool has_residual)
{
  const auto& cfg = settings::reaction_event_output;
  if (!cfg.enabled || !cfg.write_products ||
      simulation::reaction_event_product_bank.full() || n_products <= 0)
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
  if (!matches_reaction_event_filters(cell_id, material_id, nuclide, rx.mt_))
    return;

  int64_t event_id = reaction_event_id(p);

  ReactionEventSite site;
  site.event_id = event_id;
  site.history_id = p.id();
  site.particle_id = p.id();
  site.parent_id = p.id();
  site.cell_id = cell_id;
  site.cell_instance = p.cell_instance();
  site.material_id = material_id;
  site.universe_id = model::universes[universe_index]->id_;
  site.target_za = 1000 * nuc.Z_ + nuc.A_;
  site.reaction_mt = rx.mt_;
  site.incident_particle = PDG_NEUTRON;
  site.incident_energy = E_in;
  site.incident_direction = u_in;
  site.outgoing_neutron_energy = p.E();
  site.outgoing_neutron_direction = p.u();
  site.recoil_za = site.target_za;
  if (has_residual) {
    site.recoil_energy = E_recoil;
    site.recoil_direction = u_recoil;
  }
  site.event_weight = p.wgt();
  site.time = p.time();
  site.provenance = has_residual
                      ? REACTION_EVENT_PROVENANCE_RESIDUAL_MOMENTUM_BALANCE
                      : REACTION_EVENT_PROVENANCE_PRODUCT_DISTRIBUTION_SAMPLED;

  int64_t idx = simulation::reaction_event_bank.thread_safe_append(site);
  if (idx < 0)
    return;

  int64_t first_product_index {-1};
  int actual_products {0};
#pragma omp critical(reaction_event_product_append)
  {
    for (int i = 0; i < n_products; ++i) {
      if (simulation::reaction_event_product_bank.full())
        break;

      ReactionEventProductSite product;
      product.event_id = event_id;
      product.product_index = i;
      product.product_particle = PDG_NEUTRON;
      product.product_za_or_pdg = PDG_NEUTRON;
      product.product_energy = p.E();
      product.product_direction = p.u();
      product.product_weight = p.wgt();
      product.product_source = REACTION_PRODUCT_SOURCE_SAMPLED_PRODUCT;
      product.product_provenance =
        REACTION_EVENT_PROVENANCE_PRODUCT_DISTRIBUTION_SAMPLED;

      int64_t product_bank_index =
        simulation::reaction_event_product_bank.thread_safe_append(product);
      if (product_bank_index < 0)
        break;
      if (first_product_index < 0)
        first_product_index = product_bank_index;
      ++actual_products;
    }
  }

  simulation::reaction_event_bank[idx].n_products = actual_products;
  simulation::reaction_event_bank[idx].first_product_index = first_product_index;
}

void reaction_event_record_capture(Particle& p, const Nuclide& nuc,
  int reaction_mt, double E_in, Direction u_in, double event_weight,
  double E_recoil, Direction u_recoil, bool has_recoil,
  bool has_energy_balance)
{
  const auto& cfg = settings::reaction_event_output;
  if (!cfg.enabled)
    return;

  int provenance;
  if (has_recoil) {
    if (!cfg.balance_diagnostics)
      return;
    provenance = REACTION_EVENT_PROVENANCE_CAPTURE_GAMMA_APPROX;
  } else if (has_energy_balance) {
    if (!cfg.balance_diagnostics)
      return;
    provenance = REACTION_EVENT_PROVENANCE_ENERGY_BALANCE_ONLY;
  } else {
    if (!cfg.write_unsupported)
      return;
    provenance = REACTION_EVENT_PROVENANCE_UNSUPPORTED;
  }

  int cell_index = p.lowest_coord().cell();
  int material_index = p.material();
  int universe_index = p.lowest_coord().universe();
  if (cell_index == C_NONE || material_index == C_NONE ||
      universe_index == C_NONE)
    return;

  int cell_id = model::cells[cell_index]->id_;
  int material_id = model::materials[material_index]->id_;
  std::string nuclide = nuc.name_;
  if (!matches_reaction_event_filters(cell_id, material_id, nuclide, reaction_mt))
    return;

  ReactionEventSite site;
  site.event_id = reaction_event_id(p);
  site.history_id = p.id();
  site.particle_id = p.id();
  site.parent_id = p.id();
  site.cell_id = cell_id;
  site.cell_instance = p.cell_instance();
  site.material_id = material_id;
  site.universe_id = model::universes[universe_index]->id_;
  site.target_za = 1000 * nuc.Z_ + nuc.A_;
  site.reaction_mt = reaction_mt;
  site.incident_particle = PDG_NEUTRON;
  site.incident_energy = E_in;
  site.incident_direction = u_in;
  site.recoil_za = site.target_za;
  if (has_recoil) {
    site.recoil_energy = E_recoil;
    site.recoil_direction = u_recoil;
  }
  site.event_weight = event_weight;
  site.time = p.time();
  site.provenance = provenance;

  simulation::reaction_event_bank.thread_safe_append(site);
}

} // namespace openmc
