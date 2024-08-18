from typing import List, Literal, Optional, TypedDict

from care.abdm.models import AbhaNumber, ConsentArtefact, ConsentRequest
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


class UserInitiatedLinkingLinkCareContextOnInitBody(TypedDict):
    transaction_id: str
    request_id: str
    reference_id: str


class UserInitiatedLinkingLinkCareContextOnInitResponse(TypedDict):
    pass


class UserInitiatedLinkingLinkCareContextOnConfirmBody(TypedDict):
    request_id: str
    consultations: List[PatientConsultation]


class UserInitiatedLinkingLinkCareContextOnConfirmResponse(TypedDict):
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
    consultation_ids: List[str]


class DataFlowHealthInformationNotifyResponse(TypedDict):
    pass


class IdentityAuthenticationBody(TypedDict):
    abha_number: AbhaNumber


class Response(TypedDict):
    requestId: str


class IdentityAuthenticationResponse(TypedDict):
    authenticated: bool
    transactionId: str
    abhaAddress: str
    response: Response


class ConsentRequestInitBody(TypedDict):
    consent: ConsentRequest


class ConsentRequestInitResponse(TypedDict):
    pass


class ConsentRequestStatusBody(TypedDict):
    consent: ConsentRequest


class ConsentRequestStatusResponse(TypedDict):
    pass


class ConsentRequestHiuOnNotifyBody(TypedDict):
    consent: ConsentRequest
    request_id: str


class ConsentRequestHiuOnNotifyResponse(TypedDict):
    pass


class ConsentFetchBody(TypedDict):
    artefact: ConsentArtefact


class ConsentFetchResponse(TypedDict):
    pass


class DataFlowHealthInformationRequestBody(TypedDict):
    artefact: ConsentArtefact


class DataFlowHealthInformationRequestResponse(TypedDict):
    pass
