from django_filters import CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRQuestionnaireResponseMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models import Patient
from care.emr.models.allergy_intolerance import AllergyIntolerance
from care.emr.models.encounter import Encounter
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.allergy_intolerance.spec import (
    AllergyIntoleranceReadSpec,
    AllergyIntoleranceUpdateSpec,
    AllergyIntoleranceWriteSpec,
)
from care.emr.resources.questionnaire.spec import SubjectType
from care.security.authorization import AuthorizationController


class AllergyIntoleranceFilters(FilterSet):
    clinical_status = CharFilter(field_name="clinical_status")


@extend_schema_view(
    create=extend_schema(request=AllergyIntoleranceWriteSpec),
)
class AllergyIntoleranceViewSet(
    EMRQuestionnaireResponseMixin,
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
):
    database_model = AllergyIntolerance
    pydantic_model = AllergyIntoleranceWriteSpec
    pydantic_read_model = AllergyIntoleranceReadSpec
    pydantic_update_model = AllergyIntoleranceUpdateSpec
    questionnaire_type = "allergy_intolerance"
    questionnaire_title = "Allergy Intolerance"
    questionnaire_description = "Allergy Intolerance"
    questionnaire_subject_type = SubjectType.patient.value
    filterset_class = AllergyIntoleranceFilters
    filter_backends = [DjangoFilterBackend]

    def get_patient_obj(self):
        return get_object_or_404(
            Patient, external_id=self.kwargs["patient_external_id"]
        )

    def authorize_create(self, instance):
        if not AuthorizationController.call(
            "can_write_patient_obj", self.request.user, self.get_patient_obj()
        ):
            raise PermissionDenied("You do not have permission to update encounter")

    def authorize_update(self, request_obj, model_instance):
        encounter = get_object_or_404(Encounter, external_id=request_obj.encounter)
        if not AuthorizationController.call(
            "can_update_encounter_obj",
            self.request.user,
            encounter,
        ):
            raise PermissionDenied("You do not have permission to update encounter")

    def clean_update_data(self, request_data):
        return super().clean_update_data(request_data, keep_fields={"encounter"})

    def get_queryset(self):
        if not AuthorizationController.call(
            "can_view_clinical_data", self.request.user, self.get_patient_obj()
        ):
            raise PermissionDenied("Permission denied for patient data")
        return (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("patient", "encounter", "created_by", "updated_by")
            .order_by("-modified_date")
        )


InternalQuestionnaireRegistry.register(AllergyIntoleranceViewSet)
