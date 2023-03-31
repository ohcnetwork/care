import json
from datetime import datetime, timezone

import nacl.utils
from django.core.cache import cache
from nacl.public import Box, PrivateKey
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
        cache.set(data["notification"]["consentId"], json.dumps(data))

        # data = {
        #     "requestId": "5f7a535d-a3fd-416b-b069-c97d021fbacd",
        #     "timestamp": "2023-03-30T05:00:31.288Z",
        #     "notification": {
        #         "status": "GRANTED",
        #         "consentId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        #         "consentDetail": {
        #             "schemaVersion": "string",
        #             "consentId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        #             "createdAt": "2023-03-30T05:00:31.288Z",
        #             "patient": {"id": "hinapatel79@ndhm"},
        #             "careContexts": [
        #                 {
        #                     "patientReference": "hinapatel79@hospital",
        #                     "careContextReference": "Episode1",
        #                 }
        #             ],
        #             "purpose": {"text": "string", "code": "string", "refUri": "string"},
        #             "hip": {"id": "string", "name": "TESI-HIP"},
        #             "consentManager": {"id": "string"},
        #             "hiTypes": ["OPConsultation"],
        #             "permission": {
        #                 "accessMode": "VIEW",
        #                 "dateRange": {
        #                     "from": "2023-03-30T05:00:31.288Z",
        #                     "to": "2023-03-30T05:00:31.288Z",
        #                 },
        #                 "dataEraseAt": "2023-03-30T05:00:31.288Z",
        #                 "frequency": {"unit": "HOUR", "value": 0, "repeats": 0},
        #             },
        #         },
        #         "signature": "Signature of CM as defined in W3C standards; Base64 encoded",
        #         "grantAcknowledgement": False,
        #     },
        # }

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

        consent_id = data["hiRequest"]["consent"]["id"]
        consent = cache[consent_id] if consent_id not in cache else None
        if not consent or not consent["notification"]["status"] == "GRANTED":
            return Response({}, status=status.HTTP_401_UNAUTHORIZED)

        consent_from = datetime.fromisoformat(
            consent["notification"]["permission"]["dateRange"]["from"][:-1]
        )
        consent_to = datetime.fromisoformat(
            consent["notification"]["permission"]["dateRange"]["to"][:-1]
        )
        now = datetime.now()
        if not consent_from < now and now > consent_to:
            return Response({}, status=status.HTTP_403_FORBIDDEN)

        AbdmGateway.on_data_request(
            {"request_id": data["requestId"], "transaction_id": data["transactionId"]}
        )

        secret_key = PrivateKey.generate()
        public_key = secret_key.public_key.encode().hex()
        hiu_nonce = data["hiRequest"]["keyMaterial"]["nonce"].replace("-", "")
        nonce = nacl.utils.random(32).hex()
        xor_nonce = hex(int(hiu_nonce, base=16) ^ int(nonce, base=16))[2:]

        shared_key = Box(
            secret_key, data["hiRequest"]["keyMaterial"]["dhPublicKey"]["keyValue"]
        )

        AbdmGateway.data_transfer(
            {
                "transaction_id": data["transactionId"],
                "data_push_url": data["hiRequest"]["dataPushUrl"],
                "care_contexts": list(
                    map(
                        lambda context: {
                            "patient_id": context["patientReference"],
                            "consultation_id": context["careContextReference"],
                            "data": shared_key.encrypt(
                                create_consultation_bundle(
                                    PatientConsultation.objects.get(
                                        external_id=context["consultation_id"]
                                    )
                                ),
                                xor_nonce,
                            ),
                        },
                        consent["notification"]["consentDetail"]["careContexts"],
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
#     "requestId": "5f7a535d-a3fd-416b-b069-c97d021fbacd",
#     "timestamp": "2023-03-30T05:00:31.288Z",
#     "notification": {
#         "status": "GRANTED",
#         "consentId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
#         "consentDetail": {
#             "schemaVersion": "string",
#             "consentId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
#             "createdAt": "2023-03-30T05:00:31.288Z",
#             "patient": {"id": "hinapatel79@ndhm"},
#             "careContexts": [
#                 {
#                     "patientReference": "hinapatel79@hospital",
#                     "careContextReference": "Episode1",
#                 }
#             ],
#             "purpose": {"text": "string", "code": "string", "refUri": "string"},
#             "hip": {"id": "string", "name": "TESI-HIP"},
#             "consentManager": {"id": "string"},
#             "hiTypes": ["OPConsultation"],
#             "permission": {
#                 "accessMode": "VIEW",
#                 "dateRange": {
#                     "from": "2023-03-30T05:00:31.288Z",
#                     "to": "2023-03-30T05:00:31.288Z",
#                 },
#                 "dataEraseAt": "2023-03-30T05:00:31.288Z",
#                 "frequency": {"unit": "HOUR", "value": 0, "repeats": 0},
#             },
#         },
#         "signature": "Signature of CM as defined in W3C standards; Base64 encoded",
#         "grantAcknowledgement": False,
#     },
# }

# data = {
#     "requestId": "a1s2c932-2f70-3ds3-a3b5-2sfd46b12a18d",
#     "timestamp": "2023-03-30T06:37:05.476Z",
#     "transactionId": "a1s2c932-2f70-3ds3-a3b5-2sfd46b12a18d",
#     "hiRequest": {
#         "consent": {"id": "string"},
#         "dateRange": {
#             "from": "2023-03-30T06:37:05.476Z",
#             "to": "2023-03-30T06:37:05.476Z",
#         },
#         "dataPushUrl": "string",
#         "keyMaterial": {
#             "cryptoAlg": "ECDH",
#             "curve": "Curve25519",
#             "dhPublicKey": {
#                 "expiry": "2023-03-30T06:37:05.476Z",
#                 "parameters": "Curve25519/32byte random key",
#                 "keyValue": "string",
#             },
#             "nonce": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
#         },
#     },
# }
