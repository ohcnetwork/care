import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import requests
from django.conf import settings
from django.core.cache import cache

from care.abdm.models.base import Purpose
from care.abdm.service.helper import (
    ABDMAPIException,
    cm_id,
    hf_id_from_abha_id,
    timestamp,
    uuid,
)
from care.abdm.service.request import Request
from care.abdm.service.v3.types.gateway import (
    ConsentFetchBody,
    ConsentFetchResponse,
    ConsentRequestHipOnNotifyBody,
    ConsentRequestHipOnNotifyResponse,
    ConsentRequestHiuOnNotifyBody,
    ConsentRequestHiuOnNotifyResponse,
    ConsentRequestInitBody,
    ConsentRequestInitResponse,
    ConsentRequestStatusBody,
    ConsentRequestStatusResponse,
    DataFlowHealthInformationHipOnRequestBody,
    DataFlowHealthInformationHipOnRequestResponse,
    DataFlowHealthInformationNotifyBody,
    DataFlowHealthInformationNotifyResponse,
    DataFlowHealthInformationRequestBody,
    DataFlowHealthInformationRequestResponse,
    DataFlowHealthInformationTransferBody,
    DataFlowHealthInformationTransferResponse,
    IdentityAuthenticationBody,
    IdentityAuthenticationResponse,
    LinkCarecontextBody,
    LinkCarecontextResponse,
    TokenGenerateTokenBody,
    TokenGenerateTokenResponse,
    UserInitiatedLinkingLinkCareContextOnConfirmBody,
    UserInitiatedLinkingLinkCareContextOnConfirmResponse,
    UserInitiatedLinkingLinkCareContextOnInitBody,
    UserInitiatedLinkingLinkCareContextOnInitResponse,
    UserInitiatedLinkingPatientCareContextOnDiscoverBody,
    UserInitiatedLinkingPatientCareContextOnDiscoverResponse,
)
from care.abdm.utils.cipher import Cipher
from care.abdm.utils.fhir import Fhir


