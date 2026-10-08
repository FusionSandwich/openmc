#include "openmc/axis_plane_events.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

#include "openmc/boundary_condition.h"
#include "openmc/cell.h"
#include "openmc/geometry.h"
#include "openmc/particle.h"
#include "openmc/settings.h"
#include "openmc/surface.h"
#include "openmc/tallies/tally.h"
#include "openmc/universe.h"

#ifdef __FAST_MATH__
#error Exact axis-plane events require strict floating point
#endif

namespace openmc {
namespace {
using stellarcsg::AxisPlane;
using stellarcsg::DyadicDifference;
using stellarcsg::UnitAxisRay;

[[noreturn]] void unsupported(const char* reason)
{
  throw std::runtime_error(std::string("AXIS_PLANE_UNSUPPORTED: ") + reason);
}

AxisPlane plane(const Surface& s)
{
  if (const auto* p = dynamic_cast<const SurfaceXPlane*>(&s)) return {0, p->x0_};
  if (const auto* p = dynamic_cast<const SurfaceYPlane*>(&s)) return {1, p->y0_};
  if (const auto* p = dynamic_cast<const SurfaceZPlane*>(&s)) return {2, p->z0_};
  unsupported("non-built-in-axis-plane surface");
}

UnitAxisRay ray(Position r, Direction u)
{
  int axis = -1;
  for (int j = 0; j < 3; ++j) {
    if (!std::isfinite(r[j]) || !std::isfinite(u[j])) unsupported("nonfinite ray");
    if (u[j] == 0.0) continue;
    if (axis != -1 || (u[j] != 1.0 && u[j] != -1.0))
      unsupported("direction must be exactly unit axis");
    axis = j;
  }
  if (axis == -1) unsupported("zero direction");
  return UnitAxisRay({r.x, r.y, r.z}, axis, u[axis] > 0.0 ? 1 : -1);
}

void validate_vacuum_enclosure()
{
  // Admit only two distinct vacuum faces per axis. Conservative Boolean cell
  // boxes must fit inside, and collectively reach, this common outer box.
  // An internal or masked vacuum plane therefore fails before any scoring.
  array<vector<std::pair<double, int>>, 3> offsets;
  for (int i = 0; i < static_cast<int>(model::surfaces.size()); ++i) {
    const auto& s = model::surfaces[i];
    if (s->bc_) {
      const auto p = plane(*s);
      offsets[p.axis].push_back({p.offset, i + 1});
    }
  }
  BoundingBox enclosure;
  for (int j = 0; j < 3; ++j) {
    auto& values = offsets[j];
    if (values.size() != 2 || values[0].first == values[1].first)
      unsupported("vacuum requires six distinct common outer enclosure faces");
    std::sort(values.begin(), values.end());
    enclosure.min[j] = values[0].first;
    enclosure.max[j] = values[1].first;
  }
  auto extent = BoundingBox::inverted();
  for (const auto& c : model::cells) {
    const auto box = c->bounding_box();
    for (int j = 0; j < 3; ++j) {
      const auto& cell = static_cast<const CSGCell&>(*c);
      if (!cell.requires_axis_halfspace(offsets[j][0].second) ||
          !cell.requires_axis_halfspace(-offsets[j][1].second))
        unsupported("cell does not imply common vacuum enclosure halfspaces");
      if (box.min[j] < enclosure.min[j] || box.max[j] > enclosure.max[j] ||
          box.min[j] >= box.max[j])
        unsupported("cell not bounded by common vacuum enclosure");
    }
    extent |= box;
  }
  for (int j = 0; j < 3; ++j) {
    if (extent.min[j] != enclosure.min[j] || extent.max[j] != enclosure.max[j])
      unsupported("vacuum faces do not bound common cell extent");
  }
}

void validate_model()
{
  if (model::n_coord_levels != 1 || model::universes.size() != 1 ||
      model::root_universe != 0 || model::cells.empty())
    unsupported("requires one root universe and coordinate level");
  if (settings::run_mode != RunMode::FIXED_SOURCE ||
      settings::solver_type != SolverType::MONTE_CARLO || settings::cmfd_run ||
      settings::weight_windows_on ||
      settings::weight_window_checkpoint_surface || settings::survival_biasing ||
      settings::event_based || settings::check_overlaps || settings::collision_track ||
      settings::particle_restart_run || settings::restart_run)
    unsupported("requires deterministic fixed-source events without auxiliary transport");
  for (auto cutoff : settings::time_cutoff)
    if (cutoff < INFTY) unsupported("finite time cutoff");
  // Surface::surf_source_ is eligibility and defaults true for all surfaces
  // when no ID list is set. Banking itself is controlled by these settings.
  if (settings::surf_source_write || settings::surf_source_read)
    unsupported("surface source banking");
  for (const auto& s : model::surfaces) {
    if (!std::isfinite(plane(*s).offset)) unsupported("nonfinite plane");
    if (s->bc_ && (s->bc_->type() != "vacuum" || s->bc_->has_albedo()))
      unsupported("boundary condition other than transmission/vacuum");
  }
  for (const auto& c : model::cells) {
    if (!dynamic_cast<const CSGCell*>(c.get()) || c->universe_ != 0 ||
        c->type_ != Fill::MATERIAL || c->material(0) != MATERIAL_VOID ||
        c->n_instances() != 1 || !c->rotation_.empty() ||
        c->translation_.x != 0.0 || c->translation_.y != 0.0 || c->translation_.z != 0.0)
      unsupported("requires untransformed nondistributed void CSG cells");
  }
  validate_vacuum_enclosure();
  // Validate all configured tallies, even if an active-list accelerator omits one.
  for (const auto& t : model::tallies) {
    const bool flux = t->type_ == TallyType::VOLUME &&
      t->estimator_ == TallyEstimator::TRACKLENGTH &&
      t->scores_.size() == 1 && t->scores_[0] == SCORE_FLUX;
    const bool current = t->type_ == TallyType::SURFACE &&
      t->scores_.size() == 1 && t->scores_[0] == SCORE_CURRENT;
    if ((!flux && !current) || t->deriv_ != C_NONE ||
        t->nuclides_.size() != 1 || t->nuclides_[0] != -1)
      unsupported("tally score/estimator/derivative/nuclide");
    for (auto filter : t->filter_types()) {
      if ((flux && filter != FilterType::CELL) ||
          (current && filter != FilterType::SURFACE))
        unsupported("tally filter outside cell-flux/surface-current subset");
    }
    if (current && t->filters().size() != 1)
      unsupported("current requires exactly one surface filter");
  }
  if (!model::active_meshsurf_tallies.empty() ||
      !model::active_timed_tracklength_tallies.empty() ||
      !model::active_collision_tallies.empty() || !model::active_analog_tallies.empty() ||
      !model::active_pulse_height_tallies.empty()) unsupported("unsupported active tally list");
}

vector<int> sides(const UnitAxisRay& r, double coordinate, bool after)
{
  vector<int> result;
  result.reserve(model::surfaces.size());
  for (const auto& s : model::surfaces) {
    const int side = stellarcsg::axis_plane_limit_side(r, coordinate, plane(*s), after);
    if (side == 0) unsupported("parallel coplanar ray");
    result.push_back(side);
  }
  return result;
}

int owner(const vector<int>& values)
{
  int result = C_NONE;
  // Full search, independent of neighbors and spatial partition candidates.
  for (int index : model::universes[0]->cells_) {
    const auto& c = static_cast<const CSGCell&>(*model::cells[index]);
    if (!c.contains_axis_sides(values)) continue;
    if (result != C_NONE) unsupported("multiple strict owners; explicit Boolean priority required");
    result = index;
  }
  return result;
}

struct Contact {
  double coordinate;
  int index;
  DyadicDifference parameter;
};

vector<Contact> future_contacts(const UnitAxisRay& r, double current)
{
  vector<Contact> result;
  const UnitAxisRay from({r.axis() == 0 ? current : r.anchor()[0],
    r.axis() == 1 ? current : r.anchor()[1],
    r.axis() == 2 ? current : r.anchor()[2]}, r.axis(), r.direction());
  for (int i = 0; i < static_cast<int>(model::surfaces.size()); ++i) {
    const auto p = plane(*model::surfaces[i]);
    const auto c = stellarcsg::axis_plane_contact(from, p);
    if (c.status == stellarcsg::AxisContactStatus::coplanar)
      unsupported("parallel coplanar ray");
    // Every exact origin is consumed by the outgoing state at current. Positive
    // future contacts cannot be dropped merely for being close to that origin.
    if (c.status != stellarcsg::AxisContactStatus::future) continue;
    result.push_back({p.offset, i, stellarcsg::axis_plane_contact(r, p).parameter});
  }
  std::sort(result.begin(), result.end(), [](const Contact& a, const Contact& b) {
    const int order = a.parameter.compare(b.parameter);
    return order != 0 ? order < 0 :
      model::surfaces[a.index]->id_ < model::surfaces[b.index]->id_;
  });
  return result;
}

double interval(const UnitAxisRay& r, double begin, double end)
{
  const auto exact = stellarcsg::axis_interval_length(r, begin, end);
  const auto rounded = exact.rounded();
  if (exact.sign() <= 0 || rounded.status != stellarcsg::DyadicRoundingStatus::finite ||
      !std::isfinite(rounded.value) || rounded.value <= 0.0 || rounded.value == INFTY)
    unsupported("unrepresentable positive interval");
  return rounded.value;
}

void assign_owner(GeometryState& p, int index)
{
  auto& c = *model::cells[index];
  p.n_coord() = 1;
  p.coord(0).universe() = 0;
  p.coord(0).cell() = index;
  p.cell_instance() = 0;
  p.material_last() = p.material();
  p.material() = MATERIAL_VOID;
  p.sqrtkT_last() = p.sqrtkT();
  p.sqrtkT() = c.sqrtkT(0);
  p.density_mult_last() = p.density_mult();
  p.density_mult() = c.density_mult(0);
}

UnitAxisRay context_ray(GeometryState& p)
{
  auto& ctx = p.axis_plane_context();
  if (!ctx.valid) unsupported("missing ray context");
  const auto live = ray(p.r(), p.u());
  if (live.axis() != ctx.axis || live.direction() != ctx.direction || p.n_coord() != 1 ||
      p.coord(0).universe() != 0) unsupported("ray/frame changed within epoch");
  for (int j = 0; j < 3; ++j) {
    const double expected = j == ctx.axis ?
      (ctx.advanced ? ctx.event_coordinate : ctx.coordinate) : ctx.anchor[j];
    if (p.r()[j] != expected) unsupported("position changed outside certified advance");
  }
  return UnitAxisRay(ctx.anchor, ctx.axis, ctx.direction);
}
} // namespace

bool axis_plane_find_cell(GeometryState& p)
{
  validate_model();
  auto& ctx = p.axis_plane_context();
  if (!ctx.valid) {
    const auto r = ray(p.r(), p.u());
    ctx.anchor = r.anchor();
    ctx.axis = r.axis();
    ctx.direction = r.direction();
    ctx.coordinate = r.anchor()[r.axis()];
    ctx.valid = true;
    if (p.surface() != SURFACE_NONE) {
      const int index = std::abs(p.surface()) - 1;
      if (index < 0 || index >= static_cast<int>(model::surfaces.size()) ||
          stellarcsg::axis_plane_contact(r, plane(*model::surfaces[index])).status !=
            stellarcsg::AxisContactStatus::origin)
        unsupported("source surface hint is not an exact origin contact");
    }
    ctx.owner = owner(sides(r, ctx.coordinate, true));
  } else {
    const auto r = context_ray(p);
    if (ctx.pending) unsupported("lookup before pending event commit");
    if (owner(sides(r, ctx.coordinate, true)) != ctx.owner)
      unsupported("strict owner changed outside event commit");
  }
  if (ctx.owner == C_NONE) return false;
  assign_owner(p, ctx.owner);
  return true;
}

BoundaryInfo axis_plane_boundary(GeometryState& p)
{
  validate_model();
  if (!p.axis_plane_context().valid && !axis_plane_find_cell(p))
    unsupported("source has no strict outgoing owner");
  const auto r = context_ray(p);
  auto& ctx = p.axis_plane_context();
  if (ctx.advanced || ctx.pending) unsupported("uncommitted event query");
  if (p.coord(0).cell() != ctx.owner || owner(sides(r, ctx.coordinate, true)) != ctx.owner)
    unsupported("current owner disagrees with strict state");
  const auto candidates = future_contacts(r, ctx.coordinate);
  for (size_t begin = 0; begin < candidates.size();) {
    size_t end = begin + 1;
    while (end < candidates.size() &&
           candidates[begin].parameter.compare(candidates[end].parameter) == 0) ++end;
    const double coordinate = candidates[begin].coordinate;
    auto outgoing = sides(r, coordinate, true);
    const int next = owner(outgoing);
    int vacuum = C_NONE;
    for (size_t i = begin; i < end; ++i) {
      const int index = candidates[i].index;
      if (model::surfaces[index]->bc_) vacuum = index;
    }
    if (next != ctx.owner || vacuum != C_NONE) {
      if (owner(sides(r, coordinate, false)) != ctx.owner)
        unsupported("incoming owner disagrees at contact group");
      if (vacuum != C_NONE && next != C_NONE)
        unsupported("vacuum contact with outgoing owner");
      if (next == C_NONE && vacuum == C_NONE)
        unsupported("uncovered successor without vacuum");
      ctx.length = interval(r, ctx.coordinate, coordinate);
      ctx.event_coordinate = coordinate;
      ctx.parameter = candidates[begin].parameter;
      ctx.contacts.clear();
      for (size_t i = begin; i < end; ++i) ctx.contacts.push_back(candidates[i].index);
      ctx.outgoing_sides.assign(outgoing.begin(), outgoing.end());
      ctx.successor = next;
      ctx.vacuum_surface = vacuum;
      ctx.representative = ctx.direction * (ctx.contacts.front() + 1);
      ctx.pending = true;
      BoundaryInfo result;
      result.distance() = ctx.length;
      result.surface() = ctx.representative;
      result.coord_level() = 1;
      return result;
    }
    begin = end; // masked virtual group; no rounded movement and no score
  }
  unsupported("no finite next owner boundary or vacuum");
}

std::pair<double, int32_t> axis_plane_region_distance(
  const Region& region, Position position, Direction direction)
{
  validate_model();
  const auto r = ray(position, direction);
  const double current = position[r.axis()];
  const bool initial = region.contains_axis_sides(sides(r, current, true));
  const auto candidates = future_contacts(r, current);
  for (size_t begin = 0; begin < candidates.size();) {
    size_t end = begin + 1;
    while (end < candidates.size() &&
           candidates[begin].parameter.compare(candidates[end].parameter) == 0) ++end;
    if (region.contains_axis_sides(sides(r, candidates[begin].coordinate, true)) != initial)
      return {interval(r, current, candidates[begin].coordinate),
        r.direction() * (candidates[begin].index + 1)};
    begin = end;
  }
  return {INFTY, SURFACE_NONE};
}

void axis_plane_validate_particle(Particle& p)
{
  validate_model();
  if (!p.type().is_neutron() || !std::isfinite(p.E()) || p.E() <= 0.0 ||
      !std::isfinite(p.wgt()) || p.wgt() <= 0.0)
    unsupported("requires live positive-energy neutron");
  if (p.axis_plane_context().valid) (void) context_ray(p);
  else (void) ray(p.r(), p.u());
}

void axis_plane_advance_endpoint(Particle& p, double distance)
{
  auto& ctx = p.axis_plane_context();
  if (!ctx.valid || !ctx.pending || ctx.advanced || distance != ctx.length ||
      p.boundary().surface() != ctx.representative)
    unsupported("advance does not match pending exact event");
  // Caller has done ordinary movement. Replace its rounded active coordinate
  // with the certified represented plane coordinate before native scoring.
  p.r()[ctx.axis] = ctx.event_coordinate;
  ctx.advanced = true;
}

void axis_plane_commit(Particle& p)
{
  const auto r = context_ray(p);
  auto& ctx = p.axis_plane_context();
  if (!ctx.pending || !ctx.advanced || p.surface() != ctx.representative ||
      p.coord(0).cell() != ctx.owner ||
      owner(sides(r, ctx.event_coordinate, true)) != ctx.successor)
    unsupported("stale or inconsistent pending event commit");
  if (ctx.vacuum_surface != C_NONE)
    p.cross_vacuum_bc(*model::surfaces[ctx.vacuum_surface]);
  else
    assign_owner(p, ctx.successor);
  ctx.coordinate = ctx.event_coordinate;
  ctx.owner = ctx.successor;
  ctx.pending = ctx.advanced = false;
  // Keep the committed contact identities and exact anchor parameter as evidence.
  // The next query skips only origins at this exact consumed coordinate.
  p.r_last_current() = p.r();
}
} // namespace openmc
