"""
openmc.deplete
==============

A depletion front-end tool.
"""

from importlib import import_module as _import_module

from .nuclide import *
from .chain import *
from .reaction_rates import *
from .atom_number import *
from .stepresult import *
from .results import *
from .transfer_rates import *

_LAZY_ATTRS = {
    # Transport operators
    'OpenMCOperator': 'openmc_operator',
    'CoupledOperator': 'coupled_operator',
    'Operator': 'coupled_operator',
    'IndependentOperator': 'independent_operator',

    # Transport-coupled depletion helpers
    'MicroXS': 'microxs',
    'get_microxs_and_flux': 'microxs',
    'write_microxs_hdf5': 'microxs',
    'read_microxs_hdf5': 'microxs',
    'TalliedFissionYieldHelper': 'helpers',
    'DirectReactionRateHelper': 'helpers',
    'FluxCollapseHelper': 'helpers',
    'EnergyNormalizationHelper': 'helpers',
    'ChainFissionHelper': 'helpers',
    'EnergyScoreHelper': 'helpers',
    'SourceRateHelper': 'helpers',
    'ConstantFissionYieldHelper': 'helpers',
    'FissionYieldCutoffHelper': 'helpers',
    'AveragedFissionYieldHelper': 'helpers',
    'R2SManager': 'r2s',
    'get_activation_materials': 'r2s',

    # Abstract base classes and integrators
    'OperatorResult': 'abc',
    'TransportOperator': 'abc',
    'ReactionRateHelper': 'abc',
    'NormalizationHelper': 'abc',
    'FissionYieldHelper': 'abc',
    'Integrator': 'abc',
    'SIIntegrator': 'abc',
    'DepSystemSolver': 'abc',
    'PredictorIntegrator': 'integrators',
    'CECMIntegrator': 'integrators',
    'CF4Integrator': 'integrators',
    'CELIIntegrator': 'integrators',
    'EPCRK4Integrator': 'integrators',
    'LEQIIntegrator': 'integrators',
    'SICELIIntegrator': 'integrators',
    'SILEQIIntegrator': 'integrators',
}

_LAZY_MODULES = {'abc', 'cram', 'helpers'}


def __getattr__(name):
    if name in _LAZY_MODULES:
        module = _import_module(f'.{name}', __name__)
        globals()[name] = module
        return module

    if name in _LAZY_ATTRS:
        module = _import_module(f'.{_LAZY_ATTRS[name]}', __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    name for name in globals()
    if not name.startswith('_')
]
__all__ += list(_LAZY_ATTRS) + list(_LAZY_MODULES)
