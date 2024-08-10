from datetime import datetime

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.serializers.abhanumber import AbhaNumberSerializer
from care.abdm.api.v3.serializers.health_id import (
    AbhaCreateAbhaAddressSuggestionSerializer,
    AbhaCreateEnrolAbhaAddressSerializer,
    AbhaCreateLinkMobileNumberSerializer,
    AbhaCreateSendAadhaarOtpSerializer,
    AbhaCreateVerifyAadhaarOtpSerializer,
    AbhaCreateVerifyMobileOtpSerializer,
    AbhaLoginCheckAuthMethodsSerializer,
    AbhaLoginSendOtpSerializer,
    AbhaLoginVerifyOtpSerializer,
    LinkAbhaNumberAndPatientSerializer,
)
from care.abdm.models import AbhaNumber
from care.abdm.service.v3.health_id import HealthIdService
from care.facility.api.serializers.patient import PatientDetailSerializer
from care.utils.queryset.patient import get_patient_queryset


class HealthIdViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)

    serializer_action_classes = {
        "abha_create__send_aadhaar_otp": AbhaCreateSendAadhaarOtpSerializer,
        "abha_create__verify_aadhaar_otp": AbhaCreateVerifyAadhaarOtpSerializer,
        "abha_create__link_mobile_number": AbhaCreateLinkMobileNumberSerializer,
        "abha_create__verify_mobile_otp": AbhaCreateVerifyMobileOtpSerializer,
        "abha_create__abha_address_suggestion": AbhaCreateAbhaAddressSuggestionSerializer,
        "abha_create__enrol_abha_address": AbhaCreateEnrolAbhaAddressSerializer,
        "abha_login__send_otp": AbhaLoginSendOtpSerializer,
        "abha_login__verify_otp": AbhaLoginVerifyOtpSerializer,
        "abha_login__check_auth_methods": AbhaLoginCheckAuthMethodsSerializer,
        "link_abha_number_and_patient": LinkAbhaNumberAndPatientSerializer,
    }

    def get_serializer_class(self):
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return super().get_serializer_class()

    def validate_request(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return serializer.validated_data

    @action(detail=False, methods=["post"])
    def link_abha_number_and_patient(self, request):
        validated_data = self.validate_request(request)

        patient_queryset = get_patient_queryset(request.user)
        patient = patient_queryset.filter(
            external_id=validated_data.get("patient")
        ).first()

        if not patient:
            return Response(
                {
                    "detail": "Patient not found or you do not have permission to access the patient",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if patient.abha_number:
            return Response(
                {
                    "detail": "Patient already linked to an ABHA Number",
                    "patient": PatientDetailSerializer(patient).data,
                    "abha_number": AbhaNumberSerializer(patient.abha_number).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        abha_number = AbhaNumber.objects.filter(
            external_id=validated_data.get("abha_number")
        ).first()

        if not abha_number:
            return Response(
                {
                    "detail": "ABHA Number not found",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(abha_number, "patientregistration"):
            return Response(
                {
                    "detail": "ABHA Number already linked to a patient",
                    "patient": PatientDetailSerializer(
                        abha_number.patientregistration
                    ).data,
                    "abha_number": AbhaNumberSerializer(abha_number).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient.abha_number = abha_number
        patient.save()

        return Response(
            {
                "detail": "Patient linked successfully",
                "patient": PatientDetailSerializer(patient).data,
                "abha_number": AbhaNumberSerializer(abha_number).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_create__send_aadhaar_otp(self, request):
        validated_data = self.validate_request(request)

        result = HealthIdService.enrollment__request__otp(
            {
                "scope": ["abha-enrol"],
                "transaction_id": "",
                "type": "aadhaar",
                "value": validated_data.get("aadhaar"),
            }
        )

        return Response(
            {
                "transaction_id": result.get("txnId"),
                "detail": result.get("message"),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_create__verify_aadhaar_otp(self, request):
        validated_data = self.validate_request(request)

        result = HealthIdService.enrollment__enrol__byAadhaar(
            {
                "transaction_id": str(validated_data.get("transaction_id")),
                "otp": validated_data.get("otp"),
                "mobile": validated_data.get("mobile"),
            }
        )

        abha_profile = result.get("ABHAProfile")
        token = result.get("tokens")
        (abha_number, created) = AbhaNumber.objects.update_or_create(
            abha_number=abha_profile.get("ABHANumber"),
            defaults={
                "abha_number": abha_profile.get("ABHANumber"),
                "health_id": abha_profile.get("phrAddress", [None])[0],
                "name": " ".join(
                    list(
                        filter(
                            lambda x: x.strip(),
                            [
                                abha_profile.get("firstName"),
                                abha_profile.get("middleName"),
                                abha_profile.get("lastName"),
                            ],
                        )
                    )
                ),
                "first_name": abha_profile.get("firstName"),
                "middle_name": abha_profile.get("middleName"),
                "last_name": abha_profile.get("lastName"),
                "gender": abha_profile.get("gender"),
                "date_of_birth": abha_profile.get("dob"),
                "address": abha_profile.get("address"),
                "district": abha_profile.get("districtName"),
                "state": abha_profile.get("stateName"),
                "pincode": abha_profile.get("pinCode"),
                "email": abha_profile.get("email"),
                # "mobile": abha_profile.get("mobile"),
                "profile_photo": abha_profile.get("photo"),
                "new": result.get("isNew"),
                "txn_id": result.get("txnId"),
                "access_token": token.get("token"),
                "refresh_token": token.get("refreshToken"),
            },
        )

        return Response(
            {
                "transaction_id": result.get("txnId"),
                "detail": result.get("message"),
                "abha_number": AbhaNumberSerializer(abha_number).data,
                "created": created,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_create__link_mobile_number(self, request):
        validated_data = self.validate_request(request)

        result = HealthIdService.enrollment__request__otp(
            {
                "scope": ["abha-enrol", "mobile-verify"],
                "type": "mobile",
                "value": validated_data.get("mobile"),
                "transaction_id": str(validated_data.get("transaction_id")),
            }
        )

        return Response(
            {
                "transaction_id": result.get("txnId"),
                "detail": result.get("message"),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_create__verify_mobile_otp(self, request):
        validated_data = self.validate_request(request)

        result = HealthIdService.enrollment__auth__byAbdm(
            {
                "scope": ["abha-enrol", "mobile-verify"],
                "transaction_id": str(validated_data.get("transaction_id")),
                "otp": validated_data.get("otp"),
            }
        )

        return Response(
            {
                "transaction_id": result.get("txnId"),
                "detail": result.get("message"),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_create__abha_address_suggestion(self, request):
        validated_data = self.validate_request(request)

        result = HealthIdService.enrollment__enrol__suggestion(
            {
                "transaction_id": str(validated_data.get("transaction_id")),
            }
        )

        return Response(
            {
                "transaction_id": result.get("txnId"),
                "abha_addresses": result.get("abhaAddressList"),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_create__enrol_abha_address(self, request):
        validated_data = self.validate_request(request)

        result = HealthIdService.enrollment__enrol__abha_address(
            {
                "transaction_id": str(validated_data.get("transaction_id")),
                "abha_address": validated_data.get("abha_address"),
                "preferred": 1,
            }
        )

        abha_number = AbhaNumber.objects.filter(
            abha_number=result.get("healthIdNumber")
        ).first()

        if not abha_number:
            return Response(
                {
                    "detail": "Couldn't enroll abha address, ABHA Number not found, Please try again later",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile_result = HealthIdService.profile__account(
            {"x_token": abha_number.access_token}
        )

        (abha_number, _) = AbhaNumber.objects.update_or_create(
            abha_number=profile_result.get("ABHANumber"),
            defaults={
                "abha_number": profile_result.get("ABHANumber"),
                "health_id": profile_result.get("preferredAbhaAddress"),
                "name": profile_result.get("name"),
                "first_name": profile_result.get("firstName"),
                "middle_name": profile_result.get("middleName"),
                "last_name": profile_result.get("lastName"),
                "gender": profile_result.get("gender"),
                "date_of_birth": str(
                    datetime.strptime(
                        f"{profile_result.get('yearOfBirth')}-{profile_result.get('monthOfBirth')}-{profile_result.get('dayOfBirth')}",
                        "%Y-%m-%d",
                    )
                )[0:10],
                "address": profile_result.get("address"),
                "district": profile_result.get("districtName"),
                "state": profile_result.get("stateName"),
                "pincode": profile_result.get("pincode"),
                "email": profile_result.get("email"),
                # "mobile": profile_result.get("mobile"),
                "profile_photo": profile_result.get("profilePhoto"),
                "txn_id": result.get("txnId"),
            },
        )

        return Response(
            {
                "transaction_id": result.get("txnId"),
                "health_id": result.get("healthIdNumber"),
                "preferred_abha_address": result.get("preferredAbhaAddress"),
                "abha_number": AbhaNumberSerializer(abha_number).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_login__send_otp(self, request):
        validated_data = self.validate_request(request)

        otp_system = validated_data.get("otp_system")
        type = validated_data.get("type")

        scope = []

        if otp_system == "aadhaar":
            scope.append("aadhaar-verify")
        elif otp_system == "abdm":
            scope.append("mobile-verify")

        if type == "abha-address":
            scope.insert(0, "abha-address-login")
            result = HealthIdService.phr__web__login__abha__request__otp(
                {
                    "scope": scope,
                    "type": "abha-address",
                    "otp_system": otp_system,
                    "value": validated_data.get("value"),
                }
            )
        else:
            scope.insert(0, "abha-login")
            result = HealthIdService.profile__login__request__otp(
                {
                    "scope": scope,
                    "type": type,
                    "value": validated_data.get("value"),
                    "otp_system": otp_system,
                }
            )

        return Response(
            {
                "transaction_id": result.get("txnId"),
                "detail": result.get("message"),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_login__verify_otp(self, request):
        validated_data = self.validate_request(request)

        type = validated_data.get("type")
        otp_system = validated_data.get("otp_system")

        scope = []

        if otp_system == "aadhaar":
            scope.append("aadhaar-verify")
        elif otp_system == "abdm":
            scope.append("mobile-verify")

        token = None

        if type == "abha-address":
            scope.insert(0, "abha-address-login")
            result = HealthIdService.phr__web__login__abha__verify(
                {
                    "scope": scope,
                    "transaction_id": str(validated_data.get("transaction_id")),
                    "otp": validated_data.get("otp"),
                }
            )

            token = {
                "txn_id": result.get("txnId"),
                "access_token": result.get("token"),
                "refresh_token": result.get("refreshToken"),
            }
        else:
            scope.insert(0, "abha-login")
            result = HealthIdService.profile__login__verify(
                {
                    "scope": scope,
                    "transaction_id": str(validated_data.get("transaction_id")),
                    "otp": validated_data.get("otp"),
                }
            )

            if type == "mobile":
                user_verification_result = HealthIdService.profile__login__verify__user(
                    {
                        "t_token": result.get("token"),
                        "abha_number": result.get("accounts")[0].get("ABHANumber"),
                        "transaction_id": result.get("txnId"),
                    }
                )

                token = {
                    "txn_id": result.get("txnId"),
                    "access_token": user_verification_result.get("token"),
                    "refresh_token": user_verification_result.get("refreshToken"),
                }
            else:
                token = {
                    "txn_id": result.get("txnId"),
                    "access_token": result.get("token"),
                    "refresh_token": result.get("refreshToken"),
                }

        if not token:
            return Response(
                {
                    "detail": "Unable to verify OTP, Please try again later",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile_result = HealthIdService.profile__account(
            {"x_token": token.get("access_token")}
        )

        (abha_number, created) = AbhaNumber.objects.update_or_create(
            abha_number=profile_result.get("ABHANumber"),
            defaults={
                "abha_number": profile_result.get("ABHANumber"),
                "health_id": profile_result.get("preferredAbhaAddress"),
                "name": profile_result.get("name"),
                "first_name": profile_result.get("firstName"),
                "middle_name": profile_result.get("middleName"),
                "last_name": profile_result.get("lastName"),
                "gender": profile_result.get("gender"),
                "date_of_birth": str(
                    datetime.strptime(
                        f"{profile_result.get('yearOfBirth')}-{profile_result.get('monthOfBirth')}-{profile_result.get('dayOfBirth')}",
                        "%Y-%m-%d",
                    )
                )[0:10],
                "address": profile_result.get("address"),
                "district": profile_result.get("districtName"),
                "state": profile_result.get("stateName"),
                "pincode": profile_result.get("pincode"),
                "email": profile_result.get("email"),
                # "mobile": profile_result.get("mobile"),
                "profile_photo": profile_result.get("profilePhoto"),
                "txn_id": token.get("txn_id"),
                "access_token": token.get("access_token"),
                "refresh_token": token.get("refresh_token"),
            },
        )

        serialized_data = AbhaNumberSerializer(abha_number).data

        return Response(
            {"abha_number": serialized_data, "created": created},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def abha_login__check_auth_methods(self, request):
        validated_data = self.validate_request(request)

        abha_address = validated_data.get("abha_address")

        if not abha_address.endswith(f"@{settings.X_CM_ID}"):
            abha_address = f"{abha_address}@{settings.X_CM_ID}"

        result = HealthIdService.phr__web__login__abha__search(
            {
                "abha_address": abha_address,
            }
        )

        return Response(
            {
                "abha_number": result.get("healthIdNumber"),
                "auth_methods": result.get("authMethods"),
            },
            status=status.HTTP_200_OK,
        )
