from care.emr.models import Encounter
from care.emr.reports.authorizers.base import BaseReportAuthorizer
from care.security.authorization import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class EncounterReportAuthorizer(BaseReportAuthorizer):
    def authorize_read(self, user, associating_id: str) -> bool:
        encounter_obj = get_object_or_404(Encounter, external_id=associating_id)
        return AuthorizationController.call(
            "can_view_clinical_data", user, encounter_obj.patient
        ) or AuthorizationController.call("can_view_encounter_obj", user, encounter_obj)

    def authorize_write(self, user, associating_id: str) -> bool:
        encounter_obj = get_object_or_404(Encounter, external_id=associating_id)
        return AuthorizationController.call(
            "can_generate_report_for_encounter", user, encounter_obj
        )
