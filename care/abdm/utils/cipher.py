import json

import requests
from django.conf import settings


class Cipher:
    server_url = settings.FIDELIUS_URL

    def __init__(self, reciever_public_key, reciever_nonce):
        self.reciever_public_key = reciever_public_key
        self.reciever_nonce = reciever_nonce

        self.sender_private_key = None
        self.sender_public_key = None
        self.sender_nonce = None

        self.key_to_share = None

    def generate_key_pair(self):
        response = requests.get(f"{self.server_url}/keys/generate")

        if response.status_code == 200:
            key_material = response.json()

            self.sender_private_key = key_material["privateKey"]
            self.sender_public_key = key_material["publicKey"]
            self.sender_nonce = key_material["nonce"]

            return key_material

        return None

    def encrypt(self, paylaod):
        if not self.sender_private_key:
            key_material = self.generate_key_pair()

            if not key_material:
                return None

        response = requests.post(
            f"{self.server_url}/encrypt",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "receiverPublicKey": self.reciever_public_key,
                    "receiverNonce": self.reciever_nonce,
                    "senderPrivateKey": self.sender_private_key,
                    "senderPublicKey": self.sender_public_key,
                    "senderNonce": self.sender_nonce,
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
                "nonce": self.sender_nonce,
            }

        return None
