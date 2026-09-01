"""Plot the retained native WISTELL-D plasma, blanket, and 48-coil model."""

from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from stellarcsg import read_surface

root = Path(__file__).resolve().parents[3]
blanket = root / "dev/stellarcsg/qualified/composite_blanket_families.h5"
coils = root / "dev/stellarcsg/qualified/wistell_d_swept_coils.h5"
names = ["wistell_d_wistell_d_lcfs", "wistell_d_first_wall",
         "wistell_d_breeding_blanket", "wistell_d_shield",
         "wistell_d_vacuum_vessel"]
surfaces = [read_surface(blanket, name) for name in names]
theta = np.linspace(0.0, 2*np.pi, 181)
phi = np.linspace(0.0, np.pi/2, 61)
t, p = np.meshgrid(theta, phi, indexing="ij")

figure = plt.figure(figsize=(13, 5.5), constrained_layout=True)
top = figure.add_subplot(121)
iso = figure.add_subplot(122, projection="3d")
colors = plt.cm.viridis(np.linspace(0.05, 0.85, len(surfaces)))
for color, surface in zip(colors, surfaces):
    points = surface.position(t, p)
    top.plot(points[::6, :, 0].ravel(), points[::6, :, 1].ravel(), '.',
             color=color, ms=0.15, alpha=0.35)
    iso.plot(points[::12, ::3, 0].ravel(), points[::12, ::3, 1].ravel(),
             points[::12, ::3, 2].ravel(), '.', color=color, ms=0.2, alpha=0.25)
with h5py.File(coils, "r") as h5:
    for name in sorted(h5["coils"]):
        center = h5[f"coils/{name}/centerline_coefficients"][...]
        closed = np.vstack((center, center[:1]))
        top.plot(closed[:, 0], closed[:, 1], color="tab:red", lw=0.45, alpha=0.8)
        iso.plot(closed[:, 0], closed[:, 1], closed[:, 2],
                 color="tab:red", lw=0.35, alpha=0.75)
top.set_aspect("equal")
top.set_xlabel("x [cm]")
top.set_ylabel("y [cm]")
top.set_title("top view: 48 coil centerlines and blanket family")
iso.set_title("isometric: one-period surfaces and full 48-coil set")
iso.set_xlabel("x [cm]")
iso.set_ylabel("y [cm]")
iso.set_zlabel("z [cm]")
figure.suptitle("Native WISTELL-D combined geometry\n"
                "c0290b source lineage; physical-normal six-layer build; coil tube radius from retained payload")
out = root / "dev/stellarcsg/plots/composite_blanket_interop/combined_wistell_wireframe.png"
figure.savefig(out, dpi=180)
plt.close(figure)
