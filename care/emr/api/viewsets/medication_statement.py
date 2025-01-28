from django_filters import rest_framework as filters

from care.emr.api.viewsets.base import EMRModelViewSet, EMRQuestionnaireResponseMixin
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.medication_statement import MedicationStatement
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.medication.statement.spec import (
    MedicationStatementReadSpec,
    MedicationStatementSpec,
    MedicationStatementUpdateSpec,
)
from care.emr.resources.questionnaire.spec import SubjectType


class MedicationStatementFilter(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")


class MedicationStatementViewSet(
    EncounterBasedAuthorizationBase, EMRQuestionnaireResponseMixin, EMRModelViewSet
):
    database_model = MedicationStatement
    pydantic_model = MedicationStatementSpec
    pydantic_read_model = MedicationStatementReadSpec
    pydantic_update_model = MedicationStatementUpdateSpec
    questionnaire_type = "medication_statement"
    questionnaire_title = "Medication Statement"
    questionnaire_description = "Medication Statement"
    questionnaire_subject_type = SubjectType.patient.value
    filterset_class = MedicationStatementFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        self.authorize_read_encounter()
        return (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("patient", "encounter", "created_by", "updated_by")
        )


InternalQuestionnaireRegistry.register(MedicationStatementViewSet)
