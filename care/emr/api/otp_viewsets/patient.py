from care.emr.api.otp_viewsets.base import OTPBaseViewset
from care.emr.api.viewsets.base import EMRCreateMixin, EMRListMixin
from care.emr.models.patient import Patient
from care.emr.resources.patient.otp_based_flow import (
    PatientOTPReadSpec,
    PatientOTPWriteSpec,
)


class PatientOTPView(EMRCreateMixin, EMRListMixin, OTPBaseViewset):
    pydantic_model = PatientOTPWriteSpec
    pydantic_read_model = PatientOTPReadSpec

    def perform_create(self, instance):
        instance.phone_number = self.request.user.phone_number
        instance.save()

    def get_queryset(self):
        return Patient.objects.filter(phone_number=self.request.user.phone_number)
