from enum import Enum

from pydantic import BaseModel


class TOTPSetupResponse(BaseModel):
    uri: str
    secret_key: str


class TOTPVerifyRequest(BaseModel):
    code: str


class TOTPVerifyResponse(BaseModel):
    backup_codes: list[str]


class PasswordVerifyRequest(BaseModel):
    password: str


class LoginMethod(str, Enum):
    totp = "totp"
    backup = "backup"


class MFALoginRequest(BaseModel):
    method: LoginMethod
    code: str
    temp_token: str


class MFALoginResponse(BaseModel):
    access: str
    refresh: str
