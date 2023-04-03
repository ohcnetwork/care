import base64
import json
from datetime import datetime, timezone

import nacl.utils
from Crypto.Cipher import AES
from Crypto.Hash import SHA512
from Crypto.Protocol.KDF import HKDF
from django.core.cache import cache
from nacl.encoding import Base64Encoder
from nacl.public import Box, PrivateKey, PublicKey
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from care.abdm.utils.api_call import AbdmGateway
from care.abdm.utils.fhir import create_consultation_bundle
from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_consultation import PatientConsultation


class OnFetchView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print("on-fetch-modes", data)
        AbdmGateway().init(data["resp"]["requestId"])
        return Response({}, status=status.HTTP_202_ACCEPTED)


class OnInitView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print("on-init", data)
        AbdmGateway().confirm(data["auth"]["transactionId"], data["resp"]["requestId"])
        return Response({}, status=status.HTTP_202_ACCEPTED)


class OnConfirmView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)
        AbdmGateway().save_linking_token(
            data["auth"]["patient"],
            data["auth"]["accessToken"],
            data["resp"]["requestId"],
        )
        return Response({}, status=status.HTTP_202_ACCEPTED)


class OnAddContextsView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)
        return Response({}, status=status.HTTP_202_ACCEPTED)


class DiscoverView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data

        patients = PatientRegistration.objects.all()
        verified_identifiers = data["patient"]["verifiedIdentifiers"]
        matched_by = []
        if len(verified_identifiers) == 0:
            return Response(
                "No matching records found, need more data",
                status=status.HTTP_404_NOT_FOUND,
            )
        else:
            for identifier in verified_identifiers:
                if identifier["type"] == "MOBILE":
                    matched_by.append(identifier["value"])
                    patients = patients.filter(phone_number=identifier["value"])

                if identifier["type"] == "NDHM_HEALTH_NUMBER":
                    matched_by.append(identifier["value"])
                    patients = patients.filter(
                        abha_number__abha_number=identifier["value"]
                    )

                if identifier["type"] == "HEALTH_ID":
                    matched_by.append(identifier["value"])
                    patients = patients.filter(
                        abha_number__health_id=identifier["value"]
                    )

        patients.filter(
            abha_number__name=data["patient"]["name"],
            abha_number__gender=data["patient"]["gender"],
            # TODO: check date also
        )

        if len(patients) != 1:
            return Response(
                "No matching records found, need more data",
                status=status.HTTP_404_NOT_FOUND,
            )

        AbdmGateway().on_discover(
            {
                "request_id": data["requestId"],
                "transaction_id": data["transactionId"],
                "patient_id": str(patients[0].external_id),
                "patient_name": patients[0].name,
                "care_contexts": list(
                    map(
                        lambda consultation: {
                            "id": str(consultation.external_id),
                            "name": f"Encounter: {str(consultation.created_date.date())}",
                        },
                        PatientConsultation.objects.filter(patient=patients[0]),
                    )
                ),
                "matched_by": matched_by,
            }
        )
        return Response({}, status=status.HTTP_202_ACCEPTED)


class LinkInitView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data

        # TODO: send otp to patient

        AbdmGateway().on_link_init(
            {
                "request_id": data["requestId"],
                "transaction_id": data["transactionId"],
                "patient_id": data["patient"]["referenceNumber"],
                "phone": "7639899448",
            }
        )
        return Response({}, status=status.HTTP_202_ACCEPTED)


class LinkConfirmView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data

        # TODO: verify otp

        patient = PatientRegistration.objects.get(
            external_id=data["confirmation"]["linkRefNumber"]
        )
        AbdmGateway().on_link_confirm(
            {
                "request_id": data["requestId"],
                "patient_id": str(patient.external_id),
                "patient_name": patient.name,
                "care_contexts": list(
                    map(
                        lambda consultation: {
                            "id": str(consultation.external_id),
                            "name": f"Encounter: {str(consultation.created_date.date())}",
                        },
                        PatientConsultation.objects.filter(patient=patient),
                    )
                ),
            }
        )

        return Response({}, status=status.HTTP_202_ACCEPTED)


