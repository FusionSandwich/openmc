#include "openmc/tallies/filter_particle_production.h"

#include <fmt/core.h>

#include "openmc/nuclide.h"
#include "openmc/search.h"
#include "openmc/xml_interface.h"

namespace openmc {

//==============================================================================
// ParticleProductionFilter implementation
//==============================================================================

void ParticleProductionFilter::get_all_bins(
  const Particle& p, TallyEstimator estimator, FilterMatch& match) const
{
  int start_idx = p.secondary_bank_index();
  int end_idx = start_idx + p.n_secondaries();

  // Loop over secondary bank entries
  for (int bank_idx = start_idx; bank_idx < end_idx; bank_idx++) {
    const auto& site = p.secondary_bank(bank_idx);

    // Find which particle-type slot this secondary belongs to
    auto it = type_to_index_.find(site.particle.pdg_number());
    if (it == type_to_index_.end())
      continue;

    // Compute the weight for this secondary
    double weight = site.wgt;
    if (damage_model_ == DamageModel::RECOIL_ENERGY) {
      // Full recoil kinetic energy with no electronic loss correction
      weight = site.wgt * site.E;
    } else if (damage_model_ == DamageModel::NRT) {
      // Extract recoil Z, A using ParticleType methods
      int Z_R = site.particle.atomic_number();
      int A_R = site.particle.mass_number();

      // Get lattice Z, A from the collision target nuclide
      int Z_L = Z_R;
      int A_L = A_R;
      if (p.event_nuclide() >= 0) {
        const auto& nuc = *data::nuclides[p.event_nuclide()];
        Z_L = nuc.Z_;
        A_L = nuc.A_;
      }

      weight = site.wgt * lindhard_partition(site.E, Z_R, A_R, Z_L, A_L);
    }

    int particle_idx = it->second;
    if (energy_bins_.empty()) {
      // No energy binning, just particle type
      match.bins_.push_back(particle_idx);
      match.weights_.push_back(weight);
    } else {
      // Bin the energy
      if (site.E >= energy_bins_.front() && site.E <= energy_bins_.back()) {
        int n_energies = static_cast<int>(energy_bins_.size()) - 1;
        auto energy_idx =
          lower_bound_index(energy_bins_.begin(), energy_bins_.end(), site.E);
        match.bins_.push_back(particle_idx * n_energies + energy_idx);
        match.weights_.push_back(weight);
      }
    }
  }
}

std::string ParticleProductionFilter::text_label(int bin) const
{
  if (energy_bins_.empty()) {
    return fmt::format("Secondary {}", secondary_types_.at(bin).str());
  } else {
    int n_energies = static_cast<int>(energy_bins_.size()) - 1;
    int particle_idx = bin / n_energies;
    int energy_idx = bin % n_energies;
    return fmt::format("Secondary {}, Energy [{}, {})",
      secondary_types_.at(particle_idx).str(), energy_bins_.at(energy_idx),
      energy_bins_.at(energy_idx + 1));
  }
}

void ParticleProductionFilter::from_xml(pugi::xml_node node)
{
  // Read energy bins if present (optional)
  if (check_for_node(node, "energies")) {
    auto bins = get_node_array<double>(node, "energies");
    for (int64_t i = 1; i < bins.size(); ++i) {
      if (bins[i] <= bins[i - 1]) {
        throw std::runtime_error {
          "Energy bins must be monotonically increasing."};
      }
    }
    energy_bins_.assign(bins.begin(), bins.end());
  }

  // Read particle types (required)
  auto names = get_node_array<std::string>(node, "particles");
  for (const auto& name : names) {
    int idx = secondary_types_.size();
    secondary_types_.emplace_back(name);
    type_to_index_[secondary_types_.back().pdg_number()] = idx;
  }

  // Read damage model if present (optional)
  if (check_for_node(node, "damage_model")) {
    std::string model_str = get_node_value(node, "damage_model");
    if (model_str == "nrt") {
      damage_model_ = DamageModel::NRT;
    } else if (model_str == "recoil-energy") {
      damage_model_ = DamageModel::RECOIL_ENERGY;
    } else {
      throw std::runtime_error {
        "Unrecognized damage model '" + model_str + "'"};
    }
  }

  if (damage_model_ != DamageModel::NONE) {
    for (const auto& type : secondary_types_) {
      if (!type.is_nucleus()) {
        throw std::runtime_error {
          "Particle production damage models can only be applied to "
          "recoiling nuclei."};
      }
    }
  }

  // Compute total bins
  if (energy_bins_.empty()) {
    n_bins_ = secondary_types_.size();
  } else {
    n_bins_ = secondary_types_.size() * (energy_bins_.size() - 1);
  }
}

void ParticleProductionFilter::to_statepoint(hid_t filter_group) const
{
  Filter::to_statepoint(filter_group);

  // Write energy bins if present
  if (!energy_bins_.empty()) {
    write_dataset(filter_group, "energies", energy_bins_);
  }

  // Write particle types
  vector<std::string> names;
  for (const auto& pt : secondary_types_) {
    names.push_back(pt.str());
  }
  write_dataset(filter_group, "particles", names);

  // Write damage model if set
  if (damage_model_ != DamageModel::NONE) {
    std::string model_str;
    if (damage_model_ == DamageModel::NRT)
      model_str = "nrt";
    else if (damage_model_ == DamageModel::RECOIL_ENERGY)
      model_str = "recoil-energy";
    write_dataset(filter_group, "damage_model", model_str);
  }
}

} // namespace openmc
