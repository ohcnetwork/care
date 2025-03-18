import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    ADMINISTRATOR,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
    STAFF_ROLE,
    VOLUNTEER_ROLE,
)


class PatientPermissions(enum.Enum):
    can_create_patient = Permission(
        "Can Create Patient",
        "",
        PermissionContext.PATIENT,
        [
            STAFF_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
            ADMIN_ROLE,
            FACILITY_ADMIN_ROLE,
        ],
    )
    can_write_patient = Permission(
        "Can Update a Patient's data",
        "",
        PermissionContext.PATIENT,
        [
            STAFF_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
            ADMIN_ROLE,
            FACILITY_ADMIN_ROLE,
        ],
    )
    can_list_patients = Permission(
        "Can list patients",
        "",
        PermissionContext.PATIENT,
        [
            STAFF_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
            ADMIN_ROLE,
            FACILITY_ADMIN_ROLE,
            VOLUNTEER_ROLE,
        ],
    )
    can_view_clinical_data = Permission(
        "Can view clinical data about patients",
        "",
        PermissionContext.PATIENT,
        [STAFF_ROLE, DOCTOR_ROLE, NURSE_ROLE, ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )  # To be split into finer grain permissions
    can_view_questionnaire_responses = Permission(
        "Can view questionnaire responses on patient",
        "",
        PermissionContext.PATIENT,
        [
            VOLUNTEER_ROLE,
            STAFF_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMIN_ROLE,
            FACILITY_ADMIN_ROLE,
            ADMINISTRATOR,
        ],
    )
    can_submit_patient_questionnaire = Permission(
        "Can submit questionnaire about patients",
        "",
        PermissionContext.PATIENT,
        [
            VOLUNTEER_ROLE,
            STAFF_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMIN_ROLE,
            FACILITY_ADMIN_ROLE,
            ADMINISTRATOR,
        ],
    )
