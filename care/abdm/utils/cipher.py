import json

import requests
from django.conf import settings


class Cipher:
    server_url = settings.FIDELIUS_URL

    def __init__(
        self,
        external_public_key,
        external_nonce,
        internal_private_key=None,
        internal_public_key=None,
        internal_nonce=None,
    ):
        self.external_public_key = external_public_key
        self.external_nonce = external_nonce

        self.internal_private_key = internal_private_key
        self.internal_public_key = internal_public_key
        self.internal_nonce = internal_nonce

        self.key_to_share = None

    def generate_key_pair(self):
        response = requests.get(f"{self.server_url}/keys/generate")

        if response.status_code == 200:
            key_material = response.json()

            self.internal_private_key = key_material["privateKey"]
            self.internal_public_key = key_material["publicKey"]
            self.internal_nonce = key_material["nonce"]

            return key_material

        return None

    def encrypt(self, paylaod):
        if not self.internal_private_key:
            key_material = self.generate_key_pair()

            if not key_material:
                return None

        response = requests.post(
            f"{self.server_url}/encrypt",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "receiverPublicKey": self.external_public_key,
                    "receiverNonce": self.external_nonce,
                    "senderPrivateKey": self.internal_private_key,
                    "senderPublicKey": self.internal_public_key,
                    "senderNonce": self.internal_nonce,
                    "plainTextData": paylaod,
                }
            ),
        )

        if response.status_code == 200:
            data = response.json()
            self.key_to_share = data["keyToShare"]

            return {
                "public_key": self.key_to_share,
                "data": data["encryptedData"],
                "nonce": self.internal_nonce,
            }

        return None

    def decrypt(self, paylaod):
        response = requests.post(
            f"{self.server_url}/decrypt",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "receiverPrivateKey": self.internal_private_key,
                    "receiverNonce": self.internal_nonce,
                    "senderPublicKey": self.external_public_key,
                    "senderNonce": self.external_nonce,
                    "encryptedData": paylaod,
                }
            ),
        )

        if response.status_code == 200:
            data = response.json()

            return data["decryptedData"]

        return None
