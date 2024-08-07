from datetime import datetime

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
)
from care.abdm.models import AbhaNumber
from care.abdm.service.v3.health_id import HealthIdService


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
    }

    def get_serializer_class(self):
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]

        return super().get_serializer_class()

    def validate_request(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return serializer.validated_data

    def create_or_update_abha_number(
        self, data: HealthIdService.ProfileAccountResponse, token: dict, is_new=False
    ):
        return AbhaNumber.objects.update_or_create(
            abha_number=data.get("ABHANumber"),
            defaults={
                "abha_number": data.get("ABHANumber"),
                "health_id": data.get("preferredAbhaAddress")
                or data.get("phrAddress", [None])[0],
                "name": data.get("name"),
                "first_name": data.get("firstName"),
                "middle_name": data.get("middleName"),
                "last_name": data.get("lastName"),
                "gender": data.get("gender"),
                "date_of_birth": str(
                    datetime.strptime(
                        f"{data.get('yearOfBirth')}-{data.get('monthOfBirth')}-{data.get('dayOfBirth')}",
                        "%Y-%m-%d",
                    )
                )[0:10],
                "address": data.get("address"),
                "district": data.get("districtName"),
                "state": data.get("stateName"),
                "pincode": data.get("pincode"),
                "email": data.get("email"),
                "profile_photo": data.get("profilePhoto"),
                "new": is_new,
                "txn_id": token.get("txn_id"),
                "access_token": token.get("access_token"),
                "refresh_token": token.get("refresh_token"),
            },
        )

    @action(detail=False, methods=["post"])
    def abha_create__send_aadhaar_otp(self, request):
        validated_data = self.validate_request(request)

        response = HealthIdService.enrollment__request__otp(
            {
                "scope": ["abha-enrol"],
                "transaction_id": "",
                "type": "aadhaar",
                "value": validated_data.get("aadhaar"),
            }
        )

        if response.ok:
            result: HealthIdService.EnrollmentRequestOtpResponse = response.json()
            return Response(
                {
                    "transaction_id": result.get("txnId"),
                    "detail": result.get("message"),
                },
                status=status.HTTP_200_OK,
            )

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Something went wrong"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"])
    def abha_create__verify_aadhaar_otp(self, request):
        validated_data = self.validate_request(request)

        response = HealthIdService.enrollment__enrol__byAadhaar(
            {
                "transaction_id": str(validated_data.get("transaction_id")),
                "otp": validated_data.get("otp"),
                "mobile": validated_data.get("mobile"),
            }
        )

        if response.ok:
            result: HealthIdService.EnrollmentEnrolByAadhaarResponse = response.json()

            (abha_number, created) = self.create_or_update_abha_number(
                result.get("ABHAProfile"),
                {
                    "txn_id": result.get("txnId"),
                    "access_token": result.get("tokens").get("token"),
                    "refresh_token": result.get("tokens").get("refreshToken"),
                },
                result.get("isNew"),
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

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Something went wrong"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"])
    def abha_create__link_mobile_number(self, request):
        validated_data = self.validate_request(request)

        response = HealthIdService.enrollment__request__otp(
            {
                "scope": ["abha-enrol", "mobile-verify"],
                "type": "mobile",
                "value": validated_data.get("mobile"),
                "transaction_id": str(validated_data.get("transaction_id")),
            }
        )

        if response.ok:
            result: HealthIdService.EnrollmentRequestOtpResponse = response.json()
            return Response(
                {
                    "transaction_id": result.get("txnId"),
                    "detail": result.get("message"),
                },
                status=status.HTTP_200_OK,
            )

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Something went wrong"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"])
    def abha_create__verify_mobile_otp(self, request):
        validated_data = self.validate_request(request)

        response = HealthIdService.enrollment__auth__byAbdm(
            {
                "scope": ["abha-enrol", "mobile-verify"],
                "transaction_id": str(validated_data.get("transaction_id")),
                "otp": validated_data.get("otp"),
            }
        )

        if response.ok:
            result: HealthIdService.EnrollmentAuthByAbdmResponse = response.json()
            return Response(
                {
                    "transaction_id": result.get("txnId"),
                    "detail": result.get("message"),
                },
                status=status.HTTP_200_OK,
            )

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Something went wrong"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"])
    def abha_create__abha_address_suggestion(self, request):
        validated_data = self.validate_request(request)

        response = HealthIdService.enrollment__enrol_suggestion(
            {
                "transaction_id": str(validated_data.get("transaction_id")),
            }
        )

        if response.ok:
            result: HealthIdService.EnrollmentEnrolSuggestionResponse = response.json()
            return Response(
                {
                    "transaction_id": result.get("txnId"),
                    "abha_addresses": result.get("abhaAddressList"),
                },
                status=status.HTTP_200_OK,
            )

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Something went wrong"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"])
    def abha_create__enrol_abha_address(self, request):
        validated_data = self.validate_request(request)

        response = HealthIdService.enrollment__enrol_abha_address(
            {
                "transaction_id": str(validated_data.get("transaction_id")),
                "abha_address": validated_data.get("abha_address"),
                "preferred": 1,
            }
        )

        if response.ok:
            result: HealthIdService.EnrollmentEnrolAbhaAddressResponse = response.json()

            abha_number = AbhaNumber.objects.filter(
                abha_number=result.get("healthIdNumber")
            ).first()

            if abha_number:
                profile_response = HealthIdService.profile__account(
                    {"x_token": abha_number.access_token}
                )

                if profile_response.ok:
                    profile_result: HealthIdService.ProfileAccountResponse = (
                        profile_response.json()
                    )

                    (abha_number, _) = self.create_or_update_abha_number(
                        profile_result,
                        {
                            "txn_id": result.get("txnId"),
                            "access_token": abha_number.access_token,
                            "refresh_token": abha_number.refresh_token,
                        },
                    )
                else:
                    abha_number.health_id = result.get("preferredAbhaAddress")
                    abha_number.save()

                return Response(
                    {
                        "transaction_id": result.get("txnId"),
                        "health_id": result.get("healthIdNumber"),
                        "preferred_abha_address": result.get("preferredAbhaAddress"),
                        "abha_number": AbhaNumberSerializer(abha_number).data,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "transaction_id": result.get("txnId"),
                    "health_id": result.get("healthIdNumber"),
                    "preferred_abha_address": result.get("preferredAbhaAddress"),
                },
                status=status.HTTP_200_OK,
            )

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Something went wrong"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
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
            response = HealthIdService.phr__web__login__abha__request__otp(
                {
                    "scope": scope,
                    "type": "abha-address",
                    "otp_system": otp_system,
                    "value": validated_data.get("value"),
                }
            )
        else:
            scope.insert(0, "abha-login")
            response = HealthIdService.profile__login__request__otp(
                {
                    "scope": scope,
                    "type": type,
                    "value": validated_data.get("value"),
                    "otp_system": otp_system,
                }
            )

        if response.ok:
            result: HealthIdService.ProfileLoginRequestOtpResponse = response.json()
            return Response(
                {
                    "transaction_id": result.get("txnId"),
                    "detail": result.get("message"),
                },
                status=status.HTTP_200_OK,
            )

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Something went wrong"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
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
            response = HealthIdService.phr__web__login__abha__verify(
                {
                    "scope": scope,
                    "transaction_id": str(validated_data.get("transaction_id")),
                    "otp": validated_data.get("otp"),
                }
            )

            if response.ok:
                result: HealthIdService.PhrWebLoginAbhaVerifyResponse = response.json()
                token = {
                    "txn_id": result.get("txnId"),
                    "access_token": result.get("token"),
                    "refresh_token": result.get("refreshToken"),
                }
        else:
            scope.insert(0, "abha-login")
            response = HealthIdService.profile__login__verify(
                {
                    "scope": scope,
                    "transaction_id": str(validated_data.get("transaction_id")),
                    "otp": validated_data.get("otp"),
                }
            )

            if response.ok:
                result: HealthIdService.ProfileLoginVerifyResponse = response.json()

                if type == "mobile":
                    user_verification_response = (
                        HealthIdService.profile__login__verify__user(
                            {
                                "t_token": result.get("token"),
                                "abha_number": result.get("accounts")[0].get(
                                    "ABHANumber"
                                ),
                                "transaction_id": result.get("txnId"),
                            }
                        )
                    )

                    if user_verification_response.ok:
                        user_verification_result: (
                            HealthIdService.ProfileLoginVerifyUserResponse
                        ) = user_verification_response.json()
                        token = {
                            "txn_id": result.get("txnId"),
                            "access_token": user_verification_result.get("token"),
                            "refresh_token": user_verification_result.get(
                                "refreshToken"
                            ),
                        }
                    else:
                        error: HealthIdService.ErrorResponse = (
                            user_verification_response.json()
                        )
                        return Response(
                            {
                                "detail": error.get(
                                    "error", {"message": "Unable to verify user"}
                                )["message"],
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    token = {
                        "txn_id": result.get("txnId"),
                        "access_token": result.get("token"),
                        "refresh_token": result.get("refreshToken"),
                    }

        if token:
            profile_response = HealthIdService.profile__account(
                {"x_token": token.get("access_token")}
            )

            if profile_response.ok:
                profile_result: HealthIdService.ProfileAccountResponse = (
                    profile_response.json()
                )

                (abha_number, created) = self.create_or_update_abha_number(
                    profile_result, token
                )

                serialized_data = AbhaNumberSerializer(abha_number).data

                return Response(
                    {"abha_number": serialized_data, "created": created},
                    status=status.HTTP_200_OK,
                )
            else:
                error: HealthIdService.ErrorResponse = profile_response.json()
                return Response(
                    {
                        "detail": error.get(
                            "error", {"message": "Unable to get profile"}
                        )["message"],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Unable to verify otp"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"])
    def abha_login__check_auth_methods(self, request):
        validated_data = self.validate_request(request)

        response = HealthIdService.profile__login__check_auth_methods(
            {
                "abha_number": validated_data.get("abha_number"),
            }
        )

        if response.ok:
            result: HealthIdService.ProfileLoginCheckAuthMethodsResponse = (
                response.json()
            )
            return Response(
                {
                    "abha_number": result.get("abhaNumber"),
                    "auth_methods": result.get("authMethods"),
                },
                status=status.HTTP_200_OK,
            )

        error: HealthIdService.ErrorResponse = response.json()
        return Response(
            {
                "detail": error.get("error", {"message": "Unable to get auth methods"})[
                    "message"
                ],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
