from django_filters import rest_framework as filters

from care.emr.api.otp_viewsets.base import (
    OTPBaseViewset,
    OTPResourceType,
    QuerysetEnablerMixin,
)
from care.emr.api.viewsets.base import EMRListMixin, EMRRetrieveMixin
from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.resources.medication.request_prescription.spec import (
    MedicationRequestPrescriptionReadSpec,
    MedicationRequestPrescriptionRetrieveMedicationsSpec,
)
from care.utils.filters.multiselect import MultiSelectFilter


class OTPMedicationRequestPrescriptionFilters(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="encounter__facility__external_id")
    status = MultiSelectFilter(field_name="status")
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    patient = filters.UUIDFilter(field_name="patient__external_id")
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")


class OTPMedicationRequestPrescriptionViewSet(
    QuerysetEnablerMixin,
    EMRRetrieveMixin,
    OTPBaseViewset,
    EMRListMixin,
):
    database_model = MedicationRequestPrescription
    pydantic_read_model = MedicationRequestPrescriptionReadSpec
    pydantic_retrieve_model = MedicationRequestPrescriptionRetrieveMedicationsSpec
    filterset_class = OTPMedicationRequestPrescriptionFilters
    filter_backends = [filters.DjangoFilterBackend]
    resource_type = OTPResourceType.medication_request_prescription

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(patient__phone_number=self.request.user.phone_number)
        )
