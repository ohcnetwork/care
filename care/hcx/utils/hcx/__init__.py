from jwcrypto import jwk, jwe
from urllib.parse import urlencode
import requests
import uuid
import json
import datetime
from .operations import HcxOperations


class Hcx:
    def __init__(
        self,
        protocolBasePath="http://staging-hcx.swasth.app/api/v0.7",
        participantCode="1-521eaec7-8cb9-4b6c-8b4e-4dba300af6f4",
        authBasePath="https://staging-hcx.swasth.app/auth/realms/swasth-health-claim-exchange/protocol/openid-connect/token",
        username="swasth_mock_provider@swasthapp.org",
        password="Opensaber@123",
        encryptionPrivateKeyURL="https://raw.githubusercontent.com/Swasth-Digital-Health-Foundation/hcx-platform/sprint-30/demo-app/server/resources/keys/x509-private-key.pem",
        igUrl="https://ig.hcxprotocol.io/v0.7.1",
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

    def createHeaders(self, recipientCode=None):
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
            "x-hcx-correlation_id": str(uuid.uuid4()),
            "x-hcx-workflow_id": str(uuid.uuid4()),
            "x-hcx-api_call_id": str(uuid.uuid4()),
        }
        return hcx_headers

    def encryptJWE(self, recipientCode=None, fhirPayload=None):
        if recipientCode is None:
            raise ValueError("Recipient code can not be empty, must be a string")
        if type(fhirPayload) is not dict:
            raise ValueError("Fhir paylaod must be a dictionary")
        regsitry_data = self.searchRegistry(
            searchField="participant_code", searchValue=recipientCode
        )
        public_cert = requests.get(regsitry_data["participants"][0]["encryption_cert"])
        key = jwk.JWK.from_pem(public_cert.text.encode("utf-8"))
        headers = self.createHeaders(recipientCode)
        jwePayload = jwe.JWE(
            str(json.dumps(fhirPayload)), recipient=key, protected=json.dumps(headers)
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

    def generateOutgoingHcxCall(self, fhirPayload, operation, recipientCode):
        encryptedString = self.encryptJWE(
            recipientCode=recipientCode, fhirPayload=fhirPayload
        )
        response = self.makeHcxApiCall(
            operation=operation, encryptedString=encryptedString
        )
        return {"payload": encryptedString, "response": response}

    def processIncomingRequest(self, encryptedString):
        return self.decryptJWE(encryptedString=encryptedString)
