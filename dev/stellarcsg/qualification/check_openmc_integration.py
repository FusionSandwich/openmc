"""Bounded native CSG tally/source integration worker; one case per process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
import numpy as np
import openmc
import openmc.lib

from proxy_transport import DATA, ENERGY, ROOT, SCORES, model, sha
from stellarcsg.openmc_tally import make_energy_resolved_mesh_tally


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def regular(bounds, dimension, mesh_id):
    mesh = openmc.RegularMesh(mesh_id)
    mesh.lower_left, mesh.upper_right = bounds
    mesh.dimension = dimension
    return mesh


def assemble(args, fixture):
    meta = json.loads((fixture / "manifest.json").read_text())
    settings = SimpleNamespace(family=args.family, variant=args.variant,
                               particles=200 if args.family == "plasma" else 40,
                               batches=5, seed=917431, tracks=False)
    result, _, _ = model(settings, fixture, meta)
    result.tallies.clear()
    openmc.Tally.reset_ids()
    cells = result.geometry.get_all_cells()
    original = cells[2].region
    iron = cells[2].fill
    bounds = ([[115., -10., -10.], [122., 10., 10.]] if args.family == "plasma"
              else [[98., -3., -3.], [103., 3., 3.]])
    box = openmc.model.RectangularParallelepiped(
        bounds[0][0], bounds[1][0], bounds[0][1], bounds[1][1], bounds[0][2], bounds[1][2])
    midplane = openmc.XPlane(x0=0.)
    cells[2].region = original & -midplane
    local = openmc.Cell(4, name="local scoring cell", fill=iron,
                        region=original & +midplane & -box)
    remainder = openmc.Cell(5, fill=iron, region=original & +midplane & +box)
    result.geometry.root_universe.add_cells([local, remainder])
    material_cells = [cells[2], local, remainder]
    global_mesh = regular(([-150.] * 3, [150.] * 3), [4, 4, 4], 101)
    local_mesh = regular(bounds, [3, 2, 2], 102)
    rect = openmc.RectilinearMesh(103)
    rect.x_grid = rect.y_grid = rect.z_grid = [-150., 0., 150.]
    cylinder = openmc.CylindricalMesh(
        r_grid=[0., 80., 100., 125., 151.], z_grid=[-151., 0., 151.],
        phi_grid=[0., np.pi, 2 * np.pi], mesh_id=104)
    sphere = openmc.SphericalMesh(
        r_grid=[0., 80., 125., 160.], theta_grid=[0., np.pi / 2, np.pi],
        phi_grid=[0., np.pi, 2 * np.pi], mesh_id=105)
    source_mesh = regular(([95., -1., -1.], [105., 1., 1.]), [2, 1, 1], 106)
    if args.family == "plasma":
        constraints = {"domains": [cells[1]], "rejection_strategy": "resample"}
        if args.source == "mesh":
            components = [openmc.IndependentSource(
                strength=p, angle=openmc.stats.Isotropic(),
                energy=openmc.stats.Discrete([energy], [1.]))
                for p, energy in ((.25, 2.45e6), (.75, 14.1e6))]
            result.settings.source = openmc.MeshSource(
                source_mesh, components, constraints=constraints)
        else:
            result.settings.source = openmc.IndependentSource(
                space=openmc.stats.Box([119., -1., -1.], [121., 1., 1.]),
                angle=openmc.stats.Isotropic(),
                energy=openmc.stats.Discrete([14.1e6], [1.]), constraints=constraints)
    tallies = []

    def tally(index, name, filters, scores=SCORES, estimator="tracklength"):
        item = openmc.Tally(index, name=name)
        item.filters = filters
        item.scores = scores
        item.estimator = estimator
        tallies.append(item)
        return item

    material_filter = openmc.MaterialFilter([iron])
    energy_filter = openmc.EnergyFilter(ENERGY)
    tally(1, "material reference", [material_filter])
    tally(2, "subcell spectra", [openmc.CellFilter(material_cells), energy_filter])
    for index, mesh, selected in ((3, global_mesh, material_cells), (4, local_mesh, [local])):
        item = make_energy_resolved_mesh_tally(mesh=mesh, cells=selected,
                                               energy_bounds_eV=ENERGY, scores=SCORES)
        item.id = index
        item.name = "global Cartesian" if index == 3 else "local Cartesian"
        tallies.append(item)
    for index, mesh in ((5, rect), (6, cylinder), (7, sphere)):
        tally(index, type(mesh).__name__, [openmc.MeshFilter(mesh), material_filter, energy_filter])
    tally(8, "cell instances", [openmc.CellInstanceFilter([(c, 0) for c in material_cells]), energy_filter])
    tally(9, "universe and material", [openmc.UniverseFilter([result.geometry.root_universe]), material_filter])
    tally(10, "spline surface current", [openmc.SurfaceFilter([10]), energy_filter], ["current"], "analog")
    tally(11, "Cartesian mesh surface current", [openmc.MeshSurfaceFilter(global_mesh)], ["current"], "analog")
    all_cells = result.geometry.get_all_cells()
    tally(12, "birth cell", [openmc.CellBornFilter(list(all_cells)), material_filter])
    tally(13, "collision scores", [material_filter, energy_filter], estimator="collision")
    tally(14, "analog scores", [material_filter, energy_filter], ["total", "absorption", "scatter"], "analog")
    tally(15, "outgoing energy and scattering cosine", [material_filter, energy_filter,
          openmc.EnergyoutFilter(ENERGY), openmc.MuFilter([-1., 0., 1.]),
          openmc.ParticleFilter(["neutron"])], ["scatter"], "analog")
    tally(16, "constant response weight", [material_filter,
          openmc.EnergyFunctionFilter([0., 20e6], [2., 2.])])
    tally(17, "local cell reference", [openmc.CellFilter([local]), energy_filter])
    tally(18, "time and particle", [material_filter, openmc.TimeFilter([0., 1e-7, 1.]),
          openmc.ParticleFilter(["neutron"])])
    if args.source == "mesh":
        # Secondary neutrons can be born in the shell, outside the source mesh.
        tally(19, "birth mesh including secondary births", [openmc.MeshBornFilter(global_mesh), material_filter])
    result.tallies = openmc.Tallies(tallies)
    result.settings.volume_calculations = [openmc.VolumeCalculation(
        [local], 4096, lower_left=bounds[0], upper_right=bounds[1])]
    result.settings.output = {"summary": True, "tallies": False}
    result.settings.statepoint = {"batches": [5]}
    return result, bounds


def sample_checks(args):
    sites = openmc.lib.sample_external_source(512, prn_seed=675231, as_array=True)
    require(np.isfinite(sites["r"]).all() and np.isfinite(sites["u"]).all(), "nonfinite source")
    require(np.all(sites["wgt"] == 1.), "source weights changed")
    require(np.allclose(np.linalg.norm(sites["u"], axis=1), 1., rtol=0, atol=2e-15), "source directions")
    ids = [openmc.lib.find_cell(tuple(r))[0].id for r in sites["r"]]
    expected_cell = 1 if args.family == "plasma" else 4
    require(set(ids) == {expected_cell}, "sampled source left expected CSG cell")
    radial = np.hypot(sites["r"][:, 0], sites["r"][:, 1])
    if args.family == "plasma":
        require(np.all((radial - 100.)**2 + sites["r"][:, 2]**2 < 20.**2),
                "analytic torus independently rejects source")
    if args.source == "mesh":
        left = sites["r"][:, 0] < 100.
        require(np.all(sites["E"][left] == 2.45e6)
                and np.all(sites["E"][~left] == 14.1e6), "conditional source spectrum/order")
        require(abs(left.mean() - .25) < .08, "mesh source probabilities")
    else:
        require(np.all(sites["E"] == 14.1e6), "source energy changed")
    np.save("sampled-source.npy", sites, allow_pickle=False)
    return dict(samples=len(sites), observed_cells=sorted(set(ids)),
                sha256=sha("sampled-source.npy"), energies_eV=sorted(set(sites["E"].tolist())))


def inspect_results(args, result):
    with openmc.StatePoint("statepoint.5.h5") as statepoint:
        require(statepoint.n_particles == result.settings.particles
                and statepoint.n_batches == 5 and statepoint.current_batch == 5
                and statepoint.n_realizations == 5 and statepoint.seed == 917431,
                "incomplete or wrong statepoint")
        rows, means = {}, {}
        for index, tally in statepoint.tallies.items():
            require(np.isfinite(tally.mean).all() and np.isfinite(tally.std_dev).all(), "nonfinite tallies")
            means[index] = tally.mean
            frame = tally.get_pandas_dataframe()
            require(len(frame) == tally.mean.size, "DataFrame dropped bins")
            reshaped = tally.get_reshaped_data(expand_dims=True)
            require(np.isclose(reshaped.sum(), tally.mean.sum()), "reshape lost tally data")
            rows[str(index)] = dict(name=tally.name, scores=tally.scores,
                filters=[type(f).__name__ for f in tally.filters], estimator=tally.estimator,
                shape=list(tally.mean.shape), mean=tally.mean.tolist(), std_dev=tally.std_dev.tolist())
        reference = means[1].sum(axis=(0, 1))
        closures = {}
        for index in (2, 3, 5, 6, 7, 8, 9, 12, 18):
            actual = means[index].sum(axis=(0, 1))
            require(np.allclose(actual, reference, rtol=2e-10, atol=1e-10), f"partition closure {index}")
            closures[str(index)] = float(np.max(np.abs(actual - reference)))
        if 19 in means:
            require(np.allclose(means[19].sum(axis=(0, 1)), reference, rtol=2e-10, atol=1e-10), "birth mesh closure")
        require(np.allclose(means[4].sum(axis=(0, 1)), means[17].sum(axis=(0, 1)),
                            rtol=2e-10, atol=1e-10), "local mesh/cell closure")
        require(means[17].sum() > 0 and means[4].sum() > 0, "local tally was not exercised")
        require(np.allclose(means[16].sum(axis=(0, 1)), 2 * reference, rtol=2e-10, atol=1e-10), "response weighting")
        local_tally = statepoint.get_tally(id=4)
        flux = local_tally.get_slice(scores=["flux"])
        flux.get_pandas_dataframe().to_csv("local-flux.csv", index=False)
        require(np.array_equal(flux.mean.ravel(), means[4][:, :, 0].ravel()), "score slice changed order")
        surface = statepoint.summary.geometry.get_all_surfaces()[10]
        expected = ("PeriodicSplineSurface" if args.family == "plasma" else "SweptSplineSurface")
        require(type(surface).__name__ == ("ZTorus" if args.variant == "native" else expected), "summary surface dispatch")
        volume = openmc.VolumeCalculation.from_hdf5("volume_1.h5")
        local_volume = volume.volumes[4]
        require(local_volume.n > 0 and np.isfinite([local_volume.n, local_volume.s]).all(), "local volume unavailable")
        return dict(tallies=rows, closure_max_abs=closures, local_volume_cm3=[local_volume.n, local_volume.s],
                    runtime_s=statepoint.runtime, summary_surface=type(surface).__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=("plasma", "coil"), required=True)
    parser.add_argument("--variant", choices=("native", "spline"), required=True)
    parser.add_argument("--source", choices=("mesh", "box", "file"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--library-sha256", default="7fa3dbf5bef055aa2227842800e54a2daa84537a1ba6730e97f4fb6cd25d317e")
    args = parser.parse_args()
    require((args.family == "coil") == (args.source == "file"), "invalid family/source")
    fixture = ROOT / "dev/stellarcsg/reports/transport-proxy-20260926/fixtures"
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    library = ROOT / "openmc/lib/libopenmc.so"
    require(Path(openmc.__file__).resolve().parent == ROOT / "openmc", "wrong OpenMC Python package")
    require(Path(openmc.lib._dll._name).resolve() == library.resolve(), "wrong loaded native library")
    require(sha(library) == args.library_sha256, "wrong native library")
    paths = [library, Path(__file__), ROOT / "dev/stellarcsg/python/stellarcsg/openmc_tally.py",
             fixture / "manifest.json", fixture / "plasma.h5", fixture / "coil.h5",
             fixture / "source.h5", DATA / "cross_sections.xml", DATA / "FENDL-3.1d_Fe56.h5"]
    identities = {str(p): sha(p) for p in paths}
    result, bounds = assemble(args, fixture)
    os.chdir(args.output)
    result.export_to_xml()
    restored = openmc.Model.from_xml()
    require(len(restored.tallies) == len(result.tallies), "XML roundtrip lost tallies")
    require(type(restored.geometry.get_all_surfaces()[10])
            is type(result.geometry.get_all_surfaces()[10]), "XML roundtrip surface dispatch")
    xml_hashes = {p.name: sha(p) for p in Path('.').glob('*.xml')}
    save("launch.json", dict(family=args.family, variant=args.variant, source=args.source,
        library=identities[str(library)], identities=identities, xml_hashes=xml_hashes,
        particles=result.settings.particles, batches=5, seed=917431,
        local_bounds_cm=bounds, memory_cap_bytes=2 * 1024**3, timeout_s=180))
    # Native C API geometry, sampling, volume and transport use the same library.
    with openmc.lib.run_in_memory(output=False):
        sampling = sample_checks(args)
        print("Native source sampling and cell lookup passed", flush=True)
        openmc.lib.calculate_volumes(output=False)
        print("Native local volume calculation completed", flush=True)
        openmc.lib.run(output=True)
    observed = inspect_results(args, result)
    require(identities == {str(p): sha(p) for p in paths}, "inputs changed during integration")
    require(xml_hashes == {p.name: sha(p) for p in Path('.').glob('*.xml')}, "XML changed")
    outputs = {p.name: sha(p) for p in Path('.').iterdir() if p.is_file() and p.name != "receipt.json"}
    save("receipt.json", dict(state="OBSERVED_INTEGRATION_PASS", family=args.family,
        variant=args.variant, source=args.source, identities=identities,
        xml_hashes=xml_hashes, output_hashes=outputs, sampling=sampling, **observed,
        claim_boundary="Finite proxy integration checks, not all tally capabilities, physical source admission or full-spectrum equivalence. Volume is a stochastic local-cell estimate."))
    print(json.dumps(dict(state="OBSERVED_INTEGRATION_PASS", family=args.family,
                         variant=args.variant, source=args.source, tallies=len(observed["tallies"]))))


if __name__ == "__main__":
    main()
