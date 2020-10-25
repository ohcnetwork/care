from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework import mixins
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ValidationError
from django.conf import settings
from care.facility.api.serializers.patient_otp import PatientMobileOTPSerializer
from care.facility.models.patient import PatientMobileOTP

from care.users.models import phone_number_regex

from config.patient_otp_token import PatientToken


class PatientMobileOTPViewSet(
    mixins.CreateModelMixin, GenericViewSet,
):
    permission_classes = (AllowAny,)
    serializer_class = PatientMobileOTPSerializer
    queryset = PatientMobileOTP.objects.all()

    @action(detail=False, methods=["POST"])
    def login(self, request):
        if "phone_number" not in request.data or "otp" not in request.data:
            raise ValidationError("Request Incomplete")
        phone_number = request.data["phone_number"]
        otp = request.data["otp"]
        try:
            phone_number_regex(phone_number)
        except:
            raise ValidationError({"phone_number": "Invalid phone number format"})
        if len(otp) != settings.OTP_LENGTH:
            raise ValidationError({"otp": "Invalid OTP"})

        otp_object = PatientMobileOTP.objects.filter(phone_number=phone_number, otp=otp, is_used=False).first()

        if not otp_object:
            raise ValidationError({"otp": "Invalid OTP"})

        otp_object.is_used = True
        otp_object.save()
        # return JWT

        token = PatientToken()
        token["phone_number"] = phone_number

        return Response({"access": str(token)})