class NotifyView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)

        # TODO: create a seperate cache and also add a expiration time
        cache.set(data["notification"]["consentDetail"]["consentId"], json.dumps(data))

        AbdmGateway().on_notify(
            {
                "request_id": data["requestId"],
                "consent_id": data["notification"]["consentId"],
            }
        )
        return Response({}, status=status.HTTP_202_ACCEPTED)


class RequestDataView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)

        # TODO: uncomment later
        consent_id = data["hiRequest"]["consent"]["id"]
        consent = json.loads(cache.get(consent_id)) if consent_id in cache else None
        if not consent or not consent["notification"]["status"] == "GRANTED":
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        # TODO: check if from and to are in range and consent expiry is greater than today
        # consent_from = datetime.fromisoformat(
        #     consent["notification"]["permission"]["dateRange"]["from"][:-1]
        # )
        # consent_to = datetime.fromisoformat(
        #     consent["notification"]["permission"]["dateRange"]["to"][:-1]
        # )
        # now = datetime.now()
        # if not consent_from < now and now > consent_to:
        #     return Response({}, status=status.HTTP_403_FORBIDDEN)

        AbdmGateway().on_data_request(
            {"request_id": data["requestId"], "transaction_id": data["transactionId"]}
        )

        hiu_public_key_b64 = data["hiRequest"]["keyMaterial"]["dhPublicKey"]["keyValue"]
        hiu_public_key_hex = base64.b64decode(hiu_public_key_b64).hex()[2:]
        hiu_public_key_hex_x = hiu_public_key_hex[:64]
        # hiu_public_key_hex_y = hiu_public_key_hex[64:]
        hiu_public_key = PublicKey(bytes.fromhex(hiu_public_key_hex_x))
        hiu_nonce = data["hiRequest"]["keyMaterial"]["nonce"]

        secret_key = PrivateKey.generate()
        public_key = secret_key.public_key.encode(Base64Encoder)
        nonce = nacl.utils.random(32).hex()

        xored_nonce = hex(
            int(base64.b64decode(hiu_nonce).hex(), base=16) ^ int(nonce, base=16)
        )[2:]
        salt = xored_nonce[:40]
        iv = xored_nonce[40:]
        shared_key = Box(secret_key, hiu_public_key).encode(Base64Encoder).hex()

        hkdf_key = HKDF(bytes.fromhex(shared_key), 32, bytes.fromhex(salt), SHA512)

        cipher = AES.new(hkdf_key, AES.MODE_GCM, iv.encode("utf8"))

        AbdmGateway().data_transfer(
            {
                "transaction_id": data["transactionId"],
                "data_push_url": data["hiRequest"]["dataPushUrl"],
                "care_contexts": list(
                    map(
                        lambda context: {
                            "patient_id": context["patientReference"],
                            "consultation_id": context["careContextReference"],
                            "data": cipher.encrypt(
                                create_consultation_bundle(
                                    PatientConsultation.objects.get(
                                        external_id=context["careContextReference"]
                                    )
                                )
                                .json()
                                .encode("utf8")
                            ),
                        },
                        consent["notification"]["consentDetail"]["careContexts"][3:],
                    )
                ),
                "key_material": {
                    "cryptoAlg": "ECDH",
                    "curve": "Curve25519",
                    "dhPublicKey": {
                        "expiry": str(
                            datetime.now(tz=timezone.utc).strftime(
                                "%Y-%m-%dT%H:%M:%S.000Z"
                            )
                        ),  # not sure what to put here
                        "parameters": f"Curve25519/{public_key}",  # not sure what to put here
                        "keyValue": public_key,
                    },
                    "nonce": nonce,
                },
            }
        )

        AbdmGateway().data_notify(
            {
                "consent_id": data["hiRequest"]["consent"]["id"],
                "transaction_id": data["transactionId"],
                "care_contexts": list(
                    map(
                        lambda context: {"id": context["careContextReference"]},
                        consent["notification"]["consentDetail"]["careContexts"],
                    )
                ),
            }
        )

        return Response({}, status=status.HTTP_202_ACCEPTED)


