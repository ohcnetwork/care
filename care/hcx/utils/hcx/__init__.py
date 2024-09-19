import datetime
import json
import uuid
from urllib.parse import urlencode

import requests
from django.conf import settings
from jwcrypto import jwe, jwk


class Hcx:
    def __init__(
        self,
        protocolBasePath=settings.HCX_PROTOCOL_BASE_PATH,
        participantCode=settings.HCX_PARTICIPANT_CODE,
        authBasePath=settings.HCX_AUTH_BASE_PATH,
        username=settings.HCX_USERNAME,
        password=settings.HCX_PASSWORD,
        encryptionPrivateKeyURL=settings.HCX_ENCRYPTION_PRIVATE_KEY_URL,
        igUrl=settings.HCX_IG_URL,
    ):
        self.protocolBasePath = protocolBasePath
        self.participantCode = participantCode
        self.authBasePath = authBasePath
        self.username = username
        self.password = password
        self.encryptionPrivateKeyURL = encryptionPrivateKeyURL
        self.igUrl = igUrl

    def generateHcxToken(self):
        url = self.authBasePath

        payload = {
            "client_id": "registry-frontend",
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
        }
        payload_urlencoded = urlencode(payload)
        headers = {"content-type": "application/x-www-form-urlencoded"}

        response = requests.request(
            "POST", url, headers=headers, data=payload_urlencoded
        )
        y = json.loads(response.text)
        return y["access_token"]

    def searchRegistry(self, searchField, searchValue):
        url = self.protocolBasePath + "/participant/search"
        access_token = self.generateHcxToken()
        payload = json.dumps({"filters": {searchField: {"eq": searchValue}}})
        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        return dict(json.loads(response.text))

    def createHeaders(self, recipientCode=None, correlationId=None):
        # creating HCX headers
        # getting sender code
        # regsitry_user = self.searchRegistry("primary_email", self.username)
        hcx_headers = {
            "alg": "RSA-OAEP",
            "enc": "A256GCM",
            "x-hcx-recipient_code": recipientCode,
            "x-hcx-timestamp": datetime.datetime.now()
            .astimezone()
            .replace(microsecond=0)
            .isoformat(),
            "x-hcx-sender_code": self.participantCode,
            "x-hcx-correlation_id": (
                correlationId if correlationId else str(uuid.uuid4())
            ),
            # "x-hcx-workflow_id": str(uuid.uuid4()),
            "x-hcx-api_call_id": str(uuid.uuid4()),
            # "x-hcx-status": "response.complete",
        }
        return hcx_headers

    def encryptJWE(self, recipientCode=None, fhirPayload=None, correlationId=None):
        if recipientCode is None:
            raise ValueError("Recipient code can not be empty, must be a string")
        if type(fhirPayload) is not dict:
            raise ValueError("Fhir paylaod must be a dictionary")
        regsitry_data = self.searchRegistry(
            searchField="participant_code", searchValue=recipientCode
        )
        public_cert = requests.get(regsitry_data["participants"][0]["encryption_cert"])
        key = jwk.JWK.from_pem(public_cert.text.encode("utf-8"))
        headers = self.createHeaders(recipientCode, correlationId)
        jwePayload = jwe.JWE(
            str(json.dumps(fhirPayload)),
            recipient=key,
            protected=json.dumps(headers),
        )
        enc = jwePayload.serialize(compact=True)
        return enc

    def decryptJWE(self, encryptedString):
        private_key = requests.get(self.encryptionPrivateKeyURL)
        privateKey = jwk.JWK.from_pem(private_key.text.encode("utf-8"))
        jwetoken = jwe.JWE()
        jwetoken.deserialize(encryptedString, key=privateKey)
        return {
            "headers": dict(json.loads(jwetoken.payload.decode("utf-8"))),
            "payload": dict(json.loads(jwetoken.payload.decode("utf-8"))),
        }

    def makeHcxApiCall(self, operation, encryptedString):
        url = "".join(self.protocolBasePath + operation.value)
        print("making the API call to url " + url)
        access_token = self.generateHcxToken()
        payload = json.dumps({"payload": encryptedString})
        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/json",
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        return dict(json.loads(response.text))

    def generateOutgoingHcxCall(
        self, fhirPayload, operation, recipientCode, correlationId=None
    ):
        encryptedString = self.encryptJWE(
            recipientCode=recipientCode,
            fhirPayload=fhirPayload,
            correlationId=correlationId,
        )
        response = self.makeHcxApiCall(
            operation=operation, encryptedString=encryptedString
        )
        return {"payload": encryptedString, "response": response}

    def processIncomingRequest(self, encryptedString):
        return self.decryptJWE(encryptedString=encryptedString)
