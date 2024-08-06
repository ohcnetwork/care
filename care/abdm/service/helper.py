from base64 import b64encode
from datetime import datetime, timezone
from uuid import uuid4

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA1
from Crypto.PublicKey import RSA

from care.abdm.service.request import Request


def encrypt_message(message: str):
    rsa_public_key = RSA.importKey(
        Request("https://healthidsbx.abdm.gov.in/api/v1").get("/auth/cert").text.strip()
    )

    cipher = PKCS1_OAEP.new(rsa_public_key, hashAlgo=SHA1)
    encrypted_message = cipher.encrypt(message.encode())

    return b64encode(encrypted_message).decode()


def timestamp():
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uuid():
    return str(uuid4())
