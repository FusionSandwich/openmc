"""Manual native-OpenMC API example with stable finite-member identities.

Default: export a tiny two-sphere analytic CSG model, never run transport.
No spline payload is generated. Replacing the surfaces with individually
bound SweptSplineSurface objects is shown in make_swept_reference_members;
that path assumes separately admitted, disjoint coefficient payloads.
Neither path demonstrates WISTELL winding-pack fidelity or qualification.
"""
from __future__ import annotations

import argparse
from pathlib import Path


BINDINGS = (
    dict(member_id=7, surface_id=301, cell_id=201, material_id=101),
    dict(member_id=42, surface_id=302, cell_id=202, material_id=102),
)


def _assemble(surfaces):
    import openmc

    materials, members = [], []
    for binding, surface in zip(BINDINGS, surfaces, strict=True):
        material = openmc.Material(material_id=binding['material_id'],
                                   name=f"synthetic material {binding['member_id']}")
        material.add_nuclide('H1', 1.0)
        material.set_density('atom/b-cm', 1.0e-6)  # Diagnostic assumption only.
        materials.append(material)
        members.append(openmc.Cell(cell_id=binding['cell_id'], fill=material,
                                   region=-surface,
                                   name=f"finite member {binding['member_id']}"))
    # Ancestor cell provides an independent one-bin union tally. Child cells
    # provide member bins. CellFilter checks every coordinate level; do not put
    # ancestor and child IDs together in a tally then sum all bins.
    union = openmc.Cell(cell_id=500, name='union of finite members',
                       region=(-surfaces[0] | -surfaces[1]),
                       fill=openmc.Universe(universe_id=600, cells=members))
    boundary = openmc.Sphere(surface_id=399, x0=2.0, r=10.0,
                             boundary_type='vacuum')
    surroundings = openmc.Cell(cell_id=203, region=-boundary & ~union.region)
    geometry = openmc.Geometry([union, surroundings])
    by_member = openmc.Tally(tally_id=701, name='member tracklength')
    by_member.filters = [openmc.CellFilter(members)]
    by_member.scores = ['flux']
    by_member.estimator = 'tracklength'
    total = openmc.Tally(tally_id=702, name='union tracklength')
    total.filters = [openmc.CellFilter([union])]
    total.scores = ['flux']
    total.estimator = 'tracklength'
    settings = openmc.Settings()
    settings.run_mode = 'fixed source'
    settings.particles = 32
    settings.batches = 2
    settings.seed = 314159
    settings.source = [
        openmc.IndependentSource(space=openmc.stats.Point((0, 0, 0)),
                                 energy=openmc.stats.Discrete([14e6], [1]),
                                 strength=0.5),
        openmc.IndependentSource(space=openmc.stats.Point((4, 0, 0)),
                                 energy=openmc.stats.Discrete([14e6], [1]),
                                 strength=0.5),
    ]
    return openmc.Model(geometry=geometry, materials=openmc.Materials(materials),
                        settings=settings, tallies=openmc.Tallies([by_member, total]))


def make_analytic_model():
    import openmc
    surfaces = [openmc.Sphere(surface_id=301, x0=0, r=1),
                openmc.Sphere(surface_id=302, x0=4, r=1)]
    return _assemble(surfaces)


def make_swept_reference_members(data_file, payloads, materials):
    """Bind admitted payloads to explicit cells without inventing an assembly.

    payloads maps stable keys 7 and 42 to {'dataset': ..., 'content_id': ...}.
    materials maps the same keys to caller-supplied Material objects with IDs
    101 and 102 respectively. The caller owns nonoverlap/admission, outer
    boundaries, source support and transport eligibility. This function only
    returns the two member cells; it never clips arbitrary coils into a toy box.
    """
    import openmc
    expected = {binding['member_id'] for binding in BINDINGS}
    if set(payloads) != expected or set(materials) != expected:
        raise ValueError('Explicit payloads and materials for member IDs 7 and 42 required')
    members = {}
    for binding in BINDINGS:
        member_id = binding['member_id']
        material = materials[member_id]
        if material.id != binding['material_id']:
            raise ValueError('Material identity does not match the member manifest')
        surface = openmc.SweptSplineSurface(
            data_file=Path(data_file), dataset=payloads[member_id]['dataset'],
            content_id=payloads[member_id]['content_id'],
            surface_id=binding['surface_id'], name=f'member {member_id}')
        members[member_id] = openmc.Cell(
            cell_id=binding['cell_id'], fill=material, region=-surface,
            name=f'finite member {member_id}')
    return members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    model = make_analytic_model()
    model.export_to_xml(directory=args.output)
    print(f'Exported analytic API fixture only: {args.output}; transport NOT_RUN')


if __name__ == '__main__':
    main()
