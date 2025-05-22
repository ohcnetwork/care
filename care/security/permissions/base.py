from enum import Enum

from care.security.permissions.device import DevicePermissions
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.facility import FacilityPermissions
from care.security.permissions.facility_organization import (
    FacilityOrganizationPermissions,
)
from care.security.permissions.location import FacilityLocationPermissions
from care.security.permissions.organization import OrganizationPermissions
from care.security.permissions.patient import PatientPermissions
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.security.permissions.user import UserPermissions
from care.security.permissions.user_schedule import UserSchedulePermissions


class PermissionHandler:
    pass


class PermissionController:
    """
    This class defines all permissions used within care.
    This class is used to abstract all operations related to permissions
    """

    override_permission_handlers = []
    # Override Permission Controllers will be defined from plugs

    internal_permission_handlers = [
        FacilityPermissions,
        QuestionnairePermissions,
        OrganizationPermissions,
        FacilityOrganizationPermissions,
        EncounterPermissions,
        PatientPermissions,
        UserPermissions,
        UserSchedulePermissions,
        FacilityLocationPermissions,
        DevicePermissions,
    ]

    cache = {}

    @classmethod
    def build_cache(cls):
        """
        Iterate through the entire permission library and create a list of permissions and associated Metadata
        """
        for handler in (
            cls.internal_permission_handlers + cls.override_permission_handlers
        ):
            for permission in handler:
                cls.cache[permission.name] = permission.value

    @classmethod
    def get_permissions(cls):
        if not cls.cache:
            cls.build_cache()
        return cls.cache

    @classmethod
    def get_enum(cls):
        if not cls.cache:
            cls.build_cache()

        return Enum("PermissionEnum", {name: name for name in cls.cache}, type=str)
