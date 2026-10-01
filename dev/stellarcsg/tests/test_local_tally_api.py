"""Standard-mesh API and invalid-input controls; transport is tested separately."""
from pathlib import Path
import sys
import unittest

import numpy as np
import openmc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from stellarcsg.openmc_tally import make_energy_resolved_mesh_tally


class LocalTallyTests(unittest.TestCase):
    def setUp(self):
        openmc.reset_auto_ids()
        self.mesh = openmc.RegularMesh()
        self.mesh.dimension = [2, 2, 2]
        self.mesh.lower_left = [-1, -1, -1]
        self.mesh.upper_right = [1, 1, 1]

    def test_standard_mesh_and_cell_filters(self):
        cell = openmc.Cell()
        tally = make_energy_resolved_mesh_tally(
            mesh=self.mesh, cells=[cell], energy_bounds_eV=[0, 1e6, 20e6],
            scores=["flux", "damage-energy"])
        self.assertIsInstance(tally.filters[0], openmc.MeshFilter)
        self.assertIs(tally.filters[0].mesh, self.mesh)
        np.testing.assert_array_equal(tally.filters[2].bins, [cell.id])
        self.assertEqual(tally.estimator, "tracklength")
        self.assertEqual(tally.scores, ["flux", "damage-energy"])

    def test_legacy_moab_constructor_preserved(self):
        tally = make_energy_resolved_mesh_tally(
            mesh_file="local.h5m", energy_bounds_eV=[0, 20e6])
        self.assertEqual(tally.filters[0].mesh.library, "moab")

    def test_bad_energy_and_mesh_inputs(self):
        for bounds in ([0, np.nan], [0, np.inf], [-1, 1], [1, 1], [2, 1], [1]):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                make_energy_resolved_mesh_tally(mesh=self.mesh, energy_bounds_eV=bounds)
        for kwargs in ({}, {"mesh": self.mesh, "mesh_file": "x.h5m"},
                       {"mesh": self.mesh, "cells": []}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                make_energy_resolved_mesh_tally(energy_bounds_eV=[0, 1], **kwargs)
        with self.assertRaises(TypeError):
            make_energy_resolved_mesh_tally(mesh="fake", energy_bounds_eV=[0, 1])


if __name__ == "__main__":
    unittest.main()
