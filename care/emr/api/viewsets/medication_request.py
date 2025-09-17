from django_filters import rest_framework as filters
from rest_framework import filters as rest_framework_filters
from rest_framework.exceptions import PermissionDenied

from care.emr.api.viewsets.base import EMRModelViewSet, EMRQuestionnaireResponseMixin
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.medication.request.spec import (
    MedicationRequestReadSpec,
    MedicationRequestSpec,
    MedicationRequestUpdateSpec,
)
from care.emr.resources.questionnaire.spec import SubjectType
from care.security.authorization import AuthorizationController
from care.users.models import User
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.filters.null_filter import NullFilter
from care.utils.shortcuts import get_object_or_404


class MedicationRequestFilter(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    status = MultiSelectFilter(field_name="status")
    name = filters.CharFilter(field_name="medication__display", lookup_expr="icontains")
    encounter_class = filters.CharFilter(
        field_name="encounter__class", lookup_expr="iexact"
    )
    priority = filters.CharFilter(lookup_expr="iexact")
    dispense_status = MultiSelectFilter(field_name="dispense_status")
    exclude_dispense_status = MultiSelectFilter(
        field_name="dispense_status", exclude=True
    )
    dispense_status_isnull = NullFilter(field_name="dispense_status")
    facility = filters.UUIDFilter(field_name="encounter__facility__external_id")
    prescription = filters.UUIDFilter(field_name="prescription__external_id")


class MedicationRequestViewSet(
    EncounterBasedAuthorizationBase, EMRQuestionnaireResponseMixin, EMRModelViewSet
):
    database_model = MedicationRequest
    pydantic_model = MedicationRequestSpec
    pydantic_read_model = MedicationRequestReadSpec
    pydantic_update_model = MedicationRequestUpdateSpec
    questionnaire_type = "medication_request"
    questionnaire_title = "Medication Request"
    questionnaire_description = "Medication Request"
    questionnaire_subject_type = SubjectType.patient.value
    filterset_class = MedicationRequestFilter
    filter_backends = [
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
    ]
    ordering_fields = ["created_date", "modified_date"]

    def get_queryset(self):
        self.authorize_read_for_medication()
        return (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("patient", "encounter", "created_by", "updated_by")
        )

    def authorize_create(self, instance):
        super().authorize_create(instance)
        if instance.requester:
            encounter = get_object_or_404(Encounter, external_id=instance.encounter)
            requester = get_object_or_404(User, external_id=instance.requester)
            if not AuthorizationController.call(
                "can_update_encounter_obj", requester, encounter
            ):
                raise PermissionDenied(
                    "Requester does not have permission to update encounter"
                )


InternalQuestionnaireRegistry.register(MedicationRequestViewSet)
