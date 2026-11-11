from django_filters import CharFilter, FilterSet, UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.api.viewsets.base import EMRModelViewSet, EMRQuestionnaireResponseMixin
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.encounter import Encounter
from care.emr.models.procedure import Procedure
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.procedure.spec import (
    ProcedureCreateSpec,
    ProcedureReadSpec,
    ProcedureRetrieveSpec,
    ProcedureUpdateSpec,
)
from care.emr.resources.questionnaire.spec import SubjectType
from care.security.authorization import AuthorizationController
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404
from care.utils.time_util import care_now


class ProcedureFilters(FilterSet):
    encounter = UUIDFilter(field_name="encounter__external_id")
    status = MultiSelectFilter(field_name="status")
    exclude_status = MultiSelectFilter(field_name="status", exclude=True)
    name = CharFilter(field_name="code__display", lookup_expr="icontains")


class ProcedureViewSet(
    EncounterBasedAuthorizationBase,
    EMRQuestionnaireResponseMixin,
    EMRModelViewSet,
):
    database_model = Procedure
    pydantic_model = ProcedureCreateSpec
    pydantic_read_model = ProcedureReadSpec
    pydantic_update_model = ProcedureUpdateSpec
    pydantic_retrieve_model = ProcedureRetrieveSpec
    questionnaire_type = "procedure"
    questionnaire_title = "Procedure"
    questionnaire_description = "Historical procedure"
    questionnaire_subject_type = SubjectType.patient.value
    filterset_class = ProcedureFilters
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ["created_date", "modified_date", "recorded_date"]

    def validate_data(self, instance, model_obj=None):
        encounter = (
            model_obj.encounter
            if model_obj
            else get_object_or_404(Encounter, external_id=instance.encounter)
        )
        if encounter.patient_id != self.get_patient_obj().id:
            raise ValidationError("Patient does not match the encounter's patient")

    def perform_create(self, instance):
        if instance.recorded_date is None:
            instance.recorded_date = care_now()
        super().perform_create(instance)

    def authorize_retrieve(self, model_instance):
        if AuthorizationController.call(
            "can_view_clinical_data", self.request.user, model_instance.patient
        ):
            return
        if not AuthorizationController.call(
            "can_view_encounter_clinical_data",
            self.request.user,
            model_instance.encounter,
        ):
            raise PermissionDenied("You do not have permission to view clinical data")

    def get_queryset(self):
        patient = self.get_patient_obj()
        queryset = (
            super()
            .get_queryset()
            .filter(patient=patient)
            .select_related("patient", "encounter", "created_by", "updated_by")
        )
        if encounter_id := self.request.query_params.get("encounter"):
            encounter = get_object_or_404(
                Encounter, external_id=encounter_id, patient=patient
            )
            queryset = queryset.filter(encounter=encounter)
        if self.action == "list":
            self.authorize_read_encounter()
        return queryset

    def handle_update(self, instance, request_data):
        # Bulk upserts also need the same patient and encounter scope as detail URLs.
        instance = get_object_or_404(
            self.get_queryset(), external_id=instance.external_id
        )
        return super().handle_update(instance, request_data)


InternalQuestionnaireRegistry.register(ProcedureViewSet)
