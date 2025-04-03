from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404

from care.emr.models import Encounter, Patient
from care.security.authorization import AuthorizationController


class EncounterBasedAuthorizationBase:
    def get_patient_obj(self):
        return get_object_or_404(
            Patient, external_id=self.kwargs["patient_external_id"]
        )

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_update_encounter_obj", self.request.user, model_instance.encounter
        ):
            raise PermissionDenied("You do not have permission to update encounter")

    def authorize_create(self, instance):
        encounter = get_object_or_404(Encounter, external_id=instance.encounter)
        if not AuthorizationController.call(
            "can_update_encounter_obj", self.request.user, encounter
        ):
            raise PermissionDenied("You do not have permission to update encounter")

    def authorize_destroy(self, instance):
        if not AuthorizationController.call(
            "can_update_encounter_obj", self.request.user, instance.encounter
        ):
            raise PermissionDenied("You do not have permission to update encounter")

    def authorize_read_encounter(self):
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
