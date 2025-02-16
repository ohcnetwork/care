from dataclasses import dataclass


@dataclass
class Role:
    """
    This class can be inherited for role classes that are created by default
    """

    name: str
    description: str


VOLUNTEER_ROLE = Role(
    name="Volunteer",
    description="Volunteer at some facility",
)
DOCTOR_ROLE = Role(
    name="Doctor",
    description="Doctor at some facility",
)
NURSE_ROLE = Role(
    name="Nurse",
    description="Nurse at some facility",
)
NURSE_READONLY_ROLE = Role(
    name="Nurse Read Only",
    description="Read-only access for nurses",
)
STAFF_ROLE = Role(
    name="Staff",
    description="Staff at some facility",
)
STAFF_READONLY_ROLE = Role(
    name="Staff Read Only",
    description="Read-only access for staff",
)
GEO_ADMIN = Role(
    name="Geo Admin",
    description="Administrator restricted with geographical boundaries",
)
GEO_ADMIN_READONLY_ROLE = Role(
    name="Geo Admin Read Only",
    description="Read-only access for Geo Admins",
)
FACILITY_ADMIN_ROLE = Role(
    name="Facility Admin",
    description="Administrator of a facility, associated to the person creating the facility.",
)
ADMIN_ROLE = Role(
    name="Admin",
    description="Administrator",
)
# TODO: Add read roles to permissions


class RoleController:
    override_roles = []
    # Override Permission Controllers will be defined from plugs
    internal_roles = [
        DOCTOR_ROLE,
        STAFF_ROLE,
        STAFF_READONLY_ROLE,
        NURSE_ROLE,
        NURSE_READONLY_ROLE,
        GEO_ADMIN,
        GEO_ADMIN_READONLY_ROLE,
        FACILITY_ADMIN_ROLE,
        ADMIN_ROLE,
        VOLUNTEER_ROLE,
    ]

    @classmethod
    def get_roles(cls):
        return cls.internal_roles + cls.override_roles

    @classmethod
    def map_old_role_to_new(cls, old_role):
        mapping = {
            "Transportation": STAFF_ROLE,
            "Pharmacist": STAFF_ROLE,
            "Volunteer": STAFF_ROLE,
            "StaffReadOnly": STAFF_READONLY_ROLE,
            "Staff": STAFF_ROLE,
            "NurseReadOnly": NURSE_READONLY_ROLE,
            "Nurse": NURSE_ROLE,
            "Doctor": DOCTOR_ROLE,
            "Reserved": DOCTOR_ROLE,
            "WardAdmin": GEO_ADMIN,
            "LocalBodyAdmin": GEO_ADMIN,
            "DistrictLabAdmin": GEO_ADMIN,
            "DistrictReadOnlyAdmin": GEO_ADMIN_READONLY_ROLE,
            "DistrictAdmin": GEO_ADMIN,
            "StateLabAdmin": GEO_ADMIN,
            "StateReadOnlyAdmin": GEO_ADMIN_READONLY_ROLE,
            "StateAdmin": GEO_ADMIN,
        }
        return mapping[old_role]

    @classmethod
    def register_role(cls, role: Role):
        # TODO : Do some deduplication Logic
        cls.override_roles.append(role)
