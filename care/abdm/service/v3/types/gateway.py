from typing import List, Literal, Optional, TypedDict

from care.abdm.models import AbhaNumber
from care.facility.models import PatientConsultation, PatientRegistration


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


class UserInitiatedLinkingPatientCareContextOnDiscoverBody(TypedDict):
    transaction_id: str
    request_id: str
    patient: PatientRegistration
    matched_by: List[Literal["MOBILE", "ABHA_NUMBER", "MR"]]


class UserInitiatedLinkingPatientCareContextOnDiscoverResponse(TypedDict):
    pass


class UserInitiatedLinkingPatientCareContextOnInitBody(TypedDict):
    transaction_id: str
    request_id: str
    reference_id: str


class UserInitiatedLinkingPatientCareContextOnInitResponse(TypedDict):
    pass


class UserInitiatedLinkingPatientCareContextOnConfirmBody(TypedDict):
    transaction_id: str
    request_id: str
    patient: PatientRegistration


class UserInitiatedLinkingPatientCareContextOnConfirmResponse(TypedDict):
    pass
