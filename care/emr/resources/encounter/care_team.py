from pydantic import UUID4, BaseModel

from care.emr.resources.encounter.valueset import PRACTITIONER_ROLE_VALUESET
from care.emr.utils.valueset_coding_type import ValueSetBoundCoding


class EncounterCareTeamMemberSpec(BaseModel):
    user_id: UUID4
    role: ValueSetBoundCoding[PRACTITIONER_ROLE_VALUESET.slug]
