from datetime import datetime, timedelta
from typing import Any, Dict

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
            ABDMAPIException(detail=GatewayService.handle_error(response.json()))

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
            ABDMAPIException(detail=GatewayService.handle_error(response.json()))

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
            ABDMAPIException(detail=GatewayService.handle_error(response.json()))

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
            ABDMAPIException(detail=GatewayService.handle_error(response.json()))

        return {}