# consent = {
#     "notification": {
#         "consentDetail": {
#             "consentId": "feb6a86a-3b8d-4c3b-9860-41f7b0ec1218",
#             "createdAt": "2023-03-31T15:30:58.212283603",
#             "purpose": {"text": "Self Requested", "code": "PATRQT", "refUri": None},
#             "patient": {"id": "khavinshankar@sbx"},
#             "consentManager": {"id": "sbx"},
#             "hip": {"id": "IN3210000017", "name": "Coronasafe Care 01"},
#             "hiTypes": ["OPConsultation"],
#             "permission": {
#                 "accessMode": "VIEW",
#                 "dateRange": {
#                     "from": "2023-03-29T15:28:00",
#                     "to": "2023-03-31T15:28:00",
#                 },
#                 "dataEraseAt": "2023-04-01T15:28:18.501",
#                 "frequency": {"unit": "HOUR", "value": 1, "repeats": 0},
#             },
#             "careContexts": [
#                 {
#                     "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
#                     "careContextReference": "c7134ba2-692a-40f5-a143-d306896436dd",
#                 },
#                 {
#                     "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
#                     "careContextReference": "56015494-bac8-486d-85b6-6f67d1708764",
#                 },
#                 {
#                     "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
#                     "careContextReference": "140f79f9-4e4e-4bc1-b43e-ebce3c9313a5",
#                 },
#                 {
#                     "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
#                     "careContextReference": "90742c64-ac7b-4806-bcb6-2f8418d0bd5b",
#                 },
#                 {
#                     "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
#                     "careContextReference": "829cf90f-23c0-4978-be5c-94131be5d2f9",
#                 },
#             ],
#         },
#         "status": "GRANTED",
#         "signature": "jnG9oxlV6jRfxqXgW781ehe5/VYyzG5Z3aWNsgMJB2GB4IGKRu6ZqMu82WYJOKJqY62Oy7J90XBPAWWacQJVoa1eq1qcw6Fgc7pejihVVN/Ohdu2S6LSIi27DdVRQLR//7bCTSfe1P+3qCj+GkMVGgX0LbtYp2n3awZ0kRZFDt5JUI1oqWItx4Zz8pOF+1zjhD+AdzydE4JrKl3o/qICsb6+C9Iqe0ZrfqWAOmpESD17Z0p6trzkbHgeWXW/7S4Fg27cAJt9Z+HCa4PZLTOm5yx231QXyTRKCPrSQsZDe/OR5fUu3b0bDWf4F1FIJKXLG8ZmlsCs0T1gs3n8MkWYmQ==",
#         "consentId": "feb6a86a-3b8d-4c3b-9860-41f7b0ec1218",
#         "grantAcknowledgement": False,
#     },
#     "requestId": "99b5e499-c81f-42f9-a550-e0eef2b1e2c1",
#     "timestamp": "2023-03-31T15:30:58.236624856",
# }


# data = {
#     "transactionId": "2839dccc-c9e5-4e29-8904-440a1dc7f0cf",
#     "requestId": "87e509d3-c43e-4da5-a39c-296c01740a79",
#     "timestamp": "2023-03-31T15:31:28.587999924",
#     "hiRequest": {
#         "consent": {"id": "feb6a86a-3b8d-4c3b-9860-41f7b0ec1218"},
#         "dateRange": {"from": "2023-03-29T15:28:00", "to": "2023-03-31T15:28:00"},
#         "dataPushUrl": "https://dev.abdm.gov.in/api-hiu/data/notification",
#         "keyMaterial": {
#             "cryptoAlg": "ECDH",
#             "curve": "curve25519",
#             "dhPublicKey": {
#                 "expiry": "2023-04-02T15:30:58.49682",
#                 "parameters": "Ephemeral public key",
#                 "keyValue": "BHkJo9SpkcGmxTNqo4pYdvGuZ/ELbwwCxoLbqyY5kuSyJ42FBfQUsLkg8prSQrzk5lIwQ3JEuXYsignQT5juGow=",
#             },
#             "nonce": "EAeHOfrH6xNXxj2nM6TClwJ6k7FNWQ9UzAx2ylVyCzE=",
#         },
#     },
# }
