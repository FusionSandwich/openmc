"""Reproducible local plasma/coil proxy transport observations.

Run preparation once, then one bounded fresh process per observation.
No download, environment mutation, or automatic successor is performed.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import time

import h5py
import numpy as np
import openmc
from stellarcsg.coil import SweptSplineData, write_swept_collection
from stellarcsg.surface import PeriodicRadialSurfaceData
from stellarcsg.io import write_surface

ENERGY = [0., 1.e3, 1.e5, 1.e6, 5.e6, 1.e7, 14.2e6]
SCORES = ["flux", "total", "absorption", "damage-energy"]
DATA = Path("/mnt/c/Users/joshu/Documents/2026_DPA/openc-hts-dpa/.data/openmc")
ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def material():
    result = openmc.Material(material_id=1, name="Fe56 matched proxy")
    result.add_nuclide("Fe56", 1.)
    result.set_density("g/cm3", 7.8)
    result.temperature = 300.
    return result


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    xs = DATA / "FENDL-3.1d_Fe56.h5"
    with h5py.File(xs) as handle:
        if "reaction_444" not in handle["Fe56/reactions"]:
            raise ValueError("Fe56 has no MT444; damage comparison is unsupported")
        if "300K" not in handle["Fe56/kTs"]:
            raise ValueError("300 K data missing")
    # Exact constants bypass interpolation/fitting noise in the plasma pair.
    plasma = PeriodicRadialSurfaceData(
        "plasma", 1, np.full(8, 100.), np.zeros(8), np.full((8, 8), 20.),
        source_metadata={"fixture": "exact constant torus R100 r20"})
    write_surface(output / "plasma.h5", plasma)
    n = 64
    theta = 2 * np.pi * np.arange(n) / n
    # Correct the cardinal seam shrinkage; still an explicitly approximate
    # circular curve between seams, never an exact torus claim.
    control_radius = 300. / (2. + math.cos(2 * math.pi / n))
    centers = np.column_stack((control_radius * np.cos(theta),
                               control_radius * np.sin(theta), np.zeros(n)))
    normals = np.tile([0., 0., 1.], (n, 1))
    binormals = np.column_stack((np.cos(theta), np.sin(theta), np.zeros(n)))
    coil = SweptSplineData(0, centers, normals, binormals,
                          np.full(n, 5.), np.full(n, 5.), 200 * math.pi,
                          {"fixture": "64 control circular coil proxy"}, "")
    digest = hashlib.sha256(coil.canonical_metadata_json().encode())
    for array in (centers, normals, binormals,
                  coil.major_radius_coefficients_cm,
                  coil.minor_radius_coefficients_cm):
        digest.update(np.asarray(array, dtype="<f8", order="C").tobytes())
    coil = replace(coil, content_id="sha256:" + digest.hexdigest())
    write_swept_collection(output / "coil.h5", [coil])
    rng = np.random.default_rng(492781)
    directions = rng.normal(size=(256, 3))
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    sites = [openmc.SourceParticle(r=(100., 0., 0.), u=u, E=14.1e6, wgt=1.)
             for u in directions]
    openmc.write_source_file(sites, output / "source.h5")
    meta = dict(
        schema="stellarcsg.proxy-fixtures/v1", plasma_id=plasma.content_id,
        coil_id=coil.content_id, source_sites=256, source_energy_eV=14.1e6,
        source_location_cm=[100., 0., 0.], material="Fe56",
        density_g_cm3=7.8, temperature_K=300., displacement_energy_eV=40.,
        displacement_energy_status="Explicit NRT test convention, not fitted material data",
        energy_bins_eV=ENERGY, scores=SCORES,
        plasma_material_volume_cm3=2 * math.pi**2 * 100 * (21**2 - 20**2),
        coil_reference_volume_cm3=2 * math.pi**2 * 100 * 5**2,
        coil_volume_policy="Native torus reference volume; spline DPA index uses same normalization, not a certified physical coil atom count",
        hashes={name: sha(output / name)
                for name in ("plasma.h5", "coil.h5", "source.h5")},
        data_index_sha256=sha(DATA / "cross_sections.xml"),
        Fe56_h5_sha256=sha(xs), Fe56_bytes=xs.stat().st_size, MT444_present=True)
    save(output / "manifest.json", meta)
    print(json.dumps(meta))


def model(args, fixture, meta):
    openmc.reset_auto_ids()
    iron = material()
    native = args.variant in ("native", "annulus")
    if args.family == "plasma":
        if args.variant not in ("native", "spline"):
            raise ValueError("plasma supports native and spline variants")
        surface = (openmc.ZTorus(a=100., b=20., c=20., surface_id=10)
                   if native else openmc.PeriodicSplineSurface(
                       fixture / "plasma.h5", "/surfaces/plasma",
                       meta["plasma_id"], surface_id=10))
        outer = openmc.ZTorus(a=100., b=21., c=21., surface_id=11)
        region = +surface & -outer
        cells = [openmc.Cell(1, region=-surface),
                 openmc.Cell(2, fill=iron, region=region)]
        exterior = +outer
        volume = meta["plasma_material_volume_cm3"]
    else:
        if args.variant == "native":
            surface = openmc.ZTorus(a=100., b=5., c=5., surface_id=10)
            region = -surface
        elif args.variant == "annulus":
            # Equal volume and radial thickness, rectangular rather than round
            # section: useful cost/shape sensitivity control, not equivalence.
            inner = openmc.ZCylinder(r=95., surface_id=10)
            outer = openmc.ZCylinder(r=105., surface_id=11)
            bottom = openmc.ZPlane(z0=-5 * math.pi / 4, surface_id=12)
            top = openmc.ZPlane(z0=5 * math.pi / 4, surface_id=13)
            region = +inner & -outer & +bottom & -top
        elif args.variant in ("spline", "ordered"):
            surface = openmc.SweptSplineSurface(
                fixture / "coil.h5", "/coils/coil_000", meta["coil_id"],
                representation="exact_control_offset",
                bernstein_prefix=args.variant == "spline", surface_id=10)
            region = -surface
        else:
            raise ValueError("unknown coil variant")
        cells = [openmc.Cell(2, fill=iron, region=region)]
        exterior = ~region
        volume = meta["coil_reference_volume_cm3"]
    vacuum = openmc.Sphere(r=150., surface_id=99, boundary_type="vacuum")
    cells.append(openmc.Cell(3, region=exterior & -vacuum))
    settings = openmc.Settings()
    settings.run_mode = "fixed source"
    settings.particles = args.particles
    settings.batches = args.batches
    settings.seed = args.seed
    settings.source = openmc.FileSource(fixture / "source.h5")
    settings.temperature = {"default": 300., "method": "nearest", "tolerance": 1.}
    settings.statepoint = {"batches": list(range(1, args.batches + 1))}
    settings.output = {"summary": True, "tallies": False}
    settings.max_lost_particles = 1
    settings.rel_max_lost_particles = 1.e-12
    settings.verbosity = 5
    if args.tracks:
        settings.track = [(1, 1, i) for i in range(1, min(args.particles, 8) + 1)]
    spectra = openmc.Tally(1, name="material energy-resolved scores")
    spectra.filters = [openmc.CellFilter([2]), openmc.EnergyFilter(ENERGY)]
    spectra.scores = SCORES
    spectra.estimator = "tracklength"
    integral = openmc.Tally(2, name="material integral scores")
    integral.filters = [openmc.CellFilter([2])]
    integral.scores = SCORES
    integral.estimator = "tracklength"
    # An independent material filter must have the same ownership as cell 2.
    ownership = openmc.Tally(3, name="material ownership closure")
    ownership.filters = [openmc.MaterialFilter([1])]
    ownership.scores = SCORES
    ownership.estimator = "tracklength"
    return (openmc.Model(openmc.Geometry(cells), openmc.Materials([iron]),
                         settings, openmc.Tallies([spectra, integral, ownership])),
            volume, iron.get_nuclide_atom_densities()["Fe56"] * 1.e24 * volume)


def observe(args):
    fixture = args.fixtures.resolve()
    meta = json.loads((fixture / "manifest.json").read_text())
    for name, expected in meta["hashes"].items():
        if sha(fixture / name) != expected:
            raise ValueError(f"changed fixture: {name}")
    if (sha(DATA / "cross_sections.xml") != meta["data_index_sha256"]
            or sha(DATA / "FENDL-3.1d_Fe56.h5") != meta["Fe56_h5_sha256"]):
        raise ValueError("nuclear data changed")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    instance, volume, atoms = model(args, fixture, meta)
    instance.export_to_xml(output)
    binary = (ROOT / "build/astra-native/bin/openmc").resolve()
    library = (ROOT / "build/astra-native/lib/libopenmc.so").resolve()
    inputs = {name: sha(output / name) for name in
              ("geometry.xml", "materials.xml", "settings.xml", "tallies.xml")}
    identities = dict(binary=sha(binary), library=sha(library),
                      harness=sha(__file__), fixture_manifest=sha(fixture / "manifest.json"),
                      source=meta["hashes"]["source.h5"],
                      data=meta["Fe56_h5_sha256"], data_index=meta["data_index_sha256"])
    env = dict(os.environ, OPENMC_CROSS_SECTIONS=str(DATA / "cross_sections.xml"),
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               LD_LIBRARY_PATH=str(library.parent))
    loader = subprocess.run(["ldd", str(binary)], capture_output=True, text=True,
                            env=env, timeout=10, check=True)
    if str(library) not in loader.stdout:
        raise ValueError("executable is not bound to selected libopenmc")
    launch = dict(family=args.family, variant=args.variant, seed=args.seed,
                  particles=args.particles, batches=args.batches,
                  histories=args.particles * args.batches, threads=1,
                  identities=identities, input_hashes=inputs,
                  energy_bins_eV=ENERGY, scores=SCORES, estimator="tracklength",
                  MT444_present=True, damage_model="NRT-test-index",
                  volume_cm3=volume, atoms=atoms, displacement_energy_eV=40.,
                  timeout_s=args.timeout, memory_cap_bytes=2 * 1024**3,
                  started=time.time())
    save(output / "launch.json", launch)
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    started = time.perf_counter()
    timed_out = False
    with (output / "stdout.txt").open("w") as stdout, (output / "stderr.txt").open("w") as stderr:
        try:
            result = subprocess.run([str(binary)], cwd=output, env=env,
                                    stdout=stdout, stderr=stderr,
                                    timeout=args.timeout, preexec_fn=limits)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code, timed_out = None, True
    wall = time.perf_counter() - started
    statepoints = sorted(output.glob("statepoint.*.h5"),
                         key=lambda x: int(x.name.split(".")[1]))
    diagnostics = (output / "stdout.txt").read_text() + (output / "stderr.txt").read_text()
    forbidden = [token for token in ("could not be located", "lost particle",
                                    "unresolved", "ERROR:", "terminate called")
                 if token in diagnostics.lower() or token in diagnostics]
    receipt = dict(launch, exit_code=code, timed_out=timed_out, wall_s=wall,
                   forbidden_diagnostics=forbidden,
                   statepoints=[p.name for p in statepoints], state="FAILED_OR_INCOMPLETE")
    if code == 0 and not timed_out and not forbidden and len(statepoints) == args.batches:
        batches, cumulative_previous = [], None
        for index, path in enumerate(statepoints, 1):
            with openmc.StatePoint(path, autolink=False) as sp:
                if (sp.n_particles != args.particles or sp.n_batches != args.batches
                        or sp.current_batch != index or sp.seed != args.seed
                        or sp.n_realizations != index):
                    raise ValueError("statepoint history/batch identity mismatch")
                values = np.concatenate([sp.get_tally(id=i).sum.ravel() for i in (1, 2, 3)])
                if not np.isfinite(values).all():
                    raise ValueError("nonfinite tally")
                batches.append((values if cumulative_previous is None
                                else values - cumulative_previous).tolist())
                cumulative_previous = values
                if index == args.batches:
                    tally_means = {str(i): sp.get_tally(id=i).mean.tolist()
                                   for i in (1, 2, 3)}
                    tally_std = {str(i): sp.get_tally(id=i).std_dev.tolist()
                                 for i in (1, 2, 3)}
                    runtime = sp.runtime
                    leakage = [
                        dict(name=row["name"].decode(),
                             mean=float(row["mean"]), std_dev=float(row["std_dev"]))
                        for row in sp.global_tallies]
        values = np.asarray(batches)
        spectral = np.array(tally_means["1"]).reshape(len(ENERGY) - 1, len(SCORES))
        integral = np.array(tally_means["2"]).ravel()
        owner = np.array(tally_means["3"]).ravel()
        if not np.allclose(spectral.sum(axis=0), integral, rtol=1e-11, atol=1e-12):
            raise ValueError("spectral/integral closure failed")
        if not np.allclose(owner, integral, rtol=1e-11, atol=1e-12):
            raise ValueError("cell/material ownership closure failed")
        receipt.update(state="OBSERVED_COMPLETE", batch_scores=values.tolist(),
                       tally_means=tally_means, tally_std_dev=tally_std,
                       runtime_s=runtime, global_tallies=leakage,
                       nrt_dpa_index_per_source=float(.8 * integral[3] / (2 * 40 * atoms)),
                       normalization="per source particle; coil uses declared reference atom count",
                       closure="PASS", statepoint_hashes={p.name: sha(p) for p in statepoints})
    receipt["identities_after"] = dict(
        binary=sha(binary), library=sha(library), harness=sha(__file__),
        fixture_manifest=sha(fixture / "manifest.json"), source=sha(fixture / "source.h5"),
        data=sha(DATA / "FENDL-3.1d_Fe56.h5"), data_index=sha(DATA / "cross_sections.xml"))
    receipt["inputs_after"] = {name: sha(output / name) for name in inputs}
    if receipt["identities_after"] != identities or receipt["inputs_after"] != inputs:
        receipt["state"] = "PROVENANCE_CHANGED"
    save(output / "receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in
                     ("family", "variant", "seed", "state", "exit_code", "wall_s")},
                     allow_nan=False))
    if receipt["state"] != "OBSERVED_COMPLETE":
        raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--family", choices=("plasma", "coil"))
    parser.add_argument("--variant", choices=("native", "spline", "ordered", "annulus"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--particles", type=int, default=10)
    parser.add_argument("--batches", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1741)
    parser.add_argument("--timeout", type=float, default=180.)
    parser.add_argument("--tracks", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare(args.prepare.resolve())
    else:
        if not args.fixtures or not args.family or not args.variant or not args.output:
            parser.error("fixtures, family, variant and output are required")
        if args.particles < 1 or args.batches < 2 or args.timeout <= 0:
            parser.error("positive particles/timeout and >=2 batches required")
        observe(args)


if __name__ == "__main__":
    main()
