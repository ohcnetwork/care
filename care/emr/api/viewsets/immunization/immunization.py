from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.encounter import Encounter
from care.emr.models.immunisation import Immunization
from care.emr.models.patient import Patient
from care.emr.resources.immunisation.immunization import (
    ImmunizationCreateSpec,
    ImmunizationListSpec,
    ImmunizationRetrieveSpec,
    ImmunizationUpdateSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404


class ImmunizationRecordFilters(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    recommendation = filters.UUIDFilter(field_name="recommendation__external_id")
    facility = filters.UUIDFilter(field_name="facility__external_id")
    status = MultiSelectFilter(field_name="status")
    reason = MultiSelectFilter(field_name="reason")
    occurrence = filters.DateTimeFromToRangeFilter()
    primary_source = filters.BooleanFilter()


class ImmunizationRecordViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = Immunization
    pydantic_model = ImmunizationCreateSpec
    pydantic_update_model = ImmunizationUpdateSpec
    pydantic_read_model = ImmunizationListSpec
    pydantic_retrieve_model = ImmunizationRetrieveSpec
    filterset_class = ImmunizationRecordFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def get_patient_obj(self):
        return get_object_or_404(
            Patient, external_id=self.kwargs["patient_external_id"]
        )

    def validate_data(self, instance, model_obj=None):
        if model_obj is None:
            get_object_or_404(
                Encounter,
                external_id=instance.encounter,
                patient=self.get_patient_obj(),
            )

    def authorize_create(self, instance):
        encounter = get_object_or_404(
            Encounter,
            external_id=instance.encounter,
            patient=self.get_patient_obj(),
        )
        if not AuthorizationController.call(
            "can_write_encounter_immunization", self.request.user, encounter
        ):
            raise PermissionDenied("You do not have permission to create immunizations")

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_encounter_immunization",
            self.request.user,
            model_instance.encounter,
        ):
            raise PermissionDenied("You do not have permission to update immunizations")

    def authorize_retrieve(self, model_instance):
        if AuthorizationController.call(
            "can_read_patient_immunization", self.request.user, model_instance.patient
        ):
            return
        if not AuthorizationController.call(
            "can_read_encounter_immunization",
            self.request.user,
            model_instance.encounter,
        ):
            raise PermissionDenied("You do not have permission to view immunizations")

    def get_queryset(self):
        patient = self.get_patient_obj()
        queryset = (
            super()
            .get_queryset()
            .filter(patient=patient)
            .select_related(
                "patient",
                "encounter",
                "facility",
                "recommendation",
                "product",
                "location",
                "administered_by",
            )
        )
        encounter = None
        if encounter_id := self.request.query_params.get("encounter"):
            encounter = get_object_or_404(
                Encounter, external_id=encounter_id, patient=patient
            )
            queryset = queryset.filter(encounter=encounter)
        if (
            self.action == "list"
            and not AuthorizationController.call(
                "can_read_patient_immunization", self.request.user, patient
            )
            and (
                encounter is None
                or not AuthorizationController.call(
                    "can_read_encounter_immunization", self.request.user, encounter
                )
            )
        ):
            raise PermissionDenied("You do not have permission to view immunizations")
        return queryset
