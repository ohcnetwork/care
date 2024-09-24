from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.patient_otp import PatientMobileOTPSerializer
from care.facility.models.patient import PatientMobileOTP
from care.utils.models.validators import mobile_validator
from config.patient_otp_token import PatientToken


@extend_schema_view(create=extend_schema(tags=["auth"]))
class PatientMobileOTPViewSet(
    mixins.CreateModelMixin,
    GenericViewSet,
):
    authentication_classes = ()
    permission_classes = ()
    serializer_class = PatientMobileOTPSerializer
    queryset = PatientMobileOTP.objects.all()

    @extend_schema(tags=["auth"])
    @action(detail=False, methods=["POST"])
    def login(self, request):
        if "phone_number" not in request.data or "otp" not in request.data:
            msg = "Request Incomplete"
            raise ValidationError(msg)
        phone_number = request.data["phone_number"]
        otp = request.data["otp"]
        try:
            mobile_validator(phone_number)
        except Exception as e:
            raise ValidationError(
                {"phone_number": "Invalid phone number format"}
            ) from e
        if len(otp) != settings.OTP_LENGTH:
            raise ValidationError({"otp": "Invalid OTP"})

        otp_object = PatientMobileOTP.objects.filter(
            phone_number=phone_number, otp=otp, is_used=False
        ).first()

        if not otp_object:
            raise ValidationError({"otp": "Invalid OTP"})

        otp_object.is_used = True
        otp_object.save()

        token = PatientToken()
        token["phone_number"] = phone_number

        return Response({"access": str(token)})
