from rest_framework.exceptions import PermissionDenied

from care.emr.models import Encounter, Patient
from care.emr.models.consent import Consent
from care.emr.models.diagnostic_report import DiagnosticReport
from care.emr.models.referral import Referral
from care.emr.models.service_request import ServiceRequest
from care.emr.resources.file_upload.spec import FileTypeChoices
from care.security.authorization import AuthorizationController
from care.utils.shortcuts import get_object_or_404


def file_authorizer(user, file_type, associating_id, permission):  # noqa PLR0912
    allowed = False
    if file_type == FileTypeChoices.patient.value:
        patient_obj = get_object_or_404(Patient, external_id=associating_id)
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, patient_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_write_patient_obj", user, patient_obj
            )
    elif file_type == FileTypeChoices.encounter.value:
        encounter_obj = get_object_or_404(Encounter, external_id=associating_id)
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, encounter_obj.patient
            ) or AuthorizationController.call(
                "can_view_encounter_clinical_data", user, encounter_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_update_encounter_clinical_data", user, encounter_obj
            )
    elif file_type == FileTypeChoices.consent.value:
        encounter_obj = get_object_or_404(Consent, external_id=associating_id).encounter
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, encounter_obj.patient
            ) or AuthorizationController.call(
                "can_view_encounter_clinical_data", user, encounter_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_update_encounter_clinical_data", user, encounter_obj
            )
    elif file_type == FileTypeChoices.diagnostic_report.value:
        diagnostic_report_obj = get_object_or_404(
            DiagnosticReport, external_id=associating_id
        )
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_read_diagnostic_report",
                user,
                diagnostic_report_obj.service_request,
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_write_diagnostic_report",
                user,
                diagnostic_report_obj.service_request,
            )
    elif file_type == FileTypeChoices.service_request.value:
        service_request_obj = get_object_or_404(
            ServiceRequest, external_id=associating_id
        )
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_read_service_request", user, service_request_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_write_service_request", user, service_request_obj
            )
    elif file_type == FileTypeChoices.referral.value:
        referral = get_object_or_404(Referral, external_id=associating_id)
        if permission == "read":
            allowed = AuthorizationController.call("can_read_referral", user, referral)
        elif permission == "write":
            allowed = AuthorizationController.call("can_write_referral", user, referral)
    if not allowed:
        raise PermissionDenied("Cannot View File")
