from care.emr.models.specimen import Specimen
from care.emr.resources.specimen.spec import SpecimenStatusOptions


def convert_sd_to_specimen(specimen_definition):
    return Specimen(
        status=SpecimenStatusOptions.available.value,
        specimen_type=specimen_definition.type_collected,
        specimen_definition=specimen_definition,
    )
