from typing import List, Literal, Optional, TypedDict

from care.abdm.models import AbhaNumber
from care.facility.models import PatientConsultation


class TokenGenerateTokenBody(TypedDict):
    abha_number: AbhaNumber
    purpose: Optional[Literal["LINK_CARECONTEXT"]]
    consultations: Optional[List[str]]


class TokenGenerateTokenResponse(TypedDict):
    pass


class LinkCarecontextBody(TypedDict):
    link_token: str | None
    consultations: List[PatientConsultation]


class LinkCarecontextResponse(TypedDict):
    pass
