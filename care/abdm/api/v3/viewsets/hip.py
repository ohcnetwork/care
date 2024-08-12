import logging

from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.v3.serializers.hip import (
    HipLinkCareContextConfirmSerializer,
    HipLinkCareContextInitSerializer,
    HipPatientCareContextDiscoverSerializer,
    LinkCarecontextSerializer,
    LinkOnCarecontextSerializer,
    TokenOnGenerateTokenSerializer,
)
from care.abdm.models import AbhaNumber
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
    }

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

        patient = validated_data.get("patient")
        identifiers = [
            *patient.get("verifiedIdentifiers"),
            *patient.get("unverifiedIdentifiers"),
        ]

        health_id_number = filter(lambda x: x.get("type") == "ABHA_NUMBER", identifiers)
        mobile = filter(lambda x: x.get("type") == "MOBILE", identifiers)
        medical_record_id = filter(lambda x: x.get("type") == "MR", identifiers)  # noqa

        patient = PatientRegistration.objects.filter(
            Q(abha_number__abha_number=health_id_number)
            | Q(abha_number__health_id=patient.get("id"))
        ).first()
        matched_by = "ABHA_NUMBER"

        if not patient:
            patient = (
                PatientRegistration.objects.annotate(
                    similarity=TrigramSimilarity("name", patient.get("name"))
                )
                .filter(
                    Q(phone_number=mobile) | Q(phone_number="+91" + mobile),
                    Q(
                        date_of_birth__year__gte=patient.get("yearOfBirth") - 5,
                        date_of_birth__year__lte=patient.get("yearOfBirth") + 5,
                    )
                    | Q(year_of_birth__gte=patient.get("yearOfBirth")) - 5,
                    year_of_birth__lte=patient.get("yearOfBirth") + 5,
                    gender={"M": 1, "F": 2, "O": 3}.get(patient.get("gender"), 3),
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

        reference_id = uuid()
        cache.set(
            "abdm_user_initiated_linking__" + reference_id,
            {
                "reference_id": reference_id,
                # TODO: generate OTP and send it to the patient
                "otp": "000000",
                # TODO: consider abha_address is not the preferred abha address
                "abha_address": validated_data.get("abhaAddress"),
            },
        )

        GatewayService.user_initiated_linking__patient__care_context__on_init(
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

        if not cached_data.get("otp") == validated_data.get("confirmation").get("otp"):
            logger.warning(
                f"Invalid OTP: {validated_data.get('confirmation').get('otp')} for Reference ID: {validated_data.get('confirmation').get('linkRefNumber')}"
            )

            return Response(status=status.HTTP_400_BAD_REQUEST)

        patient = PatientRegistration.objects.filter(
            abha_number__health_id=cached_data.get("abha_address")
        ).first()
        GatewayService.user_initiated_linking__patient__care_context__on_confirm(
            {
                "transaction_id": str(validated_data.get("transactionId")),
                "request_id": request.headers.get("REQUEST-ID"),
                "patient": patient,
            }
        )

        Response(status=status.HTTP_202_ACCEPTED)
