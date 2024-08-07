from typing import Dict, List, Literal, Optional, TypedDict

from care.abdm.service.helper import encrypt_message, timestamp, uuid
from care.abdm.service.request import Request


class LocalizedDetails(TypedDict):
    name: str
    stateName: str
    districtName: str
    villageName: str
    wardName: str
    townName: str
    gender: str
    localizedLabels: Dict[str, str]


class ABHAProfileFull(TypedDict):
    ABHANumber: str
    preferredAbhaAddress: str
    mobile: str
    firstName: str
    middleName: str
    lastName: str
    name: str
    yearOfBirth: str
    dayOfBirth: str
    monthOfBirth: str
    gender: str
    profilePhoto: str
    status: str
    stateCode: str
    districtCode: str
    pincode: str
    address: str
    kycPhoto: str
    stateName: str
    districtName: str
    subdistrictName: str
    townName: str
    authMethods: List[str]
    tags: Dict[str, str]
    kycVerified: bool
    localizedDetails: LocalizedDetails
    createdDate: str
    phrAddress: Optional[List[str]]


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


class Token(TypedDict):
    expiresIn: int
    refreshExpiresIn: int
    refreshToken: str
    token: str


class Account(TypedDict):
    ABHANumber: str
    preferredAbhaAddress: Optional[str]
    name: Optional[str]
    gender: Optional[Literal["M", "F", "O"]]
    dob: Optional[str]
    status: Optional[Literal["ACTIVE"]]
    profilePhoto: Optional[str]
    kycVerified: Optional[bool]


class User(TypedDict):
    abhaAddress: str
    fullName: str
    abhaNumber: str
    status: str
    kycStatus: str


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
        tokens: Token
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
        accounts: List[Account]
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
    def enrollment__enrol__suggestion(data: EnrollmentEnrolSuggestionBody):
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
    def enrollment__enrol__abha_address(data: EnrollmentEnrolAbhaAddressBody):
        payload = {
            "txnId": data.get("transaction_id", ""),
            "abhaAddress": data.get("abha_address", ""),
            "preferred": data.get("preferred", 1),
        }

        path = "/enrollment/enrol/abha-address"
        return HealthIdService.request.post(
            path, payload, headers={"REQUEST-ID": uuid(), "TIMESTAMP": timestamp()}
        )

    class ProfileLoginRequestOtpBody(TypedDict):
        scope: List[
            Literal[
                "abha-login",
                "aadhaar-verify",
                "mobile-verify",
            ]
        ]
        type: Literal["aadhaar", "mobile", "abha-number"]
        value: str
        otp_system: Literal["aadhaar", "abdm"]

    class ProfileLoginRequestOtpResponse(TypedDict):
        txnId: str
        message: str

    @staticmethod
    def profile__login__request__otp(data: ProfileLoginRequestOtpBody):
        payload = {
            "scope": data.get("scope", []),
            "loginHint": data.get("type", ""),
            "loginId": encrypt_message(data.get("value", "")),
            "otpSystem": data.get("otp_system", ""),
        }

        path = "/profile/login/request/otp"
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class ProfileLoginVerifyBody(TypedDict):
        scope: List[
            Literal[
                "abha-login",
                "aadhaar-verify",
                "mobile-verify",
            ]
        ]
        transaction_id: str
        otp: str

    class ProfileLoginVerifyResponse(TypedDict):
        txnId: str
        authResult: Literal["success", "failure"]
        message: str
        token: str
        expiresIn: int
        refreshToken: str
        refreshExpiresIn: int
        accounts: List[Account]

    @staticmethod
    def profile__login__verify(data: ProfileLoginVerifyBody):
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
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class PhrWebLoginAbhaRequestOtpBody(TypedDict):
        scope: List[
            Literal[
                "abha-address-login",
                "aadhaar-verify",
                "mobile-verify",
            ]
        ]
        type: Literal["abha-address"]
        value: str
        otp_system: Literal["aadhaar", "abdm"]

    class PhrWebLoginAbhaRequestOtpResponse(TypedDict):
        txnId: str
        message: str

    @staticmethod
    def phr__web__login__abha__request__otp(data: PhrWebLoginAbhaRequestOtpBody):
        payload = {
            "scope": data.get("scope", []),
            "loginHint": data.get("type", ""),
            "loginId": encrypt_message(data.get("value", "")),
            "otpSystem": data.get("otp_system", ""),
        }

        path = "/phr/web/login/abha/request/otp"
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class PhrWebLoginAbhaVerifyBody(TypedDict):
        scope: List[
            Literal[
                "abha-address-login",
                "aadhaar-verify",
                "mobile-verify",
            ]
        ]
        transaction_id: str
        otp: str

    class PhrWebLoginAbhaVerifyResponse(TypedDict):
        message: str
        authResult: Literal["success", "failure"]
        users: List[User]
        tokens: Token

    @staticmethod
    def phr__web__login__abha__verify(data: PhrWebLoginAbhaVerifyBody):
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
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class PhrWebLoginAbhaSearchBody(TypedDict):
        abha_address: str

    class PhrWebLoginAbhaSearchResponse(TypedDict):
        healthIdNumber: str
        abhaAddress: str
        authMethods: List[Literal["AADHAAR_OTP", "MOBILE_OTP", "DEMOGRAPHICS"]]
        blockedAuthMethods: List[Literal["AADHAAR_OTP", "MOBILE_OTP", "DEMOGRAPHICS"]]
        status: Literal["ACTIVE"]
        message: str | None
        fullName: str
        mobile: str

    @staticmethod
    def phr__web__login__abha__search(data: PhrWebLoginAbhaSearchBody):
        payload = {
            "abhaAddress": data.get("abha_address", ""),
        }

        path = "/phr/web/login/abha/search"
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
            },
        )

    class ProfileLoginVerifyUserBody(TypedDict):
        abha_number: str
        transaction_id: str
        t_token: str

    class ProfileLoginVerifyUserResponse(TypedDict):
        token: str
        expiresIn: int
        refreshToken: str
        refreshExpiresIn: int

    @staticmethod
    def profile__login__verify__user(data: ProfileLoginVerifyUserBody):
        payload = {
            "abhaNumber": data.get("abha_number", ""),
            "txnId": data.get("transaction_id", ""),
        }

        path = "/profile/login/verify/user"
        return HealthIdService.request.post(
            path,
            payload,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "T-TOKEN": f"Bearer {data.get('t_token', '')}",
            },
        )

    class ProfileAccountBody(TypedDict):
        x_token: str

    class ProfileAccountResponse(TypedDict, ABHAProfileFull):
        pass

    @staticmethod
    def profile__account(data: ProfileAccountBody):
        path = "/profile/account"
        return HealthIdService.request.get(
            path,
            headers={
                "REQUEST-ID": uuid(),
                "TIMESTAMP": timestamp(),
                "X-TOKEN": f"Bearer {data.get('x_token', '')}",
            },
        )
