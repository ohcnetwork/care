from typing import Any, Dict

from care.abdm.service.helper import ABDMAPIException, encrypt_message, timestamp, uuid
from care.abdm.service.request import Request
from care.abdm.service.v3.types.health_id import (
    EnrollmentAuthByAbdmBody,
    EnrollmentAuthByAbdmResponse,
    EnrollmentEnrolAbhaAddressBody,
    EnrollmentEnrolAbhaAddressResponse,
    EnrollmentEnrolByAadhaarBody,
    EnrollmentEnrolByAadhaarResponse,
    EnrollmentEnrolSuggestionBody,
    EnrollmentEnrolSuggestionResponse,
    EnrollmentRequestOtpBody,
    EnrollmentRequestOtpResponse,
    PhrWebLoginAbhaRequestOtpBody,
    PhrWebLoginAbhaRequestOtpResponse,
    PhrWebLoginAbhaSearchBody,
    PhrWebLoginAbhaSearchResponse,
    PhrWebLoginAbhaVerifyBody,
    PhrWebLoginAbhaVerifyResponse,
    ProfileAccountBody,
    ProfileAccountResponse,
    ProfileLoginRequestOtpBody,
    ProfileLoginRequestOtpResponse,
    ProfileLoginVerifyBody,
    ProfileLoginVerifyResponse,
    ProfileLoginVerifyUserBody,
    ProfileLoginVerifyUserResponse,
)


class HealthIdService:
    request = Request("https://abhasbx.abdm.gov.in/abha/api/v3")

    @staticmethod
    def handle_error(error: Dict[str, Any] | str) -> str:
        if isinstance(error, str):
            return error

        # { error: { message: "error message" } }
        if "error" in error:
            return HealthIdService.handle_error(error["error"])

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
    def enrollment__request__otp(
        data: EnrollmentRequestOtpBody,
    ) -> EnrollmentRequestOtpResponse:
        payload = {
            "txnId": data.get("transaction_id", ""),
            "scope": data.get("scope", []),
            "loginHint": data.get("type", ""),
            "loginId": encrypt_message(data.get("value", "")),
            "otpSystem": {"aadhaar": "aadhaar", "mobile": "abdm", "": ""}[
                data.get("type", "")
            ],
        }

        path = "/enrollment/request/otp"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def enrollment__enrol__byAadhaar(
        data: EnrollmentEnrolByAadhaarBody,
    ) -> EnrollmentEnrolByAadhaarResponse:
        payload = {
            "authData": {
                "authMethods": ["otp"],
                "otp": {
                    "timeStamp": timestamp(),
                    "txnId": data.get("transaction_id", ""),
                    "otpValue": encrypt_message(data.get("otp", "")),
                    "mobile": data.get("mobile", ""),
                },
            },
            "consent": {"code": "abha-enrollment", "version": "1.4"},
        }

        path = "/enrollment/enrol/byAadhaar"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def enrollment__auth__byAbdm(
        data: EnrollmentAuthByAbdmBody,
    ) -> EnrollmentAuthByAbdmResponse:
        payload = {
            "scope": data.get("scope", []),
            "authData": {
                "authMethods": ["otp"],
                "otp": {
                    "timeStamp": timestamp(),
                    "txnId": data.get("transaction_id", ""),
                    "otpValue": encrypt_message(data.get("otp", "")),
                },
            },
        }

        path = "/enrollment/auth/byAbdm"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def enrollment__enrol__suggestion(
        data: EnrollmentEnrolSuggestionBody,
    ) -> EnrollmentEnrolSuggestionResponse:
        path = "/enrollment/enrol/suggestion"
        response = HealthIdService.request.get(
            path,
            headers={
                "TRANSACTION_ID": data.get("transaction_id"),
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def enrollment__enrol__abha_address(
        data: EnrollmentEnrolAbhaAddressBody,
    ) -> EnrollmentEnrolAbhaAddressResponse:
        payload = {
            "txnId": data.get("transaction_id", ""),
            "abhaAddress": data.get("abha_address", ""),
            "preferred": data.get("preferred", 1),
        }

        path = "/enrollment/enrol/abha-address"
        response = HealthIdService.request.post(
            path, payload, headers={"REQUEST-ID": uuid(), "TIMESTAMP": timestamp()}
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def profile__login__request__otp(
        data: ProfileLoginRequestOtpBody,
    ) -> ProfileLoginRequestOtpResponse:
        payload = {
            "scope": data.get("scope", []),
            "loginHint": data.get("type", ""),
            "loginId": encrypt_message(data.get("value", "")),
            "otpSystem": data.get("otp_system", ""),
        }

        path = "/profile/login/request/otp"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def profile__login__verify(
        data: ProfileLoginVerifyBody,
    ) -> ProfileLoginVerifyResponse:
        payload = {
            "scope": data.get("scope", []),
            "authData": {
                "authMethods": ["otp"],
                "otp": {
                    "txnId": data.get("transaction_id", ""),
                    "otpValue": encrypt_message(data.get("otp", "")),
                },
            },
        }

        path = "/profile/login/verify"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def phr__web__login__abha__request__otp(
        data: PhrWebLoginAbhaRequestOtpBody,
    ) -> PhrWebLoginAbhaRequestOtpResponse:
        payload = {
            "scope": data.get("scope", []),
            "loginHint": data.get("type", ""),
            "loginId": encrypt_message(data.get("value", "")),
            "otpSystem": data.get("otp_system", ""),
        }

        path = "/phr/web/login/abha/request/otp"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def phr__web__login__abha__verify(
        data: PhrWebLoginAbhaVerifyBody,
    ) -> PhrWebLoginAbhaVerifyResponse:
        payload = {
            "scope": data.get("scope", []),
            "authData": {
                "authMethods": ["otp"],
                "otp": {
                    "txnId": data.get("transaction_id", ""),
                    "otpValue": encrypt_message(data.get("otp", "")),
                },
            },
        }

        path = "/phr/web/login/abha/verify"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def phr__web__login__abha__search(
        data: PhrWebLoginAbhaSearchBody,
    ) -> PhrWebLoginAbhaSearchResponse:
        payload = {
            "abhaAddress": data.get("abha_address", ""),
        }

        path = "/phr/web/login/abha/search"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def profile__login__verify__user(
        data: ProfileLoginVerifyUserBody,
    ) -> ProfileLoginVerifyUserResponse:
        payload = {
            "ABHANumber": data.get("abha_number", ""),
            "txnId": data.get("transaction_id", ""),
        }

        path = "/profile/login/verify/user"
        response = HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "T-TOKEN": f"Bearer {data.get('t_token', '')}",
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()

    @staticmethod
    def profile__account(data: ProfileAccountBody) -> ProfileAccountResponse:
        path = "/profile/account"
        response = HealthIdService.request.get(
            path,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-TOKEN": f"Bearer {data.get('x_token', '')}",
            },
        )

        if response.status_code != 200:
            raise ABDMAPIException(detail=HealthIdService.handle_error(response.json()))

        return response.json()
