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


class QuestionnairePermissions(enum.Enum):
    can_write_questionnaire = Permission(
        "Can Create/Update Questionnaires",
        "",
        PermissionContext.QUESTIONNAIRE,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )
    can_archive_questionnaire = Permission(
        "Can Archive Questionnaires",
        "",
        PermissionContext.QUESTIONNAIRE,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )
    can_read_questionnaire = Permission(
        "Can Read Questionnaires",
        "",
        PermissionContext.QUESTIONNAIRE,
        [
            ADMIN_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
            STAFF_ROLE,
            FACILITY_ADMIN_ROLE,
            VOLUNTEER_ROLE,
        ],
    )
    can_submit_questionnaire = Permission(
        "Can Submit Questionnaires",
        "",
        PermissionContext.QUESTIONNAIRE,
        [
            ADMIN_ROLE,
            DOCTOR_ROLE,
            NURSE_ROLE,
            ADMINISTRATOR,
            STAFF_ROLE,
            FACILITY_ADMIN_ROLE,
            VOLUNTEER_ROLE,
        ],
    )
    can_manage_questionnaire = Permission(
        "Can Manage Questionnaires",
        "Allows users to add or remove organizations from questionnaires, ie control Access Management",
        PermissionContext.QUESTIONNAIRE,
        [ADMIN_ROLE, FACILITY_ADMIN_ROLE],
    )
