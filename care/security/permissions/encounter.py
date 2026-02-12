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

ALL_ROLES = [
    ADMIN_ROLE,
    DOCTOR_ROLE,
    NURSE_ROLE,
    ADMINISTRATOR,
    STAFF_ROLE,
    FACILITY_ADMIN_ROLE,
    VOLUNTEER_ROLE,
]

CLINICAL_DATA_ACCESS_ROLES = [
    ADMIN_ROLE,
    DOCTOR_ROLE,
    NURSE_ROLE,
    FACILITY_ADMIN_ROLE,
]


class EncounterPermissions(enum.Enum):
    can_create_encounter = Permission(
        "Can Create encounter",
        "",
        PermissionContext.ENCOUNTER,
        CLINICAL_DATA_ACCESS_ROLES,
    )
    can_list_encounter = Permission(
        "Can list encounters",
        "Clinical data is not associated with this permission",
        PermissionContext.ENCOUNTER,
        CLINICAL_DATA_ACCESS_ROLES,
    )
    can_write_encounter = Permission(
        "Update Encounter non clinical",
        "",
        PermissionContext.ENCOUNTER,
        CLINICAL_DATA_ACCESS_ROLES,
    )
    can_write_encounter_clinical_data = Permission(
        "Update Encounter related clinical data",
        "",
        PermissionContext.ENCOUNTER,
        CLINICAL_DATA_ACCESS_ROLES,
    )
    can_read_encounter = Permission(
        "Can Read encounter",
        "",
        PermissionContext.ENCOUNTER,
        CLINICAL_DATA_ACCESS_ROLES,
    )
    can_read_encounter_clinical_data = Permission(
        "Can Read encounter related clinical data",
        "",
        PermissionContext.ENCOUNTER,
        CLINICAL_DATA_ACCESS_ROLES,
    )
    can_submit_encounter_questionnaire = Permission(
        "Can submit questionnaire about patient encounters",
        "",
        PermissionContext.PATIENT,
        [
            STAFF_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMIN_ROLE,
            FACILITY_ADMIN_ROLE,
        ],
    )
