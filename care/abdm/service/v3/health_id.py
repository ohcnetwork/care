from typing import List, Literal, Optional, TypedDict

from care.abdm.service.helper import encrypt_message, timestamp, uuid
from care.abdm.service.request import Request


class ABHAProfile(TypedDict):
    ABHANumber: str
    abhaStatus: Literal["ACTIVE"]
    abhaType: Literal["STANDARD"]
    address: str
    districtCode: str
    districtName: str
    dob: str
    firstName: str
    gender: Literal["M", "F", "O"]
    lastName: str
    middleName: str
    mobile: str
    photo: str
    phrAddress: List[str]
    pinCode: str
    stateCode: str
    stateName: str


class Tokens(TypedDict):
    expiresIn: int
    refreshExpiresIn: int
    refreshToken: str
    token: str


class Accounts(TypedDict):
    ABHANumber: str


class Error(TypedDict):
    message: str
    code: str


class HealthIdService:
    request = Request("https://abhasbx.abdm.gov.in/abha/api/v3")

    class ErrorResponse(TypedDict):
        error: Error

    class EnrollmentRequestOtpBody(TypedDict):
        transaction_id: Optional[str]
        scope: List[Literal["abha-enrol", "dl-flow", "mobile-verify", "email-verify"]]
        type: Literal["aadhaar", "mobile"]
        value: str

    class EnrollmentRequestOtpResponse(TypedDict):
        txnId: str
        message: str

    @staticmethod
    def enrollment__request__otp(data: EnrollmentRequestOtpBody):
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
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class EnrollmentEnrolByAadhaarBody(TypedDict):
        transaction_id: str
        otp: str
        mobile: str

    class EnrollmentEnrolByAadhaarResponse(TypedDict):
        ABHAProfile: ABHAProfile
        isNew: bool
        message: str
        tokens: Tokens
        txnId: str

    @staticmethod
    def enrollment__enrol__byAadhaar(data: EnrollmentEnrolByAadhaarBody):
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
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class EnrollmentAuthByAbdmBody(TypedDict):
        scope: List[Literal["abha-enrol", "dl-flow", "mobile-verify", "email-verify"]]
        transaction_id: str
        otp: str

    class EnrollmentAuthByAbdmResponse(TypedDict):
        accounts: List[Accounts]
        message: str
        authResult: Literal["success", "failure"]
        txnId: str

    @staticmethod
    def enrollment__auth__byAbdm(data: EnrollmentAuthByAbdmBody):
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
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class EnrollmentEnrolSuggestionBody(TypedDict):
        transaction_id: str

    class EnrollmentEnrolSuggestionResponse(TypedDict):
        abhaAddressList: List[str]
        txnId: str

    @staticmethod
    def enrollment__enrol_suggestion(data: EnrollmentEnrolSuggestionBody):
        path = "/enrollment/enrol/suggestion"
        return HealthIdService.request.get(
            path,
            headers={
                "TRANSACTION_ID": data.get("transaction_id"),
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class EnrollmentEnrolAbhaAddressBody(TypedDict):
        transaction_id: str
        abha_address: str
        preferred: int

    class EnrollmentEnrolAbhaAddressResponse(TypedDict):
        healthIdNumber: str
        preferredAbhaAddress: str
        txnId: str

    @staticmethod
    def enrollment__enrol_abha_address(data: EnrollmentEnrolAbhaAddressBody):
        payload = {
            "txnId": data.get("transaction_id", ""),
            "abhaAddress": data.get("abha_address", ""),
            "preferred": data.get("preferred", 1),
        }

        path = "/enrollment/enrol/abha-address"
        return HealthIdService.request.post(
            path, payload, headers={"REQUEST-ID": uuid(), "TIMESTAMP": timestamp()}
        )
