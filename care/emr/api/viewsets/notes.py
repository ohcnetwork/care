from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404

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


class NoteThreadViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = NoteThread
    pydantic_model = NoteThreadCreateSpec
    pydantic_read_model = NoteThreadUpdateSpec
    pydantic_update_model = NoteThreadReadSpec

    def get_patient(self):
        return get_object_or_404(
            Patient, external_id=self.kwargs["patient_external_id"]
        )

    def authorize_create(self, instance):
        patient = self.get_patient()
        if instance.encounter:
            encounter = get_object_or_404(Encounter, external_id=instance.encounter)
            allowed = AuthorizationController.call(
                "can_update_encounter_obj", self.request.user, encounter
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
                "can_update_encounter_obj", self.request.user, model_instance.encounter
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
            raise ValueError("Patient Mismatch")
        super().perform_create(instance)

    def get_object(self):
        # TODO Authorise Based on encounter and permission
        return super().get_object()

    def get_queryset(self):
        patient = self.get_patient()
        if not AuthorizationController.call(
            "can_view_clinical_data", self.request.user, patient
        ):
            if encounter := self.request.GET.get("encounter"):
                encounter_obj = get_object_or_404(Encounter, external_id=encounter)
                if not AuthorizationController.call(
                    "can_view_encounter_obj", self.request.user, encounter_obj
                ):
                    raise PermissionDenied("Permission denied to user")
            else:
                raise PermissionDenied("Permission denied to user")

        queryset = super().get_queryset().filter(patient=patient)
        return queryset.order_by("-created_date")


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

    def perform_create(self, instance):
        instance.thread = get_object_or_404(
            NoteThread, external_id=self.kwargs["thread_external_id"]
        )
        super().perform_create(instance)

    def authorize_update(self, request_obj, model_instance):
        if self.request.user != model_instance.created_by:
            raise PermissionDenied("Cannot Update Message Created by Other User")
        self.authorize_create({})

    def authorize_create(self, instance):
        thread = get_object_or_404(
            NoteThread, external_id=self.kwargs["thread_external_id"]
        )
        if thread.encounter:
            allowed = AuthorizationController.call(
                "can_update_encounter_obj", self.request.user, thread.encounter
            )
        else:
            allowed = AuthorizationController.call(
                "can_write_patient_obj", self.request.user, thread.patient
            )
        if not allowed:
            raise PermissionDenied("You do not have permission for this action")

    def get_queryset(self):
        if not AuthorizationController.call(
            "can_view_clinical_data", self.request.user, self.get_patient_obj()
        ):
            if encounter := self.request.GET.get("encounter"):
                encounter_obj = get_object_or_404(Encounter, external_id=encounter)
                if not AuthorizationController.call(
                    "can_view_encounter_obj", self.request.user, encounter_obj
                ):
                    raise PermissionDenied("Permission denied to user")
            else:
                raise PermissionDenied("Permission denied to user")

        return (
            super()
            .get_queryset()
            .filter(thread__external_id=self.kwargs["thread_external_id"])
            .order_by("-created_date")
        )
