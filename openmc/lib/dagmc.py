from ctypes import c_double, c_int, c_int32, POINTER, c_size_t

import numpy as np

from . import _dll
from .error import _error_handler


__all__ = [
    'dagmc_universe_cell_ids',
    'dagmc_universe_cell_volumes',
]

# DAGMC functions
_dll.openmc_dagmc_universe_get_cell_ids.argtypes = [c_int32, POINTER(c_int32), POINTER(c_size_t)]
_dll.openmc_dagmc_universe_get_cell_ids.restype = c_int
_dll.openmc_dagmc_universe_get_cell_ids.errcheck = _error_handler
_dll.openmc_dagmc_universe_get_num_cells.argtypes = [c_int32, POINTER(c_size_t)]
_dll.openmc_dagmc_universe_get_num_cells.restype = c_int
_dll.openmc_dagmc_universe_get_num_cells.errcheck = _error_handler
_dll.openmc_dagmc_universe_get_cell_volumes.argtypes = [
    c_int32, POINTER(c_double), POINTER(c_size_t)]
_dll.openmc_dagmc_universe_get_cell_volumes.restype = c_int
_dll.openmc_dagmc_universe_get_cell_volumes.errcheck = _error_handler


def dagmc_universe_cell_ids(universe_id: int) -> np.ndarray:
    """Return an array of cell IDs for a DAGMC universe.

    Parameters
    ----------
    dagmc_id : int
        ID of the DAGMC universe to get cell IDs from.

    Returns
    -------
    numpy.ndarray
        DAGMC cell IDs for the universe.

    """
    n = c_size_t()
    _dll.openmc_dagmc_universe_get_num_cells(universe_id, n)
    cell_ids = np.empty(n.value, dtype=np.int32)

    _dll.openmc_dagmc_universe_get_cell_ids(
        universe_id, cell_ids.ctypes.data_as(POINTER(c_int32)), n
    )
    return cell_ids


def dagmc_universe_cell_volumes(universe_id: int) -> dict[int, float | None]:
    """Return intrinsic cell volumes for a DAGMC universe in cm³.

    The infinite implicit-complement cell has a value of ``None``.
    """
    cell_ids = dagmc_universe_cell_ids(universe_id)
    n = c_size_t(len(cell_ids))
    volumes = np.empty(n.value, dtype=np.float64)
    _dll.openmc_dagmc_universe_get_cell_volumes(
        universe_id, volumes.ctypes.data_as(POINTER(c_double)), n)
    return {
        int(cell_id): None if np.isnan(volume) else float(volume)
        for cell_id, volume in zip(cell_ids, volumes)
    }
