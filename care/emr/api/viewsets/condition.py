from django.shortcuts import get_object_or_404
from django_filters import CharFilter, FilterSet, UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError

from care.emr.api.viewsets.base import EMRModelViewSet, EMRQuestionnaireResponseMixin
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.condition import Condition
from care.emr.models.encounter import Encounter
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.condition.spec import (
    CategoryChoices,
    ConditionSpec,
    ConditionSpecRead,
    ConditionSpecUpdate,
)
from care.emr.resources.questionnaire.spec import SubjectType


class ValidateEncounterMixin:
    """
    Mixin to validate encounter and its relationship with the patient.
    """

    def validate_data(self, instance, model_obj=None):
        # Ensure the encounter exists and matches the patient's external ID
        if model_obj:
            encounter = model_obj.encounter
        else:
            encounter = get_object_or_404(Encounter, external_id=instance.encounter)

        if str(encounter.patient.external_id) != self.kwargs["patient_external_id"]:
            raise ValidationError(
                "Patient external ID mismatch with encounter's patient"
            )


class ConditionFilters(FilterSet):
    encounter = UUIDFilter(field_name="encounter__external_id")
    clinical_status = CharFilter(field_name="clinical_status", lookup_expr="iexact")
    verification_status = CharFilter(
        field_name="verification_status", lookup_expr="iexact"
    )
    severity = CharFilter(field_name="severity", lookup_expr="iexact")


class SymptomViewSet(
    ValidateEncounterMixin,
    EncounterBasedAuthorizationBase,
    EMRQuestionnaireResponseMixin,
    EMRModelViewSet,
):
    database_model = Condition
    pydantic_model = ConditionSpec
    pydantic_read_model = ConditionSpecRead
    pydantic_update_model = ConditionSpecUpdate
    # Filters
    filterset_class = ConditionFilters
    filter_backends = [DjangoFilterBackend]
    # Questionnaire Spec
    questionnaire_type = "symptom"
    questionnaire_title = "Symptom"
    questionnaire_description = "Symptom"
    questionnaire_subject_type = SubjectType.patient.value

    def perform_create(self, instance):
        instance.category = CategoryChoices.problem_list_item.value
        super().perform_create(instance)

    def get_queryset(self):
        # Check if the user has read access to the patient and their EMR Data
        self.authorize_read_encounter()
        return (
            super()
            .get_queryset()
            .filter(
                patient__external_id=self.kwargs["patient_external_id"],
                category=CategoryChoices.problem_list_item.value,
            )
            .select_related("patient", "encounter", "created_by", "updated_by")
        )


InternalQuestionnaireRegistry.register(SymptomViewSet)


class DiagnosisViewSet(
    ValidateEncounterMixin,
    EncounterBasedAuthorizationBase,
    EMRQuestionnaireResponseMixin,
    EMRModelViewSet,
):
    database_model = Condition
    pydantic_model = ConditionSpec
    pydantic_read_model = ConditionSpecRead
    pydantic_update_model = ConditionSpecUpdate

    # Filters
    filterset_class = ConditionFilters
    filter_backends = [DjangoFilterBackend]
    # Questionnaire Spec
    questionnaire_type = "diagnosis"
    questionnaire_title = "Diagnosis"
    questionnaire_description = "Diagnosis"
    questionnaire_subject_type = SubjectType.patient.value

    def perform_create(self, instance):
        instance.category = CategoryChoices.encounter_diagnosis.value
        super().perform_create(instance)

    def get_queryset(self):
        # Check if the user has read access to the patient and their EMR Data
        self.authorize_read_encounter()
        return (
            super()
            .get_queryset()
            .filter(
                patient__external_id=self.kwargs["patient_external_id"],
                category=CategoryChoices.encounter_diagnosis.value,
            )
            .select_related("patient", "encounter", "created_by", "updated_by")
        )


InternalQuestionnaireRegistry.register(DiagnosisViewSet)
