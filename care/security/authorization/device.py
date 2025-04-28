from care.security.authorization import AuthorizationController, AuthorizationHandler
from care.security.permissions.device import DevicePermissions


class DeviceAccess(AuthorizationHandler):
    def can_read_devices_on_location(self, user, location):
        return self.check_permission_in_facility_organization(
            [DevicePermissions.can_list_devices.name],
            user,
            location.facility_organization_cache,
        )

    def can_read_device(self, user, device):
        org_permission = self.check_permission_in_facility_organization(
            [DevicePermissions.can_list_devices.name],
            user,
            device.facility_organization_cache,
        )
        location_permission = False
        if device.current_location:
            location_permission = self.check_permission_in_facility_organization(
                [DevicePermissions.can_list_devices.name],
                user,
                device.current_location.facility_organization_cache,
            )
        return org_permission or location_permission

    def can_create_device(self, user, facility):
        return self.check_permission_in_facility_organization(
            [DevicePermissions.can_manage_devices.name], user, facility=facility
        )

    def can_manage_device(self, user, device):
        return self.check_permission_in_facility_organization(
            [DevicePermissions.can_manage_devices.name],
            user,
            device.facility_organization_cache,
        )

    def can_manage_device_associations_to_encounters(self, user, device):
        return self.check_permission_in_facility_organization(
            [DevicePermissions.can_manage_device_associations_to_encounters.name],
            user,
            device.facility_organization_cache,
        )


AuthorizationController.register_internal_controller(DeviceAccess)
