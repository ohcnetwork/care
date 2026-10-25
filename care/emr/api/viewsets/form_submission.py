from django.db import transaction
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.models.questionnaire import FormSubmission
from care.emr.resources.form_submission.spec import (
    FormSubmissionConditionalUpdateSpec,
    FormSubmissionReadSpec,
    FormSubmissionStatusChoices,
    FormSubmissionWriteSpec,
)
from care.security.authorization.base import AuthorizationController
from care.utils.filters.dummy_filter import DummyUUIDFilter
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404


class FormSubmissionFilters(filters.FilterSet):
    encounter = DummyUUIDFilter()
    patient = DummyUUIDFilter()
    status = MultiSelectFilter(field_name="status")
    questionnaire = filters.CharFilter(
        field_name="questionnaire__slug", lookup_expr="iexact"
    )


class FormSubmissionViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = FormSubmission
    pydantic_model = FormSubmissionWriteSpec
    pydantic_read_model = FormSubmissionReadSpec
    pydantic_update_model = FormSubmissionConditionalUpdateSpec
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FormSubmissionFilters

    def authorize_create(self, instance):
        # TODO : Check if the user is part of questionnaire organization
        if instance.encounter:
            encounter = get_object_or_404(Encounter, external_id=instance.encounter)
            self.authorize_request(encounter=encounter)
        elif instance.patient:
            patient = get_object_or_404(Patient, external_id=instance.patient)
            self.authorize_request(patient=patient)
        return super().authorize_create(instance)

    def authorize_update(self, request_obj, model_instance):
        if model_instance.encounter:
            self.authorize_request(encounter=model_instance.encounter)
        elif model_instance.patient:
            self.authorize_request(patient=model_instance.patient)
        if (
            request_obj is not None
            and request_obj.expected_status is not None
            and model_instance.status != request_obj.expected_status
        ):
            raise ValidationError("Form submission status has changed")
        return super().authorize_update(request_obj, model_instance)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Keep the status check and update locked through the outer batch commit.
        instance = get_object_or_404(
            self.get_queryset().select_for_update(no_key=True),
            **{self.lookup_field: self.kwargs[self.lookup_field]},
        )
        return Response(self.handle_update(instance, request.data))

    def perform_update(self, instance):
        old_instance = FormSubmission.objects.filter(id=instance.id).first()
        if old_instance.status == FormSubmissionStatusChoices.entered_in_error.value:
            raise ValidationError("Form submission is already entered in error")
        if (
            old_instance.status == FormSubmissionStatusChoices.submitted.value
            and instance.status == FormSubmissionStatusChoices.draft.value
        ):
            raise ValidationError(
                "Form submission cannot be set to draft after submission"
            )
        return super().perform_update(instance)

    def authorize_retrieve(self, model_instance):
        self.authorize_update(None, model_instance)

    def authorize_request(self, patient=None, encounter=None):
        if patient and not AuthorizationController.call(
            "can_submit_questionnaire_patient_obj", self.request.user, patient
        ):
            raise PermissionDenied("You do not have permission to view this patient")
        if encounter and not AuthorizationController.call(
            "can_submit_encounter_questionnaire_obj", self.request.user, encounter
        ):
            raise PermissionDenied("You do not have permission to view this encounter")

    def get_queryset(self):
        queryset = super().get_queryset().all()
        if self.action != "list":
            return queryset
        if "encounter" in self.request.GET:
            encounter = get_object_or_404(
                Encounter, external_id=self.request.GET["encounter"]
            )
            self.authorize_request(encounter=encounter)
            return queryset.filter(encounter=encounter)
        if "patient" in self.request.GET:
            patient = get_object_or_404(
                Patient, external_id=self.request.GET["patient"]
            )
            self.authorize_request(patient=patient)
            return queryset.filter(patient=patient)
        raise ValidationError("Patient or encounter is required")
