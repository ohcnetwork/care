import json
from datetime import datetime, timedelta
from typing import Any, Dict

import requests
from django.core.cache import cache

from care.abdm.service.helper import (
    ABDMAPIException,
    cm_id,
    hip_id_from_abha_number,
    timestamp,
    uuid,
)
from care.abdm.service.request import Request
from care.abdm.service.v3.types.gateway import (
    ConsentRequestHipOnNotifyBody,
    ConsentRequestHipOnNotifyResponse,
    DataFlowHealthInformationHipOnRequestBody,
    DataFlowHealthInformationHipOnRequestResponse,
    DataFlowHealthInformationNotifyBody,
    DataFlowHealthInformationNotifyResponse,
    DataFlowHealthInformationTransferBody,
    DataFlowHealthInformationTransferResponse,
    LinkCarecontextBody,
    LinkCarecontextResponse,
    TokenGenerateTokenBody,
    TokenGenerateTokenResponse,
    UserInitiatedLinkingPatientCareContextOnConfirmBody,
    UserInitiatedLinkingPatientCareContextOnConfirmResponse,
    UserInitiatedLinkingPatientCareContextOnDiscoverBody,
    UserInitiatedLinkingPatientCareContextOnDiscoverResponse,
    UserInitiatedLinkingPatientCareContextOnInitBody,
    UserInitiatedLinkingPatientCareContextOnInitResponse,
)
from care.abdm.utils.cipher import Cipher
from care.abdm.utils.fhir import Fhir


class GatewayService:
    request = Request("https://dev.abdm.gov.in/hiecm/api/v3")

    @staticmethod
    def handle_error(error: Dict[str, Any] | str) -> str:
        if isinstance(error, str):
            return error

        # { error: { message: "error message" } }
        if "error" in error:
            return GatewayService.handle_error(error["error"])

        # { message: "error message" }
        if "message" in error:
            return error["message"]

        # { field_name: "error message" }
        if len(error) == 1:
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
                "X-HIP-ID": hip_id_from_abha_number(abha_number.abha_number),
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
                "X-HIP-ID": hip_id_from_abha_number(abha_number.abha_number),
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

            payload["patient"] = {
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
    def user_initiated_linking__patient__care_context__on_init(
        data: UserInitiatedLinkingPatientCareContextOnInitBody,
    ) -> UserInitiatedLinkingPatientCareContextOnInitResponse:
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
                    ).isoformat(),
                },
            },
            "response": {
                "requestId": data.get("request_id"),
            },
        }

        path = "/user-initiated-linking/patient/care-context/on-init"
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
    def user_initiated_linking__patient__care_context__on_confirm(
        data: UserInitiatedLinkingPatientCareContextOnConfirmBody,
    ) -> UserInitiatedLinkingPatientCareContextOnConfirmResponse:
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

            payload["patient"] = {
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

        path = "/user-initiated-linking/patient/care-context/on-confirm"
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
            "hiRequest": [
                {
                    "transactionId": data.get("transaction_id"),
                    "sessionStatus": "ACKNOWLEDGED",
                }
            ],
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
                    "expiry": (datetime.now() + timedelta(days=2)).isoformat(),
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
        consultations = data.get("consultations", [])

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
                                "careContextReference": str(x.external_id),
                                "hiStatus": (
                                    "DELIVERED"
                                    if data.get("status") == "TRANSFERRED"
                                    else "FAILED"
                                ),
                                "description": data.get("status"),
                            },
                            consultations,
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
