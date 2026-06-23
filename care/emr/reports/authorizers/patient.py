from care.emr.models.patient import Patient
from care.emr.reports.authorizers.base import BaseReportAuthorizer
from care.security.authorization import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class PatientReportAuthorizer(BaseReportAuthorizer):
    def authorize_read(self, user, associating_id: str) -> bool:
        patient_obj = get_object_or_404(Patient, external_id=associating_id)
        return AuthorizationController.call("can_view_clinical_data", user, patient_obj)

    def authorize_write(self, user, associating_id: str) -> bool:
        patient_obj = get_object_or_404(Patient, external_id=associating_id)
        return AuthorizationController.call("can_write_patient_obj", user, patient_obj)
