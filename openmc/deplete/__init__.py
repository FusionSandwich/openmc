"""
openmc.deplete
==============

A depletion front-end tool.
"""

from .nuclide import *
from .chain import *
from . import abc
from . import cram

try:
    from . import helpers
    from .openmc_operator import *
    from .coupled_operator import *
    from .independent_operator import *
    from .microxs import *
    from .reaction_rates import *
    from .atom_number import *
    from .stepresult import *
    from .results import *
    from .integrators import *
    from .transfer_rates import *
    from .r2s import *
except OSError:
    # Chain-only helpers are useful in Python environments that cannot load the
    # compiled OpenMC library, such as a Windows venv next to a Docker build.
    pass
