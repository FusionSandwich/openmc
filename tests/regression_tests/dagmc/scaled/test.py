from pathlib import Path

import openmc
import openmc.lib
import pytest

from tests.testing_harness import PyAPITestHarness


pytestmark = pytest.mark.skipif(
    not openmc.lib._dagmc_enabled(),
    reason="DAGMC CAD geometry is not enabled.",
)


@pytest.fixture
def model():
    openmc.reset_auto_ids()

    fuel = openmc.Material(40, name="no-void fuel")
    coolant = openmc.Material(41, name="water")
    fuel.add_nuclide("Fe56", 1.0)
    coolant.add_nuclide("Fe56", 1.0)
    fuel.set_density("g/cm3", 7.0)
    coolant.set_density("g/cm3", 1.0)

    dagmc = openmc.DAGMCUniverse(
        Path("../legacy/dagmc.h5m"), length_multiplier=0.4)
    model = openmc.Model(
        geometry=openmc.Geometry(dagmc),
        materials=openmc.Materials([fuel, coolant]),
    )
    model.settings.run_mode = "fixed source"
    model.settings.source = openmc.IndependentSource(
        space=openmc.stats.Point((-1.3, 0.7, 1.8)),
        energy=openmc.stats.Discrete([2.0e6], [1.0]),
    )
    model.settings.batches = 10
    model.settings.particles = 500
    model.settings.seed = 19073486328125

    cell_tally = openmc.Tally(name="cell reaction rates")
    cell_tally.filters = [openmc.CellFilter([1, 2, 3])]
    cell_tally.scores = ["flux"]

    material_tally = openmc.Tally(name="material reaction rates")
    material_tally.filters = [openmc.MaterialFilter([40, 41])]
    material_tally.scores = ["absorption"]

    current_tally = openmc.Tally(name="vacuum boundary current")
    current_tally.filters = [openmc.SurfaceFilter([24, 25, 26, 27, 28, 29])]
    current_tally.scores = ["current"]

    model.tallies = [cell_tally, material_tally, current_tally]
    return model


def test_scaled_dagmc_transport(model, capsys):
    harness = PyAPITestHarness("statepoint.10.h5", model)
    harness.main()

    output = capsys.readouterr().out.lower()
    assert "lost particle" not in output
    assert "could not locate particle" not in output
    assert not list(Path.cwd().glob("particle_*.h5"))
