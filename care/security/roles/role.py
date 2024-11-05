from dataclasses import dataclass

from care.security.permissions.base import PermissionContext


@dataclass
class Role:
    """
    This class can be inherited for role classes that are created by default
    """

    name: str
    description: str
    context: PermissionContext


DOCTOR_ROLE = Role(
    name="Doctor",
    description="Some Description Here",
    context=PermissionContext.FACILITY,
)  # TODO : Clean description
STAFF_ROLE = Role(
    name="Staff",
    description="Some Description Here",
    context=PermissionContext.FACILITY,
)  # TODO : Clean description
ADMIN_ROLE = Role(
    name="Facility Admin",
    description="Some Description Here",
    context=PermissionContext.FACILITY,
)  # TODO : Clean description


class RoleController:
    override_roles = []
    # Override Permission Controllers will be defined from plugs
    internal_roles = [DOCTOR_ROLE, STAFF_ROLE]

    @classmethod
    def get_roles(cls):
        return cls.internal_roles + cls.override_roles

    @classmethod
    def map_old_role_to_new(cls, old_role):
        mapping = {
            "Transportation": STAFF_ROLE,
            "Pharmacist": STAFF_ROLE,
            "Volunteer": STAFF_ROLE,
            "StaffReadOnly": STAFF_ROLE,
            "Staff": STAFF_ROLE,
            "NurseReadOnly": STAFF_ROLE,
            "Nurse": STAFF_ROLE,
            "Doctor": DOCTOR_ROLE,
            "Reserved": DOCTOR_ROLE,
            "WardAdmin": STAFF_ROLE,
            "LocalBodyAdmin": ADMIN_ROLE,
            "DistrictLabAdmin": ADMIN_ROLE,
            "DistrictReadOnlyAdmin": ADMIN_ROLE,
            "DistrictAdmin": ADMIN_ROLE,
            "StateLabAdmin": ADMIN_ROLE,
            "StateReadOnlyAdmin": ADMIN_ROLE,
            "StateAdmin": ADMIN_ROLE,
        }
        return mapping[old_role]

    @classmethod
    def register_role(cls, role: Role):
        # TODO : Do some deduplication Logic
        cls.override_roles.append(role)
