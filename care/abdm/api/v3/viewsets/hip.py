import logging
from functools import reduce

from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.v3.serializers.hip import (
    ConsentRequestHipNotifySerializer,
    HipHealthInformationRequestSerializer,
    HipLinkCareContextConfirmSerializer,
    HipLinkCareContextInitSerializer,
    HipPatientCareContextDiscoverSerializer,
    LinkCarecontextSerializer,
    LinkOnCarecontextSerializer,
    TokenOnGenerateTokenSerializer,
)
from care.abdm.models import AbhaNumber, ConsentArtefact
from care.abdm.service.helper import uuid
from care.abdm.service.v3.gateway import GatewayService
from care.facility.models import PatientConsultation, PatientRegistration
from config.authentication import ABDMAuthentication

logger = logging.getLogger(__name__)


class HIPViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)

    serializer_action_classes = {"link__carecontext": LinkCarecontextSerializer}

    def get_serializer_class(self):
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return super().get_serializer_class()

    def validate_request(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return serializer.validated_data

    @action(detail=False, methods=["POST"])
    def link__carecontext(self, request):
        validated_data = self.validate_request(request)

        GatewayService.link__carecontext(
            {
                "consultations": validated_data.get("consultations"),
                "link_token": None,
            }
        )

        return Response(
            {
                "detail": "Linking request has been raised, you will be notified through abha app once the process is completed"
            },
            status=status.HTTP_202_ACCEPTED,
        )


class HIPCallbackViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)
    authentication_classes = [ABDMAuthentication]

    serializer_action_classes = {
        "token__on_generate_token": TokenOnGenerateTokenSerializer,
        "link__on_carecontext": LinkOnCarecontextSerializer,
        "hip__patient__care_context__discover": HipPatientCareContextDiscoverSerializer,
        "hip__link__care_context__init": HipLinkCareContextInitSerializer,
        "hip__link__care_context__confirm": HipLinkCareContextConfirmSerializer,
        "consent__request__hip__notify": ConsentRequestHipNotifySerializer,
        "hip__health_information__request": HipHealthInformationRequestSerializer,
    }

    def get_patient_by_abha_id(self, abha_id: str):
        patient = PatientRegistration.objects.filter(
            Q(abha_number__abha_number=abha_id) | Q(abha_number__health_id=abha_id)
        ).first()

        if not patient and "@" in abha_id:
            # TODO: get abha number using gateway api and search patient
            pass

        return patient

    def get_serializer_class(self):
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return super().get_serializer_class()

    def validate_request(self, request):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exception:
            logger.warning(
                f"Validation failed for request data: {request.data}, "
                f"Path: {request.path}, Method: {request.method}, "
                f"Error details: {str(exception)}"
            )

            raise exception

        return serializer.validated_data

    def token__on_generate_token(self, request):
        validated_data = self.validate_request(request)

        cached_data = cache.get(
            "abdm_link_token__" + str(validated_data.get("response").get("requestId"))
        )

        if not cached_data:
            logger.warning(
                f"Request ID: {str(validated_data.get('response').get('requestId'))} not found in cache"
            )

            return Response(status=status.HTTP_404_NOT_FOUND)

        if cached_data.get("purpose") == "LINK_CARECONTEXT":
            abha_number = AbhaNumber.objects.filter(
                abha_number=cached_data.get("abha_number")
            ).first()

            if not abha_number:
                logger.warning(
                    f"ABHA Number: {cached_data.get('abha_number')} not found in the database"
                )

                return Response(status=status.HTTP_404_NOT_FOUND)

            GatewayService.link__carecontext(
                {
                    "consultations": PatientConsultation.objects.filter(
                        external_id__in=cached_data.get("consultations", [])
                    ),
                    "link_token": validated_data.get("linkToken"),
                }
            )

        return Response(status=status.HTTP_202_ACCEPTED)

    def link__on_carecontext(self, request):
        self.validate_request(request)

        # TODO: handle failed link requests

        return Response(status=status.HTTP_202_ACCEPTED)

    def hip__patient__care_context__discover(self, request):
        validated_data = self.validate_request(request)

        patient_data = validated_data.get("patient")
        identifiers = [
            *patient_data.get("verifiedIdentifiers"),
            *patient_data.get("unverifiedIdentifiers"),
        ]

        health_id_number = next(
            filter(lambda x: x.get("type") == "ABHA_NUMBER", identifiers), {}
        ).get("value")
        patient = PatientRegistration.objects.filter(
            Q(abha_number__abha_number=health_id_number)
            | Q(abha_number__health_id=patient_data.get("id"))
        ).first()
        matched_by = "ABHA_NUMBER"

        if not patient:
            mobile = next(
                filter(lambda x: x.get("type") == "MOBILE", identifiers), {}
            ).get("value")
            patient = (
                PatientRegistration.objects.annotate(
                    similarity=TrigramSimilarity("name", patient_data.get("name"))
                )
                .filter(
                    Q(phone_number=mobile) | Q(phone_number="+91" + mobile),
                    Q(
                        date_of_birth__year__gte=patient_data.get("yearOfBirth") - 5,
                        date_of_birth__year__lte=patient_data.get("yearOfBirth") + 5,
                    )
                    | Q(year_of_birth__gte=patient_data.get("yearOfBirth")) - 5,
                    year_of_birth__lte=patient_data.get("yearOfBirth") + 5,
                    gender={"M": 1, "F": 2, "O": 3}.get(patient_data.get("gender"), 3),
                    similarity__gt=0.3,
                )
                .order_by("-similarity")
                .first()
            )
            matched_by = "MOBILE"

        if not patient:
            # TODO: handle MR matching
            pass

        GatewayService.user_initiated_linking__patient__care_context__on_discover(
            {
                "transaction_id": str(validated_data.get("transactionId")),
                "request_id": request.headers.get("REQUEST-ID"),
                "patient": patient,
                "matched_by": [matched_by],
            }
        )

        return Response(status=status.HTTP_200_OK)

    def hip__link__care_context__init(self, request):
        validated_data = self.validate_request(request)
        care_contexts = reduce(
            lambda acc, patient: acc
            + [
                {
                    "patient_reference": patient.get("referenceNumber"),
                    "care_context_reference": context.get("referenceNumber"),
                    "hi_type": patient.get("hiType"),
                }
                for context in patient.get("careContexts", [])
            ],
            validated_data.get("patient", []),
            [],
        )

        reference_id = uuid()
        cache.set(
            "abdm_user_initiated_linking__" + reference_id,
            {
                "reference_id": reference_id,
                # TODO: generate OTP and send it to the patient
                "otp": "000000",
                "abha_address": validated_data.get("abhaAddress"),
                "care_contexts": care_contexts,
            },
        )

        GatewayService.user_initiated_linking__link__care_context__on_init(
            {
                "transaction_id": str(validated_data.get("transactionId")),
                "request_id": request.headers.get("REQUEST-ID"),
                "reference_id": reference_id,
            }
        )

        return Response(status=status.HTTP_200_OK)

    def hip__link__care_context__confirm(self, request):
        validated_data = self.validate_request(request)

        cached_data = cache.get(
            "abdm_user_initiated_linking__"
            + validated_data.get("confirmation").get("linkRefNumber")
        )

        if not cached_data:
            logger.warning(
                f"Reference ID: {validated_data.get('confirmation').get('linkRefNumber')} not found in cache"
            )

            return Response(status=status.HTTP_404_NOT_FOUND)

        if not cached_data.get("otp") == validated_data.get("confirmation").get(
            "token"
        ):
            logger.warning(
                f"Invalid OTP: {validated_data.get('confirmation').get('token')} for Reference ID: {validated_data.get('confirmation').get('linkRefNumber')}"
            )

            return Response(status=status.HTTP_400_BAD_REQUEST)

        consultation_ids = list(
            map(
                lambda x: x.get("care_context_reference"),
                cached_data.get("care_contexts"),
            )
        )
        consultations = PatientConsultation.objects.filter(
            external_id__in=consultation_ids,
        )

        GatewayService.user_initiated_linking__link__care_context__on_confirm(
            {
                "request_id": request.headers.get("REQUEST-ID"),
                "consultations": consultations,
            }
        )

        return Response(status=status.HTTP_202_ACCEPTED)

    def consent__request__hip__notify(self, request):
        validated_data = self.validate_request(request)

        notification = validated_data.get("notification")
        consent_detail = notification.get("consentDetail")
        permission = consent_detail.get("permission")
        frequency = permission.get("frequency")

        patient = self.get_patient_by_abha_id(consent_detail.get("patient").get("id"))

        if not patient:
            logger.warning(
                f"Patient with ABHA ID: {consent_detail.get('patient').get('id')} not found in the database"
            )

            return Response(status=status.HTTP_404_NOT_FOUND)

        ConsentArtefact.objects.update_or_create(
            consent_id=notification.get("consentId"),
            defaults={
                "patient_abha": patient.abha_number,
                "care_contexts": consent_detail.get("careContexts"),
                "status": notification.get("status"),
                "purpose": consent_detail.get("purpose").get("code"),
                "hi_types": consent_detail.get("hiTypes"),
                "hip": consent_detail.get("hip").get("id"),
                "cm": consent_detail.get("consentManager").get("id"),
                "requester": request.user,
                "access_mode": permission.get("accessMode"),
                "from_time": permission.get("dateRange").get("fromTime"),
                "to_time": permission.get("dateRange").get("toTime"),
                "expiry": permission.get("dataEraseAt"),
                "frequency_unit": frequency.get("unit"),
                "frequency_value": frequency.get("value"),
                "frequency_repeats": frequency.get("repeats"),
                "signature": notification.get("signature"),
            },
        )

        GatewayService.consent__request__hip__on_notify(
            {
                "consent_id": str(notification.get("consentId")),
                "request_id": request.headers.get("REQUEST-ID"),
            }
        )

        return Response(status=status.HTTP_202_ACCEPTED)

    def hip__health_information__request(self, request):
        validated_data = self.validate_request(request)

        hi_request = validated_data.get("hiRequest")
        key_material = hi_request.get("keyMaterial")

        consent = ConsentArtefact.objects.filter(
            consent_id=hi_request.get("consent").get("id")
        ).first()

        if not consent:
            logger.warning(
                f"Consent with ID: {hi_request.get('consent').get('id')} not found in the database"
            )

            return Response(status=status.HTTP_404_NOT_FOUND)

        GatewayService.data_flow__health_information__hip__on_request(
            {
                "request_id": request.headers.get("REQUEST-ID"),
                "transaction_id": str(validated_data.get("transactionId")),
            }
        )

        consultations = PatientConsultation.objects.filter(
            external_id__in=list(
                map(lambda x: x.get("careContextReference"), consent.care_contexts)
            )
        )

        try:
            GatewayService.data_flow__health_information__transfer(
                {
                    "transaction_id": str(validated_data.get("transactionId")),
                    "consultations": consultations,
                    "consent": consent,
                    "url": hi_request.get("dataPushUrl"),
                    "key_material__crypto_algorithm": key_material.get("cryptoAlg"),
                    "key_material__curve": key_material.get("curve"),
                    "key_material__public_key": key_material.get("dhPublicKey").get(
                        "keyValue"
                    ),
                    "key_material__nonce": key_material.get("nonce"),
                }
            )

            GatewayService.data_flow__health_information__notify(
                {
                    "consent_id": str(consent.consent_id),
                    "transaction_id": str(validated_data.get("transactionId")),
                    "notifier__type": "HIP",
                    "notifier__id": request.headers.get("X-HIP-ID"),
                    "status": "TRANSFERRED",
                    "hip_id": request.headers.get("X-HIP-ID"),
                    "consultation_ids": list(
                        map(lambda x: str(x.external_id), consultations)
                    ),
                }
            )
        except Exception as exception:
            logger.error(
                f"Error occurred while transferring health information: {str(exception)}"
            )

            GatewayService.data_flow__health_information__notify(
                {
                    "consent_id": str(consent.consent_id),
                    "transaction_id": str(validated_data.get("transactionId")),
                    "notifier__type": "HIP",
                    "notifier__id": request.headers.get("X-HIP-ID"),
                    "status": "FAILED",
                    "hip_id": request.headers.get("X-HIP-ID"),
                    "consultation_ids": list(
                        map(lambda x: str(x.external_id), consultations)
                    ),
                }
            )

        return Response(status=status.HTTP_202_ACCEPTED)
