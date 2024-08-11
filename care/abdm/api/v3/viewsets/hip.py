import logging

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.v3.serializers.hip import (
    LinkCarecontextSerializer,
    LinkOnCarecontextSerializer,
    TokenOnGenerateTokenSerializer,
)
from care.abdm.models import AbhaNumber
from care.abdm.service.v3.gateway import GatewayService
from care.facility.models import PatientConsultation
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
                "consultations": validated_data["consultations"],
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
            "abdm_link_token__" + str(validated_data["response"]["requestId"])
        )

        if not cached_data:
            logger.warning(
                f"Request ID: {str(validated_data['response']['requestId'])} not found in cache"
            )

            return Response(status=status.HTTP_404_NOT_FOUND)

        if cached_data["purpose"] == "LINK_CARECONTEXT":
            abha_number = AbhaNumber.objects.filter(
                abha_number=cached_data["abha_number"]
            ).first()

            if not abha_number:
                logger.warning(
                    f"ABHA Number: {cached_data['abha_number']} not found in the database"
                )

                return Response(status=status.HTTP_404_NOT_FOUND)

            GatewayService.link__carecontext(
                {
                    "consultations": PatientConsultation.objects.filter(
                        external_id__in=cached_data["consultations"]
                    ),
                    "link_token": validated_data.get("linkToken"),
                }
            )

        return Response(status=status.HTTP_202_ACCEPTED)

    def link__on_carecontext(self, request):
        self.validate_request(request)

        # TODO: handle failed link requests

        return Response(status=status.HTTP_202_ACCEPTED)
