"""Small public-parameter construction example, no CAD or mesh required.

Run with PYTHONPATH=dev/stellarcsg/python and an unused output directory.
This demonstrates coefficient construction, not transport qualification.
"""
from pathlib import Path
import sys
import numpy as np
from stellarcsg import PeriodicRadialSurfaceData, SweptSplineData, write_swept_collection
from stellarcsg.io import write_surface


def build(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    plasma = PeriodicRadialSurfaceData.analytic_torus(
        name="plasma_boundary", major_radius_cm=100, minor_radius_cm=20,
        n_field_periods=4, helical_amplitude_cm=1)
    angle = np.linspace(0, 2*np.pi, 128, endpoint=False)
    centerline = np.column_stack((100 + 30*np.cos(angle),
                                 np.full_like(angle, 10), 30*np.sin(angle)))
    coil = SweptSplineData.from_centerline(
        1, centerline, major_radius_cm=1, sample_count=128,
        source_metadata={"example": "finite circular envelope", "units": "cm"})
    write_surface(directory / "plasma.h5", plasma)
    write_swept_collection(directory / "coil.h5", [coil])
    return plasma, coil


if __name__ == "__main__":
    build(sys.argv[1])
    print("Simple plasma and finite-coil coefficients written; transport NOT_RUN")
