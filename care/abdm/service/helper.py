from base64 import b64encode
from datetime import datetime, timezone
from uuid import uuid4

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA1
from Crypto.PublicKey import RSA
from django.conf import settings
from django.db.models import Q
from rest_framework.exceptions import APIException

from care.abdm.models import AbhaNumber
from care.abdm.service.request import Request


class ABDMAPIException(APIException):
    status_code = 400
    default_code = "ABDM_ERROR"
    default_detail = "An error occured while trying to communicate with ABDM"


class ABDMInternalException(APIException):
    status_code = 400
    default_code = "ABDM_INTERNAL_ERROR"
    default_detail = "An internal error occured while trying to communicate with ABDM"


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


def hf_id_from_abha_id(health_id: str):
    abha_number = AbhaNumber.objects.filter(
        Q(abha_number=health_id) | Q(health_id=health_id)
    ).first()

    if not abha_number:
        ABDMInternalException(detail="Given ABHA Number does not exist in the system")

    if not hasattr(abha_number, "patientregistration"):
        ABDMInternalException(detail="Given ABHA Number is not linked to any patient")

    patient_facility = abha_number.patientregistration.last_consultation.facility

    if not hasattr(patient_facility, "healthfacility"):
        raise ABDMInternalException(
            detail="The facility to which the patient is linked does not have a health facility linked"
        )

    return patient_facility.healthfacility.hf_id


def cm_id():
    return settings.X_CM_ID
