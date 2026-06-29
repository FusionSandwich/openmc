"""Named groups of neutron reactions for use with reaction filters."""

from __future__ import annotations

from .data.reaction import REACTION_NAME


__all__ = ['REACTION_GROUPS', 'reaction_group']

_REACTION_GROUP_MTS = {
    'elastic': (2,),
    'discrete-inelastic': tuple(range(51, 91)),
    'continuum-inelastic': (91,),
    'inelastic': (4,) + tuple(range(51, 92)),
    'capture': (102,),
    'multi-neutron': (16, 17, 37) + tuple(range(875, 892)),
    'charged-particle': tuple(range(103, 108)) + tuple(range(600, 850)),
    'gas-production': tuple(range(103, 108)) + tuple(range(600, 850)),
}

_THRESHOLD_MTS = (
    tuple(range(16, 18)) + tuple(range(22, 46)) + tuple(range(101, 118)) +
    tuple(range(152, 201)) + tuple(range(875, 892))
)

_REACTION_GROUP_MTS['pka-relevant'] = (
    _REACTION_GROUP_MTS['elastic'] +
    _REACTION_GROUP_MTS['inelastic'] +
    _THRESHOLD_MTS +
    _REACTION_GROUP_MTS['charged-particle'] +
    _REACTION_GROUP_MTS['capture']
)

REACTION_GROUPS = tuple(_REACTION_GROUP_MTS)


def _normalize_group_name(name: str) -> str:
    return name.strip().lower().replace('_', '-').replace(' ', '-')


def _unique_known_mts(mts: tuple[int, ...]) -> tuple[int, ...]:
    seen = set()
    result = []
    for mt in mts:
        if mt in REACTION_NAME and mt not in seen:
            result.append(mt)
            seen.add(mt)
    return tuple(result)


def reaction_group(
    name: str, *, as_mts: bool = False
) -> tuple[str, ...] | tuple[int, ...]:
    """Return reactions belonging to a named reaction group.

    Parameters
    ----------
    name : str
        Reaction group name. Recognized names are ``'elastic'``,
        ``'discrete-inelastic'``, ``'continuum-inelastic'``, ``'inelastic'``,
        ``'capture'``, ``'multi-neutron'``, ``'charged-particle'``,
        ``'gas-production'``, and ``'pka-relevant'``. Underscores and spaces
        are accepted in place of hyphens.
    as_mts : bool, optional
        If true, return ENDF MT numbers rather than canonical reaction names.

    Returns
    -------
    tuple of str or tuple of int
        Reactions in the requested group, suitable for use as
        :class:`openmc.ReactionFilter` bins.

    Examples
    --------
    >>> openmc.ReactionFilter(openmc.reaction_group('gas-production'))
    ReactionFilter
        Bins            =   ['(n,p)' '(n,d)' '(n,t)' ...]

    """
    if not isinstance(name, str):
        raise TypeError('reaction group name must be a string')

    group_name = _normalize_group_name(name)
    if group_name not in _REACTION_GROUP_MTS:
        valid = ', '.join(REACTION_GROUPS)
        raise ValueError(
            f"Unknown reaction group '{name}'. Valid groups are: {valid}")

    mts = _unique_known_mts(_REACTION_GROUP_MTS[group_name])
    if as_mts:
        return mts
    return tuple(REACTION_NAME[mt] for mt in mts)
