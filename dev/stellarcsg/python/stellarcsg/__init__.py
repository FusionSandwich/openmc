"""CAD-free reference tools for the StellarCSG research branch."""

from .io import read_surface, write_surface, write_surface_collection
from .mesh import (
    HexMesh,
    build_layer_mesh,
    write_legacy_vtk,
    write_mesh_hdf5,
    write_moab_h5m,
)
from .surface import PeriodicRadialSurfaceData, compile_radial_build
from .inputs import (
    CoilCenterline,
    periodic_surface_from_vmec_arrays,
    read_makegrid_coils,
    read_vmec_surface,
    write_coil_collection_hdf5,
)

__all__ = [
    "HexMesh",
    "PeriodicRadialSurfaceData",
    "CoilCenterline",
    "build_layer_mesh",
    "compile_radial_build",
    "periodic_surface_from_vmec_arrays",
    "read_makegrid_coils",
    "read_vmec_surface",
    "write_coil_collection_hdf5",
    "read_surface",
    "write_legacy_vtk",
    "write_mesh_hdf5",
    "write_moab_h5m",
    "write_surface",
    "write_surface_collection",
]
