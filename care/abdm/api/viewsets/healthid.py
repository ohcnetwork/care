# ABDM HealthID APIs

from datetime import datetime

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.healthid import (
    AadharOtpGenerateRequestPayloadSerializer,
    AadharOtpResendRequestPayloadSerializer,
    CreateHealthIdSerializer,
    GenerateMobileOtpRequestPayloadSerializer,
    HealthIdAuthSerializer,
    HealthIdSerializer,
    QRContentSerializer,
    VerifyDemographicsRequestPayloadSerializer,
    VerifyOtpRequestPayloadSerializer,
)
from care.abdm.models import AbhaNumber
from care.abdm.utils.api_call import AbdmGateway, HealthIdGateway
from care.facility.api.serializers.patient import PatientDetailSerializer
from care.facility.models.facility import Facility
from care.facility.models.patient import PatientConsultation, PatientRegistration
from care.utils.queryset.patient import get_patient_queryset
from config.auth_views import CaptchaRequiredException
from config.ratelimit import ratelimit


# API for Generating OTP for HealthID
class ABDMHealthIDViewSet(GenericViewSet, CreateModelMixin):
    base_name = "healthid"
    model = AbhaNumber
    permission_classes = (IsAuthenticated,)

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

        if ratelimit(request, "generate_aadhaar_otp", [data["aadhaar"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

        if ratelimit(request, "resend_aadhaar_otp", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

        if ratelimit(request, "verify_aadhaar_otp", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

        if ratelimit(request, "generate_mobile_otp", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

        if ratelimit(request, "verify_mobile_otp", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = VerifyOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().verify_mobile_otp(data)
        return Response(response, status=status.HTTP_200_OK)

    def create_abha(self, abha_profile, token):
        abha_object = AbhaNumber.objects.filter(
            abha_number=abha_profile["healthIdNumber"]
        ).first()

        if abha_object:
            return abha_object

        abha_object = AbhaNumber.objects.create(
            abha_number=abha_profile["healthIdNumber"],
            health_id=abha_profile["healthId"],
            name=abha_profile["name"],
            first_name=abha_profile["firstName"],
            middle_name=abha_profile["middleName"],
            last_name=abha_profile["lastName"],
            gender=abha_profile["gender"],
            date_of_birth=str(
                datetime.strptime(
                    f"{abha_profile['yearOfBirth']}-{abha_profile['monthOfBirth']}-{abha_profile['dayOfBirth']}",
                    "%Y-%m-%d",
                )
            )[0:10],
            address=abha_profile["address"] if "address" in abha_profile else "",
            district=abha_profile["districtName"],
            state=abha_profile["stateName"],
            pincode=abha_profile["pincode"],
            email=abha_profile["email"],
            profile_photo=abha_profile["profilePhoto"],
            txn_id=token["txn_id"],
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
        )
        abha_object.save()

        return abha_object

    def add_abha_details_to_patient(self, abha_object, patient_object):
        # patient = PatientRegistration.objects.filter(
        #     abha_number__abha_number=abha_object.abha_number
        # ).first()

        # if patient or patient_object.abha_number:
        #     return False

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

        if ratelimit(request, "create_health_id", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = CreateHealthIdSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        abha_profile = HealthIdGateway().create_health_id(data)

        if "token" not in abha_profile:
            return Response(
                abha_profile,
                status=status.HTTP_400_BAD_REQUEST,
            )

        # have a serializer to verify data of abha_profile
        abha_object = self.create_abha(
            abha_profile,
            {
                "txn_id": data["txnId"],
                "access_token": abha_profile["token"],
                "refresh_token": None,
            },
        )

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

        if ratelimit(
            request, "search_by_health_id", [data["healthId"]], increment=False
        ):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = HealthIdSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().search_by_health_id(data)
        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        # /v1/registration/aadhaar/searchByHealthId
        operation_id="link_via_qr",
        request_body=HealthIdSerializer,
        responses={"200": "{'status': 'boolean'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def link_via_qr(self, request):
        data = request.data

        if ratelimit(request, "link_via_qr", [data["hidn"]], increment=False):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = QRContentSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        dob = datetime.strptime(data["dob"], "%d-%m-%Y").date()

        if "patientId" not in data or data["patientId"] is None:
            patient = PatientRegistration.objects.filter(
                abha_number__abha_number=data["hidn"]
            ).first()
            if patient:
                return Response(
                    {
                        "message": "A patient is already associated with the provided Abha Number"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                "facilityId" not in data
                or not Facility.objects.filter(external_id=data["facilityId"]).first()
            ):
                return Response(
                    {"message": "Enter a valid facilityId"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not HealthIdGateway().verify_demographics(
                data["phr"] or data["hidn"],
                data["name"],
                data["gender"],
                str(dob.year),
            ):
                return Response(
                    {"message": "Please enter valid data"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            patient = PatientRegistration.objects.create(
                facility=Facility.objects.get(external_id=data["facilityId"]),
                name=data["name"],
                gender=1
                if data["gender"] == "M"
                else 2
                if data["gender"] == "F"
                else 3,
                is_antenatal=False,
                phone_number=data["mobile"],
                emergency_phone_number=data["mobile"],
                date_of_birth=dob,
                blood_group="UNK",
                nationality="India",
                address=data["address"],
                pincode=None,
                created_by=None,
                state=None,
                district=None,
                local_body=None,
                ward=None,
            )
        else:
            patient = PatientRegistration.objects.filter(
                external_id=data["patientId"]
            ).first()

            if not patient:
                return Response(
                    {"message": "Enter a valid patientId"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        abha_number = AbhaNumber.objects.create(
            abha_number=data["hidn"],
            health_id=data["phr"],
            name=data["name"],
            gender=data["gender"],
            date_of_birth=str(dob)[0:10],
            address=data["address"],
            district=data["dist name"],
            state=data["state name"],
        )

        abha_number.save()
        patient.abha_number = abha_number
        patient.save()

        AbdmGateway().fetch_modes(
            {
                "healthId": data["phr"] or data["hidn"],
                "name": data["name"],
                "gender": data["gender"],
                "dateOfBirth": str(datetime.strptime(data["dob"], "%d-%m-%Y"))[0:10],
            }
        )

        patient_serialized = PatientDetailSerializer(patient).data
        return Response(patient_serialized, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="get_new_linking_token",
        responses={"200": "{'status': 'boolean'}"},
        tags=["ABDM HealthID"],
    )
    @action(detail=False, methods=["post"])
    def get_new_linking_token(self, request):
        data = request.data

        if ratelimit(request, "get_new_linking_token", [data["patient"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        patient = PatientDetailSerializer(
            PatientRegistration.objects.get(external_id=data["patient"])
        ).data

        AbdmGateway().fetch_modes(
            {
                "healthId": patient["abha_number_object"]["abha_number"],
                "name": patient["abha_number_object"]["name"],
                "gender": patient["abha_number_object"]["gender"],
                "dateOfBirth": str(patient["abha_number_object"]["date_of_birth"]),
            }
        )

        return Response({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"])
    def add_care_context(self, request, *args, **kwargs):
        consultation_id = request.data["consultation"]

        if ratelimit(request, "add_care_context", [consultation_id]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        consultation = PatientConsultation.objects.get(external_id=consultation_id)

        if not consultation:
            return Response(
                {"consultation": "No matching records found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        AbdmGateway().fetch_modes(
            {
                "healthId": consultation.patient.abha_number.health_id,
                # "name": consultation.patient.abha_number.name,
                # "gender": consultation.patient.abha_number.gender,
                # "dateOfBirth": str(consultation.patient.abha_number.date_of_birth),
                # "consultationId": consultation_id,
                "authMode": "DIRECT",
                "purpose": "LINK",
            }
        )

        return Response(status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["POST"])
    def patient_sms_notify(self, request, *args, **kwargs):
        patient_id = request.data["patient"]

        if ratelimit(request, "patient_sms_notify", [patient_id]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        patient = PatientRegistration.objects.filter(external_id=patient_id).first()

        if not patient:
            return Response(
                {"consultation": "No matching records found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = AbdmGateway().patient_sms_notify({"phone": patient.phone_number})

        return Response(response, status=status.HTTP_202_ACCEPTED)

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

        if ratelimit(request, "auth_init", [data["healthid"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

        if ratelimit(request, "confirm_with_aadhaar_otp", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = VerifyOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().confirm_with_aadhaar_otp(data)
        abha_profile = HealthIdGateway().get_profile(response)

        # have a serializer to verify data of abha_profile
        abha_object = self.create_abha(
            abha_profile,
            {
                "access_token": response["token"],
                "refresh_token": response["refreshToken"],
                "txn_id": data["txnId"],
            },
        )

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

        if ratelimit(request, "confirm_with_mobile_otp", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = VerifyOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().confirm_with_mobile_otp(data)
        abha_profile = HealthIdGateway().get_profile(response)

        # have a serializer to verify data of abha_profile
        abha_object = self.create_abha(
            abha_profile,
            {
                "access_token": response["token"],
                "refresh_token": response["refreshToken"],
                "txn_id": data["txnId"],
            },
        )

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

        if ratelimit(request, "confirm_with_demographics", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = VerifyDemographicsRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().confirm_with_demographics(data)
        return Response(response, status=status.HTTP_200_OK)

    ############################################################################################################
    # HealthID V2 APIs
    @swagger_auto_schema(
        # /v2/registration/aadhaar/checkAndGenerateMobileOTP
        operation_id="check_and_generate_mobile_otp",
        request_body=GenerateMobileOtpRequestPayloadSerializer,
        responses={"200": "{'txnId': 'string'}"},
        tags=["ABDM HealthID V2"],
    )
    @action(detail=False, methods=["post"])
    def check_and_generate_mobile_otp(self, request):
        data = request.data

        if ratelimit(request, "check_and_generate_mobile_otp", [data["txnId"]]):
            raise CaptchaRequiredException(
                detail={"status": 429, "detail": "Too Many Requests Provide Captcha"},
                code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = GenerateMobileOtpRequestPayloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        response = HealthIdGateway().check_and_generate_mobile_otp(data)
        return Response(response, status=status.HTTP_200_OK)
