from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRRetrieveMixin
from care.emr.api.viewsets.scheduling import (
    AppointmentBookingSpec,
    SlotsForDayRequestSpec,
    SlotViewSet,
)
from care.emr.api.viewsets.scheduling.booking import TokenBookingViewSet
from care.emr.models.patient import Patient
from care.emr.models.scheduling import TokenBooking, TokenSlot
from care.emr.resources.scheduling.slot.spec import (
    BookingStatusChoices,
    TokenBookingReadSpec,
    TokenSlotBaseSpec,
)
from config.patient_otp_authentication import (
    JWTTokenPatientAuthentication,
    OTPAuthenticatedPermission,
)


class SlotsForDayRequestSpec(SlotsForDayRequestSpec):
    facility: UUID4


class CancelAppointmentSpec(BaseModel):
    patient: UUID4
    appointment: UUID4


class OTPSlotViewSet(EMRRetrieveMixin, EMRBaseViewSet):
    authentication_classes = [JWTTokenPatientAuthentication]
    permission_classes = [OTPAuthenticatedPermission]
    database_model = TokenSlot
    pydantic_read_model = TokenSlotBaseSpec

    @action(detail=False, methods=["POST"])
    def get_slots_for_day(self, request, *args, **kwargs):
        request_data = SlotsForDayRequestSpec(**request.data)
        return SlotViewSet.get_slots_for_day_handler(
            request_data.facility, request.data
        )

    @action(detail=True, methods=["POST"])
    def create_appointment(self, request, *args, **kwargs):
        request_data = AppointmentBookingSpec(**request.data)
        if not Patient.objects.filter(
            external_id=request_data.patient, phone_number=request.user.phone_number
        ).exists():
            raise ValidationError("Patient not allowed")
        return SlotViewSet.create_appointment_handler(
            self.get_object(), request.data, None
        )

    @action(detail=False, methods=["POST"])
    def cancel_appointment(self, request, *args, **kwargs):
        request_data = CancelAppointmentSpec(**request.data)
        patient = get_object_or_404(
            Patient,
            external_id=request_data.patient,
            phone_number=request.user.phone_number,
        )
        token_booking = get_object_or_404(
            TokenBooking, external_id=request_data.appointment, patient=patient
        )
        return TokenBookingViewSet.cancel_appointment_handler(
            token_booking, {"reason": BookingStatusChoices.cancelled}, None
        )

    @action(detail=False, methods=["GET"])
    def get_appointments(self, request, *args, **kwargs):
        appointments = TokenBooking.objects.filter(
            patient__phone_number=request.user.phone_number
        )
        return Response(
            {
                "results": [
                    TokenBookingReadSpec.serialize(obj).model_dump(exclude=["meta"])
                    for obj in appointments
                ]
            }
        )
