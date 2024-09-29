from dataclasses import dataclass


@dataclass
class Role:
    """
    This class can be inherited for role classes that are created by default
    """
    name: str
    description: str


DOCTOR_ROLE = Role(name="Doctor", description="Some Description Here")  # TODO : Clean description


class RoleController:
    override_roles = []
    # Override Permission Controllers will be defined from plugs
    internal_roles = [DOCTOR_ROLE]

    @classmethod
    def get_roles(cls):
        return cls.internal_roles + cls.override_roles

    @classmethod
    def register_role(cls, role: Role):
        # TODO : Do some deduplication Logic
        cls.override_roles.append(role)
