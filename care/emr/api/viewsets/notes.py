from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models import Encounter
from care.emr.models.notes import NoteMessage, NoteThread
from care.emr.models.patient import Patient
from care.emr.resources.notes.notes_spec import (
    NoteMessageCreateSpec,
    NoteMessageReadSpec,
    NoteMessageUpdateSpec,
)
from care.emr.resources.notes.thread_spec import (
    NoteThreadCreateSpec,
    NoteThreadReadSpec,
    NoteThreadUpdateSpec,
)
from care.security.authorization import AuthorizationController
from care.utils.filters.null_filter import NullFilter
from care.utils.shortcuts import get_object_or_404


def authorize_notes_view(user, patient, encounter=None):
    if AuthorizationController.call("can_view_clinical_data", user, patient):
        return
    if encounter and AuthorizationController.call(
        "can_view_encounter_clinical_data", user, encounter
    ):
        return
    raise PermissionDenied("Permission denied to user")


class NoteThreadFilters(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    encounter_isnull = NullFilter(field_name="encounter")


class NoteThreadViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = NoteThread
    pydantic_model = NoteThreadCreateSpec
    pydantic_read_model = NoteThreadReadSpec
    pydantic_update_model = NoteThreadUpdateSpec
    filterset_class = NoteThreadFilters
    filter_backends = [filters.DjangoFilterBackend]

    def get_patient(self):
        return get_object_or_404(
            Patient, external_id=self.kwargs["patient_external_id"]
        )

    def authorize_create(self, instance):
        patient = self.get_patient()
        if instance.encounter:
            encounter = get_object_or_404(Encounter, external_id=instance.encounter)
            allowed = AuthorizationController.call(
                "can_update_encounter_clinical_data", self.request.user, encounter
            )
        else:
            allowed = AuthorizationController.call(
                "can_write_patient_obj", self.request.user, patient
            )
        if not allowed:
            raise PermissionDenied("You do not have permission for this action")

    def authorize_update(self, request_obj, model_instance):
        patient = model_instance.patient
        if model_instance.encounter:
            allowed = AuthorizationController.call(
                "can_update_encounter_clinical_data",
                self.request.user,
                model_instance.encounter,
            )
        else:
            allowed = AuthorizationController.call(
                "can_write_patient_obj", self.request.user, patient
            )
        if not allowed:
            raise PermissionDenied("You do not have permission for this action")

    def perform_create(self, instance):
        instance.patient = self.get_patient()
        if instance.encounter and instance.encounter.patient != instance.patient:
            raise ValidationError("Patient Mismatch")
        super().perform_create(instance)

    def get_object(self):
        patient = self.get_patient()
        obj = get_object_or_404(
            self.database_model,
            patient=patient,
            **{self.lookup_field: self.kwargs[self.lookup_field]},
        )
        authorize_notes_view(self.request.user, patient, obj.encounter)
        return obj

    def get_queryset(self):
        patient = self.get_patient()
        encounter_obj = None
        if encounter := self.request.GET.get("encounter"):
            encounter_obj = get_object_or_404(Encounter, external_id=encounter)
        authorize_notes_view(self.request.user, patient, encounter_obj)
        return super().get_queryset().filter(patient=patient).order_by("-created_date")


class NoteMessageViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = NoteMessage
    pydantic_model = NoteMessageCreateSpec
    pydantic_read_model = NoteMessageReadSpec
    pydantic_update_model = NoteMessageUpdateSpec

    def get_patient_obj(self):
        return get_object_or_404(
            Patient, external_id=self.kwargs["patient_external_id"]
        )

    def get_thread_obj(self):
        patient = self.get_patient_obj()
        thread = get_object_or_404(
            NoteThread, external_id=self.kwargs["thread_external_id"]
        )
        if thread.patient_id != patient.id:
            raise ValidationError("Thread does not belong to the patient")
        return thread

    def perform_create(self, instance):
        instance.thread = self.get_thread_obj()
        if encounter_id := self.request.data.get("encounter"):
            encounter = get_object_or_404(Encounter, external_id=encounter_id)
            if encounter.patient != instance.thread.patient:
                raise ValidationError("Patient Mismatch")
            instance.encounter = encounter
        instance.patient = instance.thread.patient
        super().perform_create(instance)

    def authorize_thread_write(self, thread):
        if thread.encounter:
            allowed = AuthorizationController.call(
                "can_update_encounter_clinical_data",
                self.request.user,
                thread.encounter,
            )
        else:
            allowed = AuthorizationController.call(
                "can_write_patient_obj", self.request.user, thread.patient
            )
        if not allowed:
            raise PermissionDenied("You do not have permission for this action")

    def authorize_update(self, request_obj, model_instance):
        if self.request.user.id != model_instance.created_by_id:
            raise PermissionDenied("Cannot Update Message Created by Other User")
        thread = self.get_thread_obj()
        self.authorize_thread_write(thread)
        if model_instance.thread_id != thread.id:
            raise ValidationError("Message does not belong to the thread")

    def authorize_create(self, instance):
        thread = self.get_thread_obj()
        self.authorize_thread_write(thread)

    def authorize_retrieve(self, model_instance):
        thread = self.get_thread_obj()
        if model_instance.thread != thread:
            raise ValidationError("Message does not belong to the thread")

    def get_object(self):
        thread = self.get_thread_obj()
        obj = get_object_or_404(
            self.database_model,
            **{self.lookup_field: self.kwargs[self.lookup_field]},
        )
        authorize_notes_view(self.request.user, thread.patient, thread.encounter)
        return obj

    def get_queryset(self):
        patient = self.get_patient_obj()
        encounter_obj = None
        if encounter := self.request.GET.get("encounter"):
            encounter_obj = get_object_or_404(Encounter, external_id=encounter)
        authorize_notes_view(self.request.user, patient, encounter_obj)
        queryset = super().get_queryset().select_related("thread")
        if self.action == "list":
            thread = self.get_thread_obj()
            return queryset.filter(thread=thread).order_by("-created_date")
        return queryset.order_by("-modified_date")
