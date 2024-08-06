from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.abdm.api.v3.serializers.health_id import (
    AbhaAddressSuggestionSerializer,
    EnrolAbhaAddressSerializer,
    LinkMobileNumberSerializer,
    SendAadhaarOtpSerializer,
    VerifyAadhaarOtpSerializer,
    VerifyMobileOtpSerializer,
)
from care.abdm.service.v3.health_id import HealthIdService


class HealthIdViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated,)

    serializer_action_classes = {
        "abha_create__send_aadhaar_otp": SendAadhaarOtpSerializer,
        "abha_create__verify_aadhaar_otp": VerifyAadhaarOtpSerializer,
        "abha_create__link_mobile_number": LinkMobileNumberSerializer,
        "abha_create__verify_mobile_otp": VerifyMobileOtpSerializer,
        "abha_create__abha_address_suggestion": AbhaAddressSuggestionSerializer,
        "abha_create__enrol_abha_address": EnrolAbhaAddressSerializer,
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
                    "transaction_id": result["txnId"],
                    "detail": result["message"],
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

            # TODO: create abha address here

            return Response(
                {"transaction_id": result["txnId"], "detail": result["message"]},
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
                    "transaction_id": result["txnId"],
                    "detail": result["message"],
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
                    "transaction_id": result["txnId"],
                    "detail": result["message"],
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
                    "transaction_id": result["txnId"],
                    "abha_addresses": result["abhaAddressList"],
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

            # TODO: update the abha address here or make an api call to profile and update the abha address

            return Response(
                {
                    "transaction_id": result["txnId"],
                    "health_id": result["healthIdNumber"],
                    "preferred_abha_address": result["preferredAbhaAddress"],
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
