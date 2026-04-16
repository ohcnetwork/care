from datetime import timedelta

from django.conf import settings
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet, EMRUpdateMixin
from care.emr.models import Encounter, Patient
from care.emr.models.questionnaire import QuestionnaireResponse
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireResponseReadSpec,
    QuestionnaireResponseStatusChoices,
    QuestionnaireResponseUpdate,
)
from care.security.authorization import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from care.utils.time_util import care_now


class QuestionnaireResponseFilters(filters.FilterSet):
    encounter = filters.CharFilter(field_name="encounter__external_id")
    subject_type = filters.CharFilter(field_name="questionnaire__subject_type")
    questionnaire = filters.UUIDFilter(field_name="questionnaire__external_id")
    questionnaire_slug = filters.CharFilter(field_name="questionnaire__slug")
    form_submission = filters.UUIDFilter(field_name="form_submission__external_id")
    status = filters.CharFilter(field_name="status")


class QuestionnaireResponseViewSet(EMRModelReadOnlyViewSet, EMRUpdateMixin):
    database_model = QuestionnaireResponse
    pydantic_model = QuestionnaireResponseReadSpec
    pydantic_read_model = QuestionnaireResponseReadSpec
    pydantic_update_model = QuestionnaireResponseUpdate
    filterset_class = QuestionnaireResponseFilters
    filter_backends = [filters.DjangoFilterBackend]

    def authorize_update(self, request_obj, model_instance):
        if (
            model_instance.status
            == QuestionnaireResponseStatusChoices.entered_in_error.value
        ):
            raise PermissionDenied("Questionnaire Response cannot be edited")
        if self.request.user.is_superuser:
            return True
        if care_now() > model_instance.created_date + timedelta(
            minutes=settings.QUESTIONNAIRE_ERRORED_TIME_LIMIT_MINUTES
        ):
            raise PermissionDenied("Questionnaire Response cannot be edited")
        return super().authorize_update(request_obj, model_instance)

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .filter(
                patient__external_id=self.kwargs["patient_external_id"],
            )
            .order_by("-created_date")
            .select_related("questionnaire", "encounter", "created_by", "updated_by")
        )
        patient = None
        encounter = None
        if self.action == "list":
            patient = get_object_or_404(
                Patient, external_id=self.kwargs["patient_external_id"]
            )
            if "encounter" in self.request.GET:
                encounter = get_object_or_404(
                    Encounter, external_id=self.request.GET["encounter"]
                )
        else:
            obj = get_object_or_404(
                QuestionnaireResponse, external_id=self.kwargs["external_id"]
            )
            patient = obj.patient
            encounter = obj.encounter
        if encounter:
            allowed = AuthorizationController.call(
                "can_view_clinical_data", self.request.user, patient
            ) or AuthorizationController.call(
                "can_view_encounter_clinical_data", self.request.user, encounter
            )
        else:
            allowed = AuthorizationController.call(
                "can_view_patient_questionnaire_responses", self.request.user, patient
            )
        if not allowed:
            raise PermissionDenied(
                "You do not have permission to view questionnaire responses"
            )
        if "questionnaire_slugs" in self.request.GET:
            questionnaire_slugs = self.request.GET.get("questionnaire_slugs").split(",")
            queryset = queryset.filter(questionnaire__slug__in=questionnaire_slugs)
        if "only_unstructured" in self.request.GET:
            queryset = queryset.filter(structured_response_type__isnull=True)
        return queryset
