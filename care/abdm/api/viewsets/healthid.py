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
    VerifyDemographicsRequestPayloadSerializer,
    VerifyOtpRequestPayloadSerializer,
)
from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import HealthIdGateway, HealthIdGatewayV2
from care.facility.models.patient import PatientRegistration
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
        response = HealthIdGateway().verify_aadhaar_otp(
            data
        )  # HealthIdGatewayV2().verify_document_mobile_otp(data)
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

    def create_abha(self, abha_profile):
        abha_object = AbhaNumber.objects.filter(
            abha_number=abha_profile["healthIdNumber"]
        ).first()

        if abha_object:
            return abha_object

        abha_object = AbhaNumber()
        abha_object.abha_number = abha_profile["healthIdNumber"]
        abha_object.email = abha_profile["email"]
        abha_object.first_name = abha_profile["firstName"]
        abha_object.health_id = abha_profile["healthId"]
        abha_object.last_name = abha_profile["lastName"]
        abha_object.middle_name = abha_profile["middleName"]
        abha_object.profile_photo = abha_profile["profilePhoto"]
        abha_object.txn_id = abha_profile["healthIdNumber"]
        abha_object.save()

        return abha_object

    def add_abha_details_to_patient(self, abha_object, patient_object):
        patient = PatientRegistration.objects.filter(
            abha_number__abha_number=abha_object.abha_number
        ).first()

        if patient or patient_object.abha_number:
            return False

        patient_object.abha_number = abha_object
        patient_object.save()
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
        abha_profile = HealthIdGateway().create_health_id(data)

        # have a serializer to verify data of abha_profile
        abha_object = self.create_abha(abha_profile)

        if "patientId" in data:
            patient_id = data.pop("patientId")
            allowed_patients = get_patient_queryset(request.user)
            patient_obj = allowed_patients.filter(external_id=patient_id).first()
            if not patient_obj:
                raise ValidationError({"patient": "Not Found"})

            if not self.add_abha_details_to_patient(
                abha_object,
                patient_obj,
            ):
                return Response(
                    {"message": "Failed to add abha Number to the patient"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"id": abha_object.external_id, "abha_profile": abha_profile},
            status=status.HTTP_200_OK,
        )

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
        abha_profile = HealthIdGateway().get_profile(response)

        # have a serializer to verify data of abha_profile
        abha_object = self.create_abha(abha_profile)

        if "patientId" in data:
            patient_id = data.pop("patientId")
            allowed_patients = get_patient_queryset(request.user)
            patient_obj = allowed_patients.filter(external_id=patient_id).first()
            if not patient_obj:
                raise ValidationError({"patient": "Not Found"})

            if not self.add_abha_details_to_patient(
                abha_object,
                patient_obj,
            ):
                return Response(
                    {"message": "Failed to add abha Number to the patient"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"id": abha_object.external_id, "abha_profile": abha_profile},
            status=status.HTTP_200_OK,
        )

    # /v1/auth/confirmWithMobileOtp
    @swagger_auto_schema(
        operation_id="confirm_with_mobile_otp",
        request_body=VerifyOtpRequestPayloadSerializer,
        # responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def confirm_with_mobile_otp(self, request):
        data = request.data
        serializer = VerifyOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().confirm_with_mobile_otp(data)
        abha_profile = HealthIdGateway().get_profile(response)

        # have a serializer to verify data of abha_profile
        abha_object = self.create_abha(abha_profile)

        if "patientId" in data:
            patient_id = data.pop("patientId")
            allowed_patients = get_patient_queryset(request.user)
            patient_obj = allowed_patients.filter(external_id=patient_id).first()
            if not patient_obj:
                raise ValidationError({"patient": "Not Found"})

            if not self.add_abha_details_to_patient(
                abha_object,
                patient_obj,
            ):
                return Response(
                    {"message": "Failed to add abha Number to the patient"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"id": abha_object.external_id, "abha_profile": abha_profile},
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_id="confirm_with_demographics",
        request_body=VerifyDemographicsRequestPayloadSerializer,
        responses={"200": "{'status': true}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def confirm_with_demographics(self, request):
        data = request.data
        serializer = VerifyDemographicsRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().confirm_with_demographics(data)
        return Response(response, status=status.HTTP_200_OK)

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
