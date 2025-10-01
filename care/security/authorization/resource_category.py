from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.resource_category import ResourceCategoryPermissions


class ResourceCategoryAccess(AuthorizationHandler):
    def can_list_facility_resource_category(self, user, facility):
        """
        Check if the user has permission to view resource categories in the facility
        """
        return self.check_permission_in_facility_organization(
            [ResourceCategoryPermissions.can_read_resource_category.name],
            user,
            facility=facility,
        )

    def can_write_facility_resource_category(self, user, facility):
        """
        Check if the user has permission to view resource categories in the facility
        """
        return self.check_permission_in_facility_organization(
            [ResourceCategoryPermissions.can_write_resource_category.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(ResourceCategoryAccess)
