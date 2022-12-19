# ABDM HealthID APIs

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.healthid import (
    AadharOtpGenerateRequestPayloadSerializer,
    AadharOtpResendRequestPayloadSerializer,
    CreateHealthIdSerializer,
    GenerateMobileOtpRequestPayloadSerializer,
    VerifyOtpRequestPayloadSerializer,
)
from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import HealthIdGateway


# API for Generating OTP for HealthID
class ABDMHealthIDViewSet(GenericViewSet, CreateModelMixin):
    base_name = "healthid"
    model = AbhaNumber
    # Override Create method
    # def create(self, request, *args, **kwargs):

    @swagger_auto_schema(
        operation_id="generate_aadhaar_otp",
        request_body=AadharOtpGenerateRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def generate_aadhaar_otp(self, request):
        data = request.data
        serializer = AadharOtpGenerateRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().generate_aadhaar_otp(data)
        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        # /v1/registration/aadhaar/resendAadhaarOtp
        operation_id="resend_aadhaar_otp",
        request_body=AadharOtpResendRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def resend_aadhaar_otp(self, request):
        data = request.data
        serializer = AadharOtpResendRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().resend_aadhaar_otp(data)
        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        # /v1/registration/aadhaar/verifyAadhaarOtp
        operation_id="verify_aadhaar_otp",
        request_body=VerifyOtpRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def verify_aadhaar_otp(self, request):
        data = request.data
        serializer = VerifyOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().verify_aadhaar_otp(data)
        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        # /v1/registration/aadhaar/generateMobileOTP
        operation_id="generate_mobile_otp",
        request_body=GenerateMobileOtpRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def generate_mobile_otp(self, request):
        data = request.data
        serializer = GenerateMobileOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().generate_mobile_otp(data)
        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        # /v1/registration/aadhaar/verifyMobileOTP
        operation_id="verify_mobile_otp",
        request_body=VerifyOtpRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def verify_mobile_otp(self, request):
        data = request.data
        serializer = VerifyOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().verify_mobile_otp(data)
        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        # /v1/registration/aadhaar/createHealthId
        operation_id="create_health_id",
        request_body=CreateHealthIdSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def create_health_id(self, request):
        data = request.data
        serializer = CreateHealthIdSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().create_health_id(data)
        print(response.status_code)
        return Response(response, status=status.HTTP_200_OK)

    # HealthID V2 APIs
    @swagger_auto_schema(
        # /v1/registration/aadhaar/checkAndGenerateMobileOTP
        operation_id="check_and_generate_mobile_otp",
        request_body=GenerateMobileOtpRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID V2"],
    )
    @action(detail=False, methods=["post"])
    def check_and_generate_mobile_otp(self, request):
        data = request.data
        serializer = GenerateMobileOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().check_and_generate_mobile_otp(data)
        return Response(response, status=status.HTTP_200_OK)
