from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.tag_config import TagConfigPermissions


class TagConfigAccess(AuthorizationHandler):
    def can_list_facility_tag_config(self, user, facility):
        """
        Check if the user has permission to view tag configs in the facility
        """
        return self.check_permission_in_facility_organization(
            [TagConfigPermissions.can_read_tag_config.name],
            user,
            facility=facility,
        )

    def can_write_facility_tag_config(self, user, facility):
        """
        Check if the user has permission to view tag configs in the facility
        """
        return self.check_permission_in_facility_organization(
            [TagConfigPermissions.can_write_tag_config.name],
            user,
            facility=facility,
            root=True,
        )

    def can_apply_tag_config(self, user, tag_config):
        if user.is_superuser:
            return True

        if tag_config.facility_organization:
            allowed_orgs = [tag_config.facility_organization.id]
            allowed_orgs.extend(tag_config.facility_organization.parent_cache)

            return self.check_permission_in_facility_organization(
                [TagConfigPermissions.can_apply_tag_config.name],
                user,
                orgs=allowed_orgs,
                facility=tag_config.facility,
            )

        if tag_config.organization:
            allowed_orgs = [tag_config.organization.id]
            allowed_orgs.extend(tag_config.organization.parent_cache)

            return self.check_permission_in_organization(
                [TagConfigPermissions.can_apply_tag_config.name],
                user,
                orgs=allowed_orgs,
            )

        # If no managing organization, check basic facility permission
        if tag_config.facility:
            return self.check_permission_in_facility_organization(
                [TagConfigPermissions.can_apply_tag_config.name],
                user,
                facility=tag_config.facility,
            )

        # For instance-level tags with no managing org, allow if user has basic apply permission
        return self.check_permission_in_facility_organization(
            [TagConfigPermissions.can_apply_tag_config.name],
            user,
        )


AuthorizationController.register_internal_controller(TagConfigAccess)
