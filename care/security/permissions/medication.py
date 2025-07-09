import enum

from care.security.permissions.constants import Permission, PermissionContext
from care.security.roles.role import (
    ADMIN_ROLE,
    DOCTOR_ROLE,
    FACILITY_ADMIN_ROLE,
    NURSE_ROLE,
    STAFF_ROLE,
)


class MedicationPermissions(enum.Enum):
    is_pharmacist = Permission(
        "Pharmacist in Care",
        "Pharmacists in Care have access to all medication requests and can create dispenses for patients",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE, STAFF_ROLE, DOCTOR_ROLE, NURSE_ROLE],
    )
    read_medication_dispense = Permission(
        "Medication Dispense Read",
        "Users can read medication dispenses",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE, STAFF_ROLE, DOCTOR_ROLE, NURSE_ROLE],
    )
    write_medication_dispense = Permission(
        "Write Medication Dispense",
        "Users can write medication dispenses",
        PermissionContext.FACILITY,
        [FACILITY_ADMIN_ROLE, ADMIN_ROLE, STAFF_ROLE, DOCTOR_ROLE, NURSE_ROLE],
    )
