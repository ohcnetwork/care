import json
from datetime import datetime, timedelta

from django.core.cache import cache
from rest_framework import status
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.abdm.utils.api_call import AbdmGateway
from care.abdm.utils.cipher import Cipher
from care.abdm.utils.fhir import Fhir
from care.facility.models.patient import PatientRegistration
from care.facility.models.patient_consultation import PatientConsultation
from config.authentication import ABDMAuthentication


class OnFetchView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        data = request.data

        try:
            AbdmGateway().init(data["resp"]["requestId"])
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({}, status=status.HTTP_202_ACCEPTED)


class OnInitView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        data = request.data

        AbdmGateway().confirm(data["auth"]["transactionId"], data["resp"]["requestId"])

        return Response({}, status=status.HTTP_202_ACCEPTED)


class OnConfirmView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        data = request.data

        if "validity" in data["auth"]:
            if data["auth"]["validity"]["purpose"] == "LINK":
                AbdmGateway().add_care_context(
                    data["auth"]["accessToken"],
                    data["resp"]["requestId"],
                )
            else:
                AbdmGateway().save_linking_token(
                    data["auth"]["patient"],
                    data["auth"]["accessToken"],
                    data["resp"]["requestId"],
                )
        else:
            AbdmGateway().save_linking_token(
                data["auth"]["patient"],
                data["auth"]["accessToken"],
                data["resp"]["requestId"],
            )
            AbdmGateway().add_care_context(
                data["auth"]["accessToken"],
                data["resp"]["requestId"],
            )

        return Response({}, status=status.HTTP_202_ACCEPTED)


class AuthNotifyView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        data = request.data

        if data["auth"]["status"] != "GRANTED":
            return

        AbdmGateway.auth_on_notify({"request_id": data["auth"]["transactionId"]})

        # AbdmGateway().add_care_context(
        #     data["auth"]["accessToken"],
        #     data["resp"]["requestId"],
        # )


class OnAddContextsView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        return Response({}, status=status.HTTP_202_ACCEPTED)


class DiscoverView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

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
                if identifier["value"] is None:
                    continue

                # if identifier["type"] == "MOBILE":
                #     matched_by.append(identifier["value"])
                #     mobile = identifier["value"].replace("+91", "").replace("-", "")
                #     patients = patients.filter(
                #         Q(phone_number=f"+91{mobile}") | Q(phone_number=mobile)
                #     )

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

        # TODO: also filter by demographics
        patient = patients.last()

        if not patient:
            return Response(
                "No matching records found, need more data",
                status=status.HTTP_404_NOT_FOUND,
            )

        AbdmGateway().on_discover(
            {
                "request_id": data["requestId"],
                "transaction_id": data["transactionId"],
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
                "matched_by": matched_by,
            }
        )
        return Response({}, status=status.HTTP_202_ACCEPTED)


class LinkInitView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

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
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        data = request.data

        # TODO: verify otp

        patient = get_object_or_404(
            PatientRegistration.objects.filter(
                external_id=data["confirmation"]["linkRefNumber"]
            )
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
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        data = request.data

        cache.set(data["notification"]["consentId"], json.dumps(data))

        AbdmGateway().on_notify(
            {
                "request_id": data["requestId"],
                "consent_id": data["notification"]["consentId"],
            }
        )
        return Response({}, status=status.HTTP_202_ACCEPTED)


class RequestDataView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    def post(self, request, *args, **kwargs):
        data = request.data

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
            return Response({}, status=status.HTTP_202_ACCEPTED)
            return Response(
                on_data_request_response, status=status.HTTP_400_BAD_REQUEST
            )

        cipher = Cipher(
            data["hiRequest"]["keyMaterial"]["dhPublicKey"]["keyValue"],
            data["hiRequest"]["keyMaterial"]["nonce"],
        )

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
                                                PatientConsultation.objects.filter(
                                                    external_id=context[
                                                        "careContextReference"
                                                    ]
                                                ).first()
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
                    "nonce": cipher.internal_nonce,
                },
            }
        )

        try:
            AbdmGateway().data_notify(
                {
                    "health_id": consent["notification"]["consentDetail"]["patient"][
                        "id"
                    ],
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
        except Exception as e:
            return Response(
                {
                    "detail": "Failed to notify (health-information/notify)",
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({}, status=status.HTTP_202_ACCEPTED)
