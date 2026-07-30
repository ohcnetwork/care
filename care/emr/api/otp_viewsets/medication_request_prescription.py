from django_filters import rest_framework as filters

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRListMixin, EMRRetrieveMixin
from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.resources.medication.request_prescription.spec import (
    MedicationRequestPrescriptionReadSpec,
    MedicationRequestPrescriptionRetrieveMedicationsSpec,
)
from care.utils.filters.multiselect import MultiSelectFilter
from config.patient_otp_authentication import (
    JWTTokenPatientAuthentication,
    OTPAuthenticatedPermission,
)


class OTPMedicationPrescriptionFilter(filters.FilterSet):
    status = MultiSelectFilter(field_name="status")
    facility = filters.UUIDFilter(field_name="encounter__facility__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    created_date = filters.DateTimeFromToRangeFilter()


class OTPMedicationRequestPrescriptionViewSet(
    EMRRetrieveMixin, EMRBaseViewSet, EMRListMixin
):
    authentication_classes = [JWTTokenPatientAuthentication]
    permission_classes = [OTPAuthenticatedPermission]
    database_model = MedicationRequestPrescription
    pydantic_read_model = MedicationRequestPrescriptionReadSpec
    pydantic_retrieve_model = MedicationRequestPrescriptionRetrieveMedicationsSpec
    filterset_class = OTPMedicationPrescriptionFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(patient__phone_number=self.request.user.phone_number)
        )
