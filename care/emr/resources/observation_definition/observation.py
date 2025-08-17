from care.emr.models.observation import Observation
from care.emr.resources.observation.spec import ObservationStatus


def convert_od_to_observation(observation_definition, encounter):
    return Observation(
        status=ObservationStatus.final.value,
        encounter=encounter,
        category=observation_definition.category,
        main_code=observation_definition.code,
    )
