from typing import List, Literal, Optional, TypedDict

from care.abdm.models import AbhaNumber, ConsentArtefact
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


class ConsentRequestHipOnNotifyBody(TypedDict):
    consent_id: str
    request_id: str


class ConsentRequestHipOnNotifyResponse(TypedDict):
    pass


class DataFlowHealthInformationHipOnRequestBody(TypedDict):
    transaction_id: str
    request_id: str


class DataFlowHealthInformationHipOnRequestResponse(TypedDict):
    pass


class DataFlowHealthInformationTransferBody(TypedDict):
    url: str
    consultations: List[PatientConsultation]
    consent: ConsentArtefact
    transaction_id: str
    key_material__crypto_algorithm: str
    key_material__curve: str
    key_material__public_key: str
    key_material__nonce: str


class DataFlowHealthInformationTransferResponse(TypedDict):
    pass


class DataFlowHealthInformationNotifyBody(TypedDict):
    transaction_id: str
    consent_id: str
    notifier__type: Literal["HIP", "HIU"]
    notifier__id: str
    status: Literal["TRANSFERRED", "FAILED"]
    hip_id: str
    consultations: List[PatientConsultation]


class DataFlowHealthInformationNotifyResponse(TypedDict):
    pass
