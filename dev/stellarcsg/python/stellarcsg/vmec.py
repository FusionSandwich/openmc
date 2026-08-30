"""Minimal, deterministic VMEC boundary reader for StellarCSG compilation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file


@dataclass(frozen=True)
class VmecBoundary:
    """Fourier representation of the last closed VMEC flux surface.

    VMEC stores lengths in metres and ``xn`` with the field-period multiplier
    already applied. Public methods return transport coordinates in centimetres.
    """

    source_path: str
    n_field_periods: int
    xm: np.ndarray
    xn: np.ndarray
    rmnc_m: np.ndarray
    zmns_m: np.ndarray
    rmns_m: np.ndarray | None
    zmnc_m: np.ndarray | None
    raxis_cc_m: np.ndarray
    zaxis_cs_m: np.ndarray
    raxis_cs_m: np.ndarray | None = None
    zaxis_cc_m: np.ndarray | None = None

    @classmethod
    def from_wout(cls, path: str | Path) -> "VmecBoundary":
        source = Path(path)
        with netcdf_file(source, "r", mmap=False) as handle:
            variables = handle.variables

            def array(name: str) -> np.ndarray:
                return np.array(variables[name].data, dtype=np.float64, copy=True)

            def optional(name: str) -> np.ndarray | None:
                return array(name) if name in variables else None

            nfp = int(np.asarray(variables["nfp"].data).item())
            rmnc = array("rmnc")[-1]
            zmns = array("zmns")[-1]
            rmns_all = optional("rmns")
            zmnc_all = optional("zmnc")
            return cls(
                source_path=str(source),
                n_field_periods=nfp,
                xm=array("xm"),
                xn=array("xn"),
                rmnc_m=rmnc,
                zmns_m=zmns,
                rmns_m=None if rmns_all is None else rmns_all[-1],
                zmnc_m=None if zmnc_all is None else zmnc_all[-1],
                raxis_cc_m=array("raxis_cc"),
                zaxis_cs_m=array("zaxis_cs"),
                raxis_cs_m=optional("raxis_cs"),
                zaxis_cc_m=optional("zaxis_cc"),
            )

    def position_cm(self, theta: np.ndarray, phi: np.ndarray) -> np.ndarray:
        position, _, _ = self.position_and_derivatives_cm(theta, phi)
        return position

    def position_and_derivatives_cm(
        self, theta: np.ndarray, phi: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return position and derivatives with respect to theta and phi."""
        theta_array, phi_array = np.broadcast_arrays(
            np.asarray(theta, dtype=np.float64),
            np.asarray(phi, dtype=np.float64),
        )
        phase = (
            theta_array[..., None] * self.xm
            - phi_array[..., None] * self.xn
        )
        radius_m = np.sum(self.rmnc_m * np.cos(phase), axis=-1)
        height_m = np.sum(self.zmns_m * np.sin(phase), axis=-1)
        radius_theta_m = np.sum(
            -self.xm * self.rmnc_m * np.sin(phase), axis=-1
        )
        radius_phi_m = np.sum(
            self.xn * self.rmnc_m * np.sin(phase), axis=-1
        )
        height_theta_m = np.sum(
            self.xm * self.zmns_m * np.cos(phase), axis=-1
        )
        height_phi_m = np.sum(
            -self.xn * self.zmns_m * np.cos(phase), axis=-1
        )
        if self.rmns_m is not None:
            radius_m += np.sum(self.rmns_m * np.sin(phase), axis=-1)
            radius_theta_m += np.sum(
                self.xm * self.rmns_m * np.cos(phase), axis=-1
            )
            radius_phi_m += np.sum(
                -self.xn * self.rmns_m * np.cos(phase), axis=-1
            )
        if self.zmnc_m is not None:
            height_m += np.sum(self.zmnc_m * np.cos(phase), axis=-1)
            height_theta_m += np.sum(
                -self.xm * self.zmnc_m * np.sin(phase), axis=-1
            )
            height_phi_m += np.sum(
                self.xn * self.zmnc_m * np.sin(phase), axis=-1
            )
        cos_phi = np.cos(phi_array)
        sin_phi = np.sin(phi_array)
        position = 100.0 * np.stack(
            (
                radius_m * cos_phi,
                radius_m * sin_phi,
                height_m,
            ),
            axis=-1,
        )
        dtheta = 100.0 * np.stack(
            (
                radius_theta_m * cos_phi,
                radius_theta_m * sin_phi,
                height_theta_m,
            ),
            axis=-1,
        )
        dphi = 100.0 * np.stack(
            (
                radius_phi_m * cos_phi - radius_m * sin_phi,
                radius_phi_m * sin_phi + radius_m * cos_phi,
                height_phi_m,
            ),
            axis=-1,
        )
        return position, dtheta, dphi

    def axis_cm(self, phi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        phi_array = np.asarray(phi, dtype=np.float64)
        mode = np.arange(self.raxis_cc_m.size, dtype=np.float64)
        phase = self.n_field_periods * phi_array[..., None] * mode
        radius_m = np.sum(self.raxis_cc_m * np.cos(phase), axis=-1)
        height_m = np.sum(self.zaxis_cs_m * np.sin(phase), axis=-1)
        if self.raxis_cs_m is not None:
            radius_m += np.sum(self.raxis_cs_m * np.sin(phase), axis=-1)
        if self.zaxis_cc_m is not None:
            height_m += np.sum(self.zaxis_cc_m * np.cos(phase), axis=-1)
        return 100.0 * radius_m, 100.0 * height_m

    def surface_grid_cm(self, n_theta: int, n_phi: int) -> tuple[np.ndarray, ...]:
        if n_theta < 4 or n_phi < 4:
            raise ValueError("VMEC surface grid requires at least four samples per angle")
        theta = 2.0 * np.pi * np.arange(n_theta) / n_theta
        phi = (
            2.0 * np.pi * np.arange(n_phi)
            / (self.n_field_periods * n_phi)
        )
        t, p = np.meshgrid(theta, phi, indexing="ij")
        axis_r, axis_z = self.axis_cm(phi)
        return self.position_cm(t, p), phi, axis_r, axis_z
