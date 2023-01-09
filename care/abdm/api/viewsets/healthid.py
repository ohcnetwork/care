# ABDM HealthID APIs

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.healthid import (
    AadharOtpGenerateRequestPayloadSerializer,
    AadharOtpResendRequestPayloadSerializer,
    CreateHealthIdSerializer,
    GenerateMobileOtpRequestPayloadSerializer,
    HealthIdAuthSerializer,
    HealthIdSerializer,
    VerifyOtpRequestPayloadSerializer,
)
from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import HealthIdGateway, HealthIdGatewayV2
from care.utils.queryset.patient import get_patient_queryset


# API for Generating OTP for HealthID
class ABDMHealthIDViewSet(GenericViewSet, CreateModelMixin):
    base_name = "healthid"
    model = AbhaNumber

    # TODO: Ratelimiting for all endpoints that generate OTP's / Critical API's
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
        response = HealthIdGatewayV2().generate_aadhaar_otp(data)
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
        response = HealthIdGatewayV2().verify_document_mobile_otp(data)
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

    def add_abha_details_to_patient(self, data, patient_obj):
        abha_object = AbhaNumber.objects.filter(
            abha_number=data["healthIdNumber"]
        ).first()
        if abha_object:
            # Flow when abha number exists in db somehow!
            return False
        else:
            # Create abha number flow
            abha_object = AbhaNumber()
            abha_object.abha_number = data["healthIdNumber"]
            abha_object.email = data["email"]
            abha_object.first_name = data["firstName"]
            abha_object.health_id = data["healthId"]
            abha_object.last_name = data["lastName"]
            abha_object.middle_name = data["middleName"]
            abha_object.profile_photo = data["profilePhoto"]
            abha_object.save()

        patient_obj.abha_number = abha_object
        patient_obj.save()
        return True

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
        patient_id = data.pop("patientId")
        allowed_patients = get_patient_queryset(request.user)
        patient_obj = allowed_patients.filter(external_id=patient_id).first()
        if not patient_obj:
            raise ValidationError({"patient": "Not Found"})
        response = HealthIdGateway().create_health_id(data)
        abha_object = AbhaNumber.objects.filter(
            abha_number=response["healthIdNumber"]
        ).first()
        if abha_object:
            # Flow when abha number exists in db somehow!
            pass
        else:
            # Create abha number flow
            abha_object = AbhaNumber()
            abha_object.abha_number = response["healthIdNumber"]
            abha_object.email = response["email"]
            abha_object.first_name = response["firstName"]
            abha_object.health_id = response["healthId"]
            abha_object.last_name = response["lastName"]
            abha_object.middle_name = response["middleName"]
            abha_object.profile_photo = response["profilePhoto"]
            abha_object.txn_id = response["healthIdNumber"]
            abha_object.access_token = response["token"]
            abha_object.refresh_token = data["txnId"]
            abha_object.save()

        patient_obj.abha_number = abha_object
        patient_obj.save()
        return Response(response, status=status.HTTP_200_OK)

    # APIs to Find & Link Existing HealthID
    # searchByHealthId
    @swagger_auto_schema(
        # /v1/registration/aadhaar/searchByHealthId
        operation_id="search_by_health_id",
        request_body=HealthIdSerializer,
        responses={"200": "{'status': 'boolean'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def search_by_health_id(self, request):
        data = request.data
        serializer = HealthIdSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().search_by_health_id(data)
        return Response(response, status=status.HTTP_200_OK)

    # auth/init
    @swagger_auto_schema(
        # /v1/auth/init
        operation_id="auth_init",
        request_body=HealthIdAuthSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def auth_init(self, request):
        data = request.data
        serializer = HealthIdAuthSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().auth_init(data)
        return Response(response, status=status.HTTP_200_OK)

    # /v1/auth/confirmWithAadhaarOtp
    @swagger_auto_schema(
        operation_id="confirm_with_aadhaar_otp",
        request_body=VerifyOtpRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def confirm_with_aadhaar_otp(self, request):
        data = request.data
        serializer = VerifyOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().confirm_with_aadhaar_otp(data)
        abha_object = HealthIdGateway().get_profile(response)

        patient_id = data.pop("patientId")
        allowed_patients = get_patient_queryset(request.user)
        patient_obj = allowed_patients.filter(external_id=patient_id).first()
        if not patient_obj:
            raise ValidationError({"patient": "Not Found"})

        if self.add_abha_details_to_patient(
            abha_object,
            patient_obj,
        ):
            return Response(abha_object, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "ABHA NUmber / Health ID already Exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # /v1/auth/confirmWithMobileOtp
    @swagger_auto_schema(
        operation_id="confirm_with_mobile_otp",
        request_body=VerifyOtpRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def confirm_with_mobile_otp(self, request):
        data = request.data
        serializer = VerifyOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().confirm_with_mobile_otp(data)
        abha_object = HealthIdGateway().get_profile(response)

        patient_id = data.pop("patientId")
        allowed_patients = get_patient_queryset(request.user)
        patient_obj = allowed_patients.filter(external_id=patient_id).first()
        if not patient_obj:
            raise ValidationError({"patient": "Not Found"})

        if self.add_abha_details_to_patient(
            abha_object,
            patient_obj,
        ):
            return Response(abha_object, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "ABHA NUmber / Health ID already Exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    ############################################################################################################
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
