import datetime
import json
import logging
import uuid
from urllib.parse import urlencode

import requests
from django.conf import settings
from jwcrypto import jwe, jwk

logger = logging.getLogger(__name__)

HCX_API_TIMEOUT = 25


class Hcx:
    def __init__(
        self,
        protocol_base_path=settings.HCX_PROTOCOL_BASE_PATH,
        participant_code=settings.HCX_PARTICIPANT_CODE,
        auth_base_path=settings.HCX_AUTH_BASE_PATH,
        username=settings.HCX_USERNAME,
        password=settings.HCX_PASSWORD,
        encryption_private_key_url=settings.HCX_ENCRYPTION_PRIVATE_KEY_URL,
        ig_url=settings.HCX_IG_URL,
    ):
        self.protocol_base_path = protocol_base_path
        self.participant_code = participant_code
        self.auth_base_path = auth_base_path
        self.username = username
        self.password = password
        self.encryption_private_key_url = encryption_private_key_url
        self.ig_url = ig_url

    def generate_hcx_token(self):
        url = self.auth_base_path

        payload = {
            "client_id": "registry-frontend",
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
        }
        payload_urlencoded = urlencode(payload)
        headers = {"content-type": "application/x-www-form-urlencoded"}

        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=payload_urlencoded,
        )
        y = json.loads(response.text)
        return y["access_token"]

    def search_registry(self, search_field, search_value):
        url = self.protocol_base_path + "/participant/search"
        access_token = self.generate_hcx_token()
        payload = json.dumps({"filters": {search_field: {"eq": search_value}}})
        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        return dict(json.loads(response.text))

    def create_headers(self, recipient_code=None, correlation_id=None):
        return {
            "alg": "RSA-OAEP",
            "enc": "A256GCM",
            "x-hcx-recipient_code": recipient_code,
            "x-hcx-timestamp": datetime.datetime.now()
            .astimezone()
            .replace(microsecond=0)
            .isoformat(),
            "x-hcx-sender_code": self.participant_code,
            "x-hcx-correlation_id": correlation_id
            if correlation_id
            else str(uuid.uuid4()),
            # "x-hcx-workflow_id": str(uuid.uuid4()),
            "x-hcx-api_call_id": str(uuid.uuid4()),
            # "x-hcx-status": "response.complete",
        }

    def encrypt_jwe(self, recipient_code=None, fhir_payload=None, correlation_id=None):
        if recipient_code is None:
            raise ValueError("Recipient code can not be empty, must be a string")
        if not isinstance(fhir_payload, dict):
            raise ValueError("Fhir paylaod must be a dictionary")
        regsitry_data = self.search_registry(
            search_field="participant_code",
            search_value=recipient_code,
        )
        response = requests.get(
            regsitry_data["participants"][0]["encryption_cert"],
            timeout=HCX_API_TIMEOUT,
        )
        key = jwk.JWK.from_pem(response.text.encode("utf-8"))
        headers = self.create_headers(recipient_code, correlation_id)
        jwe_payload = jwe.JWE(
            str(json.dumps(fhir_payload)),
            recipient=key,
            protected=json.dumps(headers),
        )
        return jwe_payload.serialize(compact=True)

    def decrypt_jwe(self, encrypted_string):
        response = requests.get(
            self.encryption_private_key_url,
            timeout=HCX_API_TIMEOUT,
        )
        private_key = jwk.JWK.from_pem(response.text.encode("utf-8"))
        jwe_token = jwe.JWE()
        jwe_token.deserialize(encrypted_string, key=private_key)
        return {
            "headers": dict(json.loads(jwe_token.payload.decode("utf-8"))),
            "payload": dict(json.loads(jwe_token.payload.decode("utf-8"))),
        }

    def make_hcx_api_call(self, operation, encrypted_string):
        url = "".join(self.protocol_base_path + operation.value)
        logger.info("making hxc api call to url: %s", url)
        access_token = self.generate_hcx_token()
        payload = json.dumps({"payload": encrypted_string})
        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return dict(json.loads(response.text))

    def generate_outgoing_hcx_call(
        self,
        fhir_payload,
        operation,
        recipient_code,
        correlation_id=None,
    ):
        encrypted_string = self.encrypt_jwe(
            recipient_code=recipient_code,
            fhir_payload=fhir_payload,
            correlation_id=correlation_id,
        )
        response = self.make_hcx_api_call(
            operation=operation,
            encrypted_string=encrypted_string,
        )
        return {"payload": encrypted_string, "response": response}

    def process_incoming_request(self, encrypted_string):
        return self.decrypt_jwe(encrypted_string=encrypted_string)
