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
from .coil import (
    CapsuleTube,
    CoilHexMesh,
    build_coil_local_mesh,
    coil_mesh_summary,
    resample_closed_centerline,
    rotation_minimizing_frames,
    write_coil_mesh_hdf5,
    write_coil_mesh_summary,
    write_coil_mesh_vtk,
)

__all__ = [
    "HexMesh",
    "PeriodicRadialSurfaceData",
    "CoilCenterline",
    "CapsuleTube",
    "CoilHexMesh",
    "build_coil_local_mesh",
    "build_layer_mesh",
    "coil_mesh_summary",
    "compile_radial_build",
    "periodic_surface_from_vmec_arrays",
    "read_makegrid_coils",
    "read_vmec_surface",
    "resample_closed_centerline",
    "rotation_minimizing_frames",
    "write_coil_collection_hdf5",
    "write_coil_mesh_hdf5",
    "write_coil_mesh_summary",
    "write_coil_mesh_vtk",
    "read_surface",
    "write_legacy_vtk",
    "write_mesh_hdf5",
    "write_moab_h5m",
    "write_surface",
    "write_surface_collection",
]
