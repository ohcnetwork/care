from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet
from care.emr.models import Encounter, Patient
from care.emr.models.questionnaire import QuestionnaireResponse
from care.emr.resources.questionnaire_response.spec import QuestionnaireResponseReadSpec
from care.security.authorization import AuthorizationController


class QuestionnaireResponseFilters(filters.FilterSet):
    encounter = filters.CharFilter(field_name="encounter__external_id")
    subject_type = filters.CharFilter(field_name="questionnaire__subject_type")
    questionnaire = filters.UUIDFilter(field_name="questionnaire__external_id")
    questionnaire_slug = filters.CharFilter(field_name="questionnaire__slug")


class QuestionnaireResponseViewSet(EMRModelReadOnlyViewSet):
    database_model = QuestionnaireResponse
    pydantic_model = QuestionnaireResponseReadSpec
    pydantic_read_model = QuestionnaireResponseReadSpec
    filterset_class = QuestionnaireResponseFilters
    filter_backends = [filters.DjangoFilterBackend]

    def get_queryset(self):
        queryset = (
            QuestionnaireResponse.objects.filter(
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
            obj = get_object_or_404(QuestionnaireResponse, self.kwargs["external_id"])
            patient = obj.patient
            encounter = obj.encounter
        if encounter:
            allowed = AuthorizationController.call(
                "can_view_clinical_data", self.request.user, patient
            ) or AuthorizationController.call(
                "can_view_encounter_obj", self.request.user, encounter
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
