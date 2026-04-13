import enum
from dataclasses import dataclass, field


class RoleContext(enum.Enum):
    FACILITY = "FACILITY"
    GOVT_ORG = "GOVT_ORG"
    ROLE_ORG = "ROLE_ORG"


@dataclass
class Role:
    """
    This class can be inherited for role classes that are created by default
    """

    name: str
    description: str
    contexts: list[RoleContext] = field(default_factory=list)


VOLUNTEER_ROLE = Role(
    name="Volunteer",
    description="Volunteer at some facility",
    contexts=[RoleContext.FACILITY, RoleContext.GOVT_ORG],
)
DOCTOR_ROLE = Role(
    name="Doctor",
    description="Doctor at some facility",
    contexts=[RoleContext.FACILITY, RoleContext.GOVT_ORG],
)
NURSE_ROLE = Role(
    name="Nurse",
    description="Nurse at some facility",
    contexts=[RoleContext.FACILITY, RoleContext.GOVT_ORG],
)
STAFF_ROLE = Role(
    name="Staff",
    description="Staff at some facility",
    contexts=[RoleContext.FACILITY, RoleContext.GOVT_ORG],
)
PHARMACIST_ROLE = Role(
    name="Pharmacist",
    description="Pharmacist at some facility",
    contexts=[RoleContext.FACILITY],
)
ADMINISTRATOR = Role(
    name="Administrator",
    description="Administrator at a given boundary",
    contexts=[RoleContext.FACILITY, RoleContext.GOVT_ORG],
)
FACILITY_ADMIN_ROLE = Role(
    name="Facility Admin",
    description="Administrator of a facility, associated to the person creating the facility.",
    contexts=[RoleContext.FACILITY],
)
ADMIN_ROLE = Role(
    name="Admin",
    description="Admin",
    contexts=[RoleContext.FACILITY, RoleContext.GOVT_ORG],
)

ROLE_ORGANIZATION_ADMIN_ROLE = Role(
    name="Admin",
    description="Administrator of a role organization",
    contexts=[RoleContext.ROLE_ORG],
)
ROLE_ORGANIZATION_MANAGER_ROLE = Role(
    name="Manager",
    description="Manager of a role organization",
    contexts=[RoleContext.ROLE_ORG],
)
ROLE_ORGANIZATION_MEMBER_ROLE = Role(
    name="Member",
    description="Member of a role organization",
    contexts=[RoleContext.ROLE_ORG],
)


class RoleController:
    override_roles = []
    # Override Permission Controllers will be defined from plugs
    internal_roles = [
        DOCTOR_ROLE,
        STAFF_ROLE,
        NURSE_ROLE,
        ADMINISTRATOR,
        FACILITY_ADMIN_ROLE,
        ADMIN_ROLE,
        VOLUNTEER_ROLE,
        PHARMACIST_ROLE,
        ROLE_ORGANIZATION_ADMIN_ROLE,
        ROLE_ORGANIZATION_MANAGER_ROLE,
        ROLE_ORGANIZATION_MEMBER_ROLE,
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
            "StaffReadOnly": STAFF_ROLE,
            "Staff": STAFF_ROLE,
            "NurseReadOnly": NURSE_ROLE,
            "Nurse": NURSE_ROLE,
            "Doctor": DOCTOR_ROLE,
            "Reserved": DOCTOR_ROLE,
            "WardAdmin": ADMINISTRATOR,
            "LocalBodyAdmin": ADMINISTRATOR,
            "DistrictLabAdmin": ADMINISTRATOR,
            "DistrictReadOnlyAdmin": ADMINISTRATOR,
            "DistrictAdmin": ADMINISTRATOR,
            "StateLabAdmin": ADMINISTRATOR,
            "StateReadOnlyAdmin": ADMINISTRATOR,
            "StateAdmin": ADMINISTRATOR,
        }
        return mapping[old_role]

    @classmethod
    def register_role(cls, role: Role):
        # TODO : Do some deduplication Logic
        cls.override_roles.append(role)
