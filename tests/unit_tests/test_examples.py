import openmc
import openmc.examples
from openmc.utility_funcs import change_directory


def _tally_by_name(model, name):
    for tally in model.tallies:
        if tally.name == name:
            return tally
    raise AssertionError(f'Tally {name!r} not found')


def test_reaction_tally_model(tmp_path):
    with change_directory(tmp_path):
        model = openmc.examples.reaction_tally_model()

        assert isinstance(model, openmc.Model)
        assert len(model.materials) == 2
        assert len(model.tallies) == 5
        assert model.settings.run_mode == 'fixed source'

        production = _tally_by_name(model, 'reaction-neutron-production')
        assert isinstance(production.filters[0], openmc.ReactionFilter)
        assert isinstance(production.filters[1], openmc.ParticleProductionFilter)
        assert production.scores == ['events']

        damage = _tally_by_name(model, 'reaction-damage-energy')
        assert isinstance(damage.filters[0], openmc.ReactionFilter)
        assert isinstance(damage.filters[1], openmc.MaterialFilter)
        assert damage.scores == ['damage-energy']

        heating = _tally_by_name(model, 'reaction-heating')
        assert isinstance(heating.filters[0], openmc.ReactionFilter)
        assert isinstance(heating.filters[1], openmc.MaterialFilter)
        assert heating.scores == ['heating']

        energy = _tally_by_name(model, 'reaction-energy')
        assert isinstance(energy.filters[0], openmc.ReactionFilter)
        assert isinstance(energy.filters[1], openmc.EnergyFilter)

        material = _tally_by_name(model, 'reaction-material')
        assert isinstance(material.filters[0], openmc.ReactionFilter)
        assert isinstance(material.filters[1], openmc.MaterialFilter)

        model.export_to_xml()
