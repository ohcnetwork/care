from dataclasses import dataclass


@dataclass
class NewRole:
    """
    This class can be inherited for role classes that are created by default
    """
    name: str
    description: str


DOCTOR_ROLE = NewRole(name="Doctor", description="Some Description Here")  # TODO : Clean description


class Role:
    OVERRIDE_PERMISSION_CONTROLLERS = []
    # Override Permission Controllers will be defined from plugs
    INTERNAL_PERMISSION_CONTROLLERS = [DOCTOR_ROLE]

    @classmethod
    def get_roles(cls):
        return cls.INTERNAL_PERMISSION_CONTROLLERS + cls.OVERRIDE_PERMISSION_CONTROLLERS
