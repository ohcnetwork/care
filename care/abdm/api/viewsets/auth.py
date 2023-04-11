import json
from datetime import datetime, timedelta

from django.core.cache import cache
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from care.abdm.utils.api_call import AbdmGateway
from care.abdm.utils.cipher import Cipher
from care.abdm.utils.fhir import Fhir
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

        on_data_request_response = AbdmGateway().on_data_request(
            {"request_id": data["requestId"], "transaction_id": data["transactionId"]}
        )

        if not on_data_request_response.status_code == 202:
            return Response(
                on_data_request_response, status=status.HTTP_400_BAD_REQUEST
            )

        cipher = Cipher(
            data["hiRequest"]["keyMaterial"]["dhPublicKey"]["keyValue"],
            data["hiRequest"]["keyMaterial"]["nonce"],
        )

        print(consent["notification"]["consentDetail"]["careContexts"][:1:-1])

        AbdmGateway().data_transfer(
            {
                "transaction_id": data["transactionId"],
                "data_push_url": data["hiRequest"]["dataPushUrl"],
                "care_contexts": sum(
                    list(
                        map(
                            lambda context: list(
                                map(
                                    lambda record: {
                                        "patient_id": context["patientReference"],
                                        "consultation_id": context[
                                            "careContextReference"
                                        ],
                                        "data": cipher.encrypt(
                                            Fhir(
                                                PatientConsultation.objects.get(
                                                    external_id=context[
                                                        "careContextReference"
                                                    ]
                                                )
                                            ).create_record(record)
                                        )["data"],
                                    },
                                    consent["notification"]["consentDetail"]["hiTypes"],
                                )
                            ),
                            consent["notification"]["consentDetail"]["careContexts"][
                                :-2:-1
                            ],
                        )
                    ),
                    [],
                ),
                "key_material": {
                    "cryptoAlg": "ECDH",
                    "curve": "Curve25519",
                    "dhPublicKey": {
                        "expiry": (datetime.now() + timedelta(days=2)).isoformat(),
                        "parameters": "Curve25519/32byte random key",
                        "keyValue": cipher.key_to_share,
                    },
                    "nonce": cipher.sender_nonce,
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
                        consent["notification"]["consentDetail"]["careContexts"][
                            :-2:-1
                        ],
                    )
                ),
            }
        )

        return Response({}, status=status.HTTP_202_ACCEPTED)


consent = {
    "notification": {
        "consentDetail": {
            "consentId": "0ad38ac1-5f61-480a-b9d6-6ace3e2d2139",
            "createdAt": "2023-04-11T08:01:55.554799671",
            "purpose": {"text": "Care Management", "code": "CAREMGT", "refUri": None},
            "patient": {"id": "khavinshankar@sbx"},
            "consentManager": {"id": "sbx"},
            "hip": {"id": "IN3210000017", "name": "Coronasafe Care 01"},
            "hiTypes": [
                "DiagnosticReport",
                "DischargeSummary",
                "HealthDocumentRecord",
                "ImmunizationRecord",
                "OPConsultation",
                "Prescription",
                "WellnessRecord",
            ],
            "permission": {
                "accessMode": "VIEW",
                "dateRange": {
                    "from": "2023-04-11T08:01:32.774",
                    "to": "2023-04-11T08:01:32.774",
                },
                "dataEraseAt": "2023-04-12T08:01:32.774",
                "frequency": {"unit": "HOUR", "value": 1, "repeats": 0},
            },
            "careContexts": [
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "c7134ba2-692a-40f5-a143-d306896436dd",
                },
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "56015494-bac8-486d-85b6-6f67d1708764",
                },
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "140f79f9-4e4e-4bc1-b43e-ebce3c9313a5",
                },
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "90742c64-ac7b-4806-bcb6-2f8418d0bd5b",
                },
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "829cf90f-23c0-4978-be5c-94131be5d2f9",
                },
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "140f79f9-4e4e-4bc1-b43e-ebce3c9313a5",
                },
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "90742c64-ac7b-4806-bcb6-2f8418d0bd5b",
                },
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "829cf90f-23c0-4978-be5c-94131be5d2f9",
                },
                {
                    "patientReference": "1019f565-065a-4287-93fd-a3db4cda7fe4",
                    "careContextReference": "66d32279-b3b3-43e1-971e-eadc5da67e95",
                },
            ],
        },
        "status": "GRANTED",
        "signature": "oB2JZD5CMecjW3y817dYK9pqE36yE3W+jUPtc0vfrPOMEFoYftdXAnNHxBUYZ0FKKIAJGf3erLxkzx0KE+ISFJyXX4U8OzKTBGJEjjJJ7/reDRSWnXS41D89/l8kmZHtVNsqmkje4BMKAjQylw9i8js+VaVpbgC7+NtYcSfLPWqPLnw+ppFJVKM3vrL7/w1UUrrSWB27YOX02XYj4eBtjxiLneG6fTzTT7QqrUtaYYFTU7CY1Ujwx+/q82J1sz3FGszFBe4c+1orqs2jwyLSgu73qmsySdJM1ugjjWs2Y/EBG6SnWjvfz7rvfDZ0KLfcUnWfEU5FVj8umGucAshnXA==",
        "consentId": "0ad38ac1-5f61-480a-b9d6-6ace3e2d2139",
        "grantAcknowledgement": False,
    },
    "requestId": "12fa9195-031a-4d89-b96c-0d7e3cfd009f",
    "timestamp": "2023-04-11T08:01:55.570970194",
}
