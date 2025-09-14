from django_filters import rest_framework as filters
from rest_framework import filters as rest_framework_filters

from care.emr.api.viewsets.base import EMRModelViewSet, EMRTagMixin
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.resources.medication.request_prescription.spec import (
    MedicationRequestPrescriptionReadSpec,
    MedicationRequestPrescriptionUpdateSpec,
    MedicationRequestPrescriptionWriteSpec,
)
from care.emr.resources.tag.config_spec import TagResource
from care.emr.tagging.filters import SingleFacilityTagFilter
from care.utils.filters.multiselect import MultiSelectFilter


class MedicationRequestPrescriptionFilter(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    status = MultiSelectFilter(field_name="status")
    facility = filters.UUIDFilter(field_name="encounter__facility__external_id")


class MedicationRequestPrescriptionViewSet(
    EncounterBasedAuthorizationBase, EMRModelViewSet, EMRTagMixin
):
    database_model = MedicationRequestPrescription
    pydantic_model = MedicationRequestPrescriptionWriteSpec
    pydantic_update_model = MedicationRequestPrescriptionUpdateSpec
    pydantic_read_model = MedicationRequestPrescriptionReadSpec
    filterset_class = MedicationRequestPrescriptionFilter
    filter_backends = [
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
        SingleFacilityTagFilter,
    ]
    ordering_fields = ["created_date", "modified_date"]
    resource_type = TagResource.medication_request_prescription

    def get_facility_from_instance(self, instance):
        return instance.encounter.facility  # Overide as needed

    def get_queryset(self):
        self.authorize_read_for_medication()
        return (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("patient", "encounter", "created_by", "updated_by", "prescribed_by")
            .prefetch_related("medication_requests")
        )
