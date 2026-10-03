from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet, EMRUpdateMixin
from care.emr.api.viewsets.questionnaire.resource_authz import (
    authorize_resource_questionnaire_response_read,
    authorize_resource_questionnaire_submission,
    get_questionniare_resource,
)
from care.emr.api.viewsets.questionnaire_response import QuestionnaireFilter
from care.emr.models.facility_resource import (
    FacilityResourceObservation,
    FacilityResourceQuestionnaireResponse,
)
from care.emr.resources.observation.spec import ObservationStatus
from care.emr.resources.questionnaire_response.resource_spce import (
    ResourceQuestionnaireResponseReadSpec,
    ResourceQuestionnaireResponseUpdate,
)
from care.emr.resources.questionnaire_response.spec import (
    QuestionnaireResponseStatusChoices,
)
from care.utils.filters.dummy_filter import DummyCharFilter, DummyUUIDFilter
from care.utils.time_util import care_now


class ResourceQuestionnaireResponseFilters(filters.FilterSet):
    questionnaire = QuestionnaireFilter()
    questionnaire_slug = filters.CharFilter(field_name="questionnaire__slug")
    status = filters.CharFilter(field_name="status")
    created_by = filters.UUIDFilter(field_name="created_by__external_id")
    subject_id = DummyUUIDFilter()
    subject_type = DummyCharFilter()


class ResourceQuestionnaireResponseViewSet(EMRModelReadOnlyViewSet, EMRUpdateMixin):
    database_model = FacilityResourceQuestionnaireResponse
    pydantic_model = ResourceQuestionnaireResponseReadSpec
    pydantic_update_model = ResourceQuestionnaireResponseUpdate
    filterset_class = ResourceQuestionnaireResponseFilters
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

        resource = get_questionniare_resource(
            model_instance.subject_type, model_instance.subject_id
        )
        authorize_resource_questionnaire_submission(
            model_instance.subject_type, resource, self.request.user
        )

        return super().authorize_update(request_obj, model_instance)

    def perform_update(self, instance):
        with transaction.atomic():
            old_obj = FacilityResourceQuestionnaireResponse.objects.get(id=instance.id)
            if (
                old_obj.status != instance.status
                and instance.status
                == QuestionnaireResponseStatusChoices.entered_in_error.value
            ):
                FacilityResourceObservation.objects.filter(
                    questionnaire_response=instance
                ).update(status=ObservationStatus.entered_in_error.value)
            super().perform_update(instance)

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .order_by("-created_date")
            .select_related("questionnaire")
        )

        if self.action in ["list", "retrieve"]:
            subject_id = self.request.GET.get("subject_id")
            subject_type = self.request.GET.get("subject_type")
            if not subject_id or not subject_type:
                raise ValidationError("subject_id and subject_type are required")
            subject = get_questionniare_resource(subject_type, subject_id)
            authorize_resource_questionnaire_response_read(
                subject_type, subject, self.request.user
            )
            queryset = queryset.filter(subject_type=subject_type, subject_id=subject_id)

        if "questionnaire_slugs" in self.request.GET:
            questionnaire_slugs = self.request.GET.get("questionnaire_slugs").split(",")
            queryset = queryset.filter(questionnaire__slug__in=questionnaire_slugs)
        return queryset
