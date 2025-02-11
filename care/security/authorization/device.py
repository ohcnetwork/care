from care.security.authorization import AuthorizationController, AuthorizationHandler
from care.security.permissions.device import DevicePermissions
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.location import FacilityLocationPermissions


class DeviceAccess(AuthorizationHandler):
    def can_list_devices(self, user):
        return self.check_permission_in_facility_organization(
            [DevicePermissions.can_list_devices.name],
            user,
        )

    def can_manage_devices(self, user):
        return self.check_permission_in_facility_organization(
            [DevicePermissions.can_manage_devices.name],
            user,
        )

    def can_associate_device_encounter(self, user, facility):
        return self.check_permission_in_facility_organization(
            [
                DevicePermissions.can_manage_devices.name,
                EncounterPermissions.can_write_encounter.name,
            ],
            user,
            facility=facility,
        )

    def can_associate_device_location(self, user, facility):
        return self.check_permission_in_facility_organization(
            [
                DevicePermissions.can_manage_devices.name,
                FacilityLocationPermissions.can_write_facility_locations.name,
            ],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(DeviceAccess)
