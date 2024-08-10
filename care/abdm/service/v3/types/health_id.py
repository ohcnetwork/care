from typing import Dict, List, Literal, Optional, TypedDict


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
    gender: Literal["M", "F", "O"]
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


class EnrollmentRequestOtpBody(TypedDict):
    transaction_id: Optional[str]
    scope: List[Literal["abha-enrol", "dl-flow", "mobile-verify", "email-verify"]]
    type: Literal["aadhaar", "mobile"]
    value: str


class EnrollmentRequestOtpResponse(TypedDict):
    txnId: str
    message: str


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


class EnrollmentAuthByAbdmBody(TypedDict):
    scope: List[Literal["abha-enrol", "dl-flow", "mobile-verify", "email-verify"]]
    transaction_id: str
    otp: str


class EnrollmentAuthByAbdmResponse(TypedDict):
    accounts: List[Account]
    message: str
    authResult: Literal["success", "failure"]
    txnId: str


class EnrollmentEnrolSuggestionBody(TypedDict):
    transaction_id: str


class EnrollmentEnrolSuggestionResponse(TypedDict):
    abhaAddressList: List[str]
    txnId: str


class EnrollmentEnrolAbhaAddressBody(TypedDict):
    transaction_id: str
    abha_address: str
    preferred: int


class EnrollmentEnrolAbhaAddressResponse(TypedDict):
    healthIdNumber: str
    preferredAbhaAddress: str
    txnId: str


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


class ProfileLoginVerifyUserBody(TypedDict):
    abha_number: str
    transaction_id: str
    t_token: str


class ProfileLoginVerifyUserResponse(TypedDict):
    token: str
    expiresIn: int
    refreshToken: str
    refreshExpiresIn: int


class ProfileAccountBody(TypedDict):
    x_token: str


class ProfileAccountResponse(TypedDict, ABHAProfileFull):
    pass
