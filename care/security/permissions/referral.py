import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    ADMINISTRATOR,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
    ROLE_ORGANIZATION_ADMIN_ROLE,
    ROLE_ORGANIZATION_MANAGER_ROLE,
    ROLE_ORGANIZATION_MEMBER_ROLE,
    STAFF_ROLE,
)

REFERRAL_ROLES = [
    ADMIN_ROLE,
    ADMINISTRATOR,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
    STAFF_ROLE,
    ROLE_ORGANIZATION_ADMIN_ROLE,
    ROLE_ORGANIZATION_MANAGER_ROLE,
    ROLE_ORGANIZATION_MEMBER_ROLE,
]


class ReferralPermissions(enum.Enum):
    can_manage_referral_availability = Permission(
        "Can Manage Referral Availabilities",
        "Publish and update referral availability for an entity",
        PermissionContext.ORGANIZATION,
        [
            ADMIN_ROLE,
            ADMINISTRATOR,
            FACILITY_ADMIN_ROLE,
            ROLE_ORGANIZATION_ADMIN_ROLE,
            ROLE_ORGANIZATION_MANAGER_ROLE,
        ],
    )
    can_read_referral_availability = Permission(
        "Can Read Referral Availabilities",
        "View private referral availability and its questionnaires",
        PermissionContext.ORGANIZATION,
        REFERRAL_ROLES,
    )
    can_submit_referral_availability = Permission(
        "Can Submit to Private Referral Availabilities",
        "Start a referral to a private destination",
        PermissionContext.ORGANIZATION,
        REFERRAL_ROLES,
    )
    can_create_referral = Permission(
        "Can Create Referrals",
        "Start a referral from a patient or encounter",
        PermissionContext.PATIENT,
        REFERRAL_ROLES,
    )
    can_read_referral = Permission(
        "Can Read Referrals",
        "Read referrals at the origin patient, encounter, or destination entity",
        PermissionContext.PATIENT,
        REFERRAL_ROLES,
    )
    can_write_referral = Permission(
        "Can Update Referrals",
        "Update referrals, assignments, attachments, and referral discussions",
        PermissionContext.PATIENT,
        REFERRAL_ROLES,
    )