class GatewayService:
    request = Request("https://dev.abdm.gov.in/hiecm/api/v3")

    @staticmethod
    def handle_error(error: Dict[str, Any] | str) -> str:
        if isinstance(error, list):
            return GatewayService.handle_error(error[0])

        if isinstance(error, str):
            return error

        # { error: { message: "error message" } }
        if "error" in error:
            return GatewayService.handle_error(error["error"])

        # { message: "error message" }
        if "message" in error:
            return error["message"]

        # { field_name: "error message" }
        if isinstance(error, dict) and len(error) == 1:
            error.pop("code")
            error.pop("timestamp")
            return "".join(list(map(lambda x: str(x), list(error.values()))))

        return "Unknown error occurred at ABDM's end while processing the request. Please try again later."

    @staticmethod
    def token__generate_token(
        data: TokenGenerateTokenBody,
    ) -> TokenGenerateTokenResponse:
        abha_number = data.get("abha_number")

        if not abha_number:
            raise ABDMAPIException(detail="Provide an ABHA number to generate token")

        payload = {
            "abhaNumber": abha_number.abha_number.replace("-", ""),
            "abhaAddress": abha_number.health_id,
            "name": abha_number.name,
            "gender": abha_number.gender,
            "yearOfBirth": datetime.strptime(
                abha_number.date_of_birth, "%Y-%m-%d"
            ).year,
        }

        request_id = uuid()
        cache.set(
            "abdm_link_token__" + request_id,
            {
                "abha_number": abha_number.abha_number,
                "purpose": data.get("purpose"),
                "consultations": data.get("consultations"),
            },
            timeout=60 * 5,
        )

        path = "/token/generate-token"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": request_id,
                "TIMESTAMP": timestamp(),
                "X-HIP-ID": hf_id_from_abha_id(abha_number.abha_number),
                "X-CM-ID": cm_id(),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def link__carecontext(data: LinkCarecontextBody) -> LinkCarecontextResponse:
        consultations = data.get("consultations")

        if not consultations or len(consultations) == 0:
            raise ABDMAPIException(detail="Provide at least one consultation to link")

        patient = consultations[0].patient
        abha_number = patient.abha_number

        if not abha_number:
            raise ABDMAPIException(
                detail="Failed to link consultation, Patient does not have an ABHA number"
            )

        if not data.get("link_token"):
            GatewayService.token__generate_token(
                {
                    "abha_number": abha_number,
                    "purpose": "LINK_CARECONTEXT",
                    "consultations": list(
                        map(lambda x: str(x.external_id), consultations)
                    ),
                }
            )
            return {}

        payload = {
            "abhaNumber": abha_number.abha_number.replace("-", ""),
            "abhaAddress": abha_number.health_id,
            "patient": [
                {
                    "referenceNumber": str(patient.external_id),
                    "display": patient.name,
                    "careContexts": list(
                        map(
                            lambda x: {
                                "referenceNumber": str(x.external_id),
                                "display": f"Encounter on {str(x.created_date.date())}",
                            },
                            consultations,
                        )
                    ),
                    "hiType": "DischargeSummary",
                    "count": len(consultations),
                }
            ],
        }

        path = "/link/carecontext"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
                "X-HIP-ID": hf_id_from_abha_id(abha_number.abha_number),
                "X-LINK-TOKEN": data.get("link_token"),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def user_initiated_linking__patient__care_context__on_discover(
        data: UserInitiatedLinkingPatientCareContextOnDiscoverBody,
    ) -> UserInitiatedLinkingPatientCareContextOnDiscoverResponse:
        payload: Dict = {
            "transactionId": data.get("transaction_id"),
            "response": {
                "requestId": data.get("request_id"),
            },
        }

        patient = data.get("patient")
        if patient:
            consultations = []

            if hasattr(patient, "consultations"):
                consultations = patient.consultations.all()

            payload["patient"] = [
                {
                    "referenceNumber": str(patient.external_id),
                    "display": patient.name,
                    "careContexts": list(
                        map(
                            lambda x: {
                                "referenceNumber": str(x.external_id),
                                "display": f"Encounter on {str(x.created_date.date())}",
                            },
                            consultations,
                        )
                    ),
                    "hiType": "DischargeSummary",
                    "count": len(consultations),
                }
            ]
            payload["matchedBy"] = data.get("matched_by", [])
        else:
            payload["error"] = {
                "code": "ABDM-1010",
                "message": "Patient not found",
            }

        path = "/user-initiated-linking/patient/care-context/on-discover"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def user_initiated_linking__link__care_context__on_init(
        data: UserInitiatedLinkingLinkCareContextOnInitBody,
    ) -> UserInitiatedLinkingLinkCareContextOnInitResponse:
        payload = {
            "transactionId": data.get("transaction_id"),
            "link": {
                "referenceNumber": data.get("reference_id"),
                "authenticationType": "DIRECT",
                "meta": {
                    "communicationMedium": "MOBILE",
                    "communicationHint": "OTP",
                    "communicationExpiry": (
                        datetime.now() + timedelta(minutes=5)
                    ).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                },
            },
            "response": {
                "requestId": data.get("request_id"),
            },
        }

        path = "/user-initiated-linking/link/care-context/on-init"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def user_initiated_linking__link__care_context__on_confirm(
        data: UserInitiatedLinkingLinkCareContextOnConfirmBody,
    ) -> UserInitiatedLinkingLinkCareContextOnConfirmResponse:
        payload: Dict = {
            "response": {
                "requestId": data.get("request_id"),
            },
        }

        consultations = data.get("consultations", [])
        if len(consultations) > 0:
            patient = consultations[0].patient
            payload["patient"] = [
                {
                    "referenceNumber": str(patient.external_id),
                    "display": patient.name,
                    "careContexts": list(
                        map(
                            lambda x: {
                                "referenceNumber": str(x.external_id),
                                "display": f"Encounter on {str(x.created_date.date())}",
                            },
                            consultations,
                        )
                    ),
                    "hiType": "DischargeSummary",
                    "count": len(consultations),
                }
            ]

        path = "/user-initiated-linking/link/care-context/on-confirm"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def consent__request__hip__on_notify(
        data: ConsentRequestHipOnNotifyBody,
    ) -> ConsentRequestHipOnNotifyResponse:
        payload = {
            "acknowledgement": {
                "status": "ok",
                "consentId": data.get("consent_id"),
            },
            "response": {"requestId": data.get("request_id")},
        }

        path = "/consent/request/hip/on-notify"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def data_flow__health_information__hip__on_request(
        data: DataFlowHealthInformationHipOnRequestBody,
    ) -> DataFlowHealthInformationHipOnRequestResponse:
        payload = {
            "hiRequest": {
                "transactionId": data.get("transaction_id"),
                "sessionStatus": "ACKNOWLEDGED",
            },
            "response": {"requestId": data.get("request_id")},
        }

        path = "/data-flow/health-information/hip/on-request"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def data_flow__health_information__transfer(
        data: DataFlowHealthInformationTransferBody,
    ) -> DataFlowHealthInformationTransferResponse:
        consultations = data.get("consultations", [])
        consent = data.get("consent")

        cipher = Cipher(
            external_public_key=data.get("key_material__public_key"),
            external_nonce=data.get("key_material__nonce"),
        )

        entries = []
        for consultation in consultations:
            if consent:
                for hi_type in consent.hi_types:
                    fhir_data = Fhir(consultation=consultation).create_record(hi_type)

                    encrypted_data = cipher.encrypt(fhir_data)["data"]

                    entry = {
                        "content": encrypted_data,
                        "media": "application/fhir+json",
                        "checksum": "",  # TODO: look into generating checksum
                        "careContextReference": str(consultation.external_id),
                    }
                    entries.append(entry)

        payload = {
            "pageNumber": 1,
            "pageCount": 1,
            "transactionId": data.get("transaction_id"),
            "entries": entries,
            "keyMaterial": {
                "cryptoAlg": data.get("key_material__crypto_algorithm"),
                "curve": data.get("key_material__curve"),
                "dhPublicKey": {
                    "expiry": (datetime.now() + timedelta(days=2)).strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z"
                    ),
                    "parameters": "Curve25519/32byte random key",
                    "keyValue": cipher.key_to_share,
                },
                "nonce": cipher.internal_nonce,
            },
        }

        auth_header = Request("").auth_header()
        headers = {
            "Content-Type": "application/json",
            **auth_header,
        }

        path = data.get("url", "")
        response = requests.post(
            path,
            json=json.dumps(payload),
            headers=headers,
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def data_flow__health_information__notify(
        data: DataFlowHealthInformationNotifyBody,
    ) -> DataFlowHealthInformationNotifyResponse:
        consultation_ids = data.get("consultation_ids", [])

        payload = {
            "notification": {
                "consentId": data.get("consent_id"),
                "transactionId": data.get("transaction_id"),
                "doneAt": timestamp(),
                "notifier": {
                    "type": data.get("notifier__type"),
                    "id": data.get("notifier__id"),
                },
                "statusNotification": {
                    "sessionStatus": data.get("status"),
                    "hipId": data.get("hip_id"),
                    "statusResponses": list(
                        map(
                            lambda x: {
                                "careContextReference": x,
                                "hiStatus": (
                                    "DELIVERED"
                                    if data.get("status") == "TRANSFERRED"
                                    else "FAILED"
                                ),
                                "description": data.get("status"),
                            },
                            consultation_ids,
                        )
                    ),
                },
            }
        }

        path = "/data-flow/health-information/notify"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def identity__authentication(
        data: IdentityAuthenticationBody,
    ) -> IdentityAuthenticationResponse:
        abha_number = data.get("abha_number")

        if not abha_number:
            raise ABDMAPIException(detail="Provide an ABHA number to authenticate")

        payload = {
            "scope": "DEMO",
            "parameters": {
                "abhaNumber": abha_number.abha_number.replace("-", ""),
                "abhaAddress": abha_number.health_id,
                "name": abha_number.name,
                "gender": abha_number.gender,
                "yearOfBirth": datetime.strptime(
                    abha_number.date_of_birth, "%Y-%m-%d"
                ).year,
            },
        }

        path = "/identity/authentication"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
                "REQUESTER-ID": hf_id_from_abha_id(abha_number.abha_number),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def consent__request__init(
        data: ConsentRequestInitBody,
    ) -> ConsentRequestInitResponse:
        consent = data.get("consent")

        if not consent:
            raise ABDMAPIException(detail="Provide a consent to initiate")

        hiu_id = hf_id_from_abha_id(consent.patient_abha.health_id)

        payload = {
            "consent": {
                "purpose": {
                    "text": Purpose(consent.purpose).label,
                    "code": Purpose(consent.purpose).value,
                    "refUri": "http://terminology.hl7.org/ValueSet/v3-PurposeOfUse",
                },
                "patient": {"id": consent.patient_abha.health_id},
                "hiu": {"id": hiu_id},
                "requester": {
                    "name": f"{consent.requester.REVERSE_TYPE_MAP[consent.requester.user_type]}, {consent.requester.first_name} {consent.requester.last_name}",
                    "identifier": {
                        "type": "CARE Username",
                        "value": consent.requester.username,
                        "system": settings.CURRENT_DOMAIN,
                    },
                },
                "hiTypes": consent.hi_types,
                "permission": {
                    "accessMode": consent.access_mode,
                    "dateRange": {
                        "from": consent.from_time.astimezone(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%S.000Z"
                        ),
                        "to": consent.to_time.astimezone(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%S.000Z"
                        ),
                    },
                    "dataEraseAt": consent.expiry.astimezone(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S.000Z"
                    ),
                    "frequency": {
                        "unit": consent.frequency_unit,
                        "value": consent.frequency_value,
                        "repeats": consent.frequency_repeats,
                    },
                },
            },
        }

        path = "/consent/request/init"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": str(consent.external_id),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
                "X-HIU-ID": hiu_id,
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def consent__request__status(
        data: ConsentRequestStatusBody,
    ) -> ConsentRequestStatusResponse:
        consent = data.get("consent")

        if not consent:
            raise ABDMAPIException(detail="Provide a consent to check status")

        payload = {
            "consentRequestId": str(consent.consent_id),
        }

        response = GatewayService.request.post(
            "/consent/request/status",
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
                "X-HIU-ID": hf_id_from_abha_id(consent.patient_abha.health_id),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def consent__request__hiu__on_notify(
        data: ConsentRequestHiuOnNotifyBody,
    ) -> ConsentRequestHiuOnNotifyResponse:
        consent = data.get("consent")

        if not consent:
            raise ABDMAPIException(detail="Provide a consent to notify")

        payload = {
            "acknowledgement": list(
                map(
                    lambda x: {
                        "consentId": str(x.external_id),
                        "status": "OK",
                    },
                    consent.consent_artefacts.all() or [],
                )
            ),
            "response": {"requestId": data.get("request_id")},
        }

        path = "/consent/request/hiu/on-notify"
        response = GatewayService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def consent__fetch(
        data: ConsentFetchBody,
    ) -> ConsentFetchResponse:
        artefact = data.get("artefact")

        if not artefact:
            raise ABDMAPIException(detail="Provide a consent to check status")

        payload = {
            "consentId": str(artefact.artefact_id),
        }

        response = GatewayService.request.post(
            "/consent/fetch",
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
                "X-HIU-ID": hf_id_from_abha_id(artefact.patient_abha.health_id),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}

    @staticmethod
    def data_flow__health_information__request(
        data: DataFlowHealthInformationRequestBody,
    ) -> DataFlowHealthInformationRequestResponse:
        artefact = data.get("artefact")

        if not artefact:
            raise ABDMAPIException(detail="Provide a consent artefact to request")

        request_id = uuid()
        artefact.consent_id = request_id
        artefact.save()

        payload = {
            "hiRequest": {
                "consent": {"id": str(artefact.artefact_id)},
                "dateRange": {
                    "from": artefact.from_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "to": artefact.to_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                },
                "dataPushUrl": settings.BACKEND_DOMAIN
                + "/api/v3/hiu/health-information/transfer",
                "keyMaterial": {
                    "cryptoAlg": artefact.key_material_algorithm,
                    "curve": artefact.key_material_curve,
                    "dhPublicKey": {
                        "expiry": artefact.expiry.astimezone(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%S.000Z"
                        ),
                        "parameters": f"{artefact.key_material_curve}/{artefact.key_material_algorithm}",
                        "keyValue": artefact.key_material_public_key,
                    },
                    "nonce": artefact.key_material_nonce,
                },
            },
        }

        response = GatewayService.request.post(
            "/data-flow/health-information/request",
            payload,
            headers={
                "REQUEST-ID": request_id,
                "TIMESTAMP": timestamp(),
                "X-CM-ID": cm_id(),
                "X-HIU-ID": hf_id_from_abha_id(artefact.patient_abha.health_id),
            },
        )

        if response.status_code != 202:
            raise ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}
