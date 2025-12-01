from rest_framework.exceptions import PermissionDenied

from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.template import TemplatePermissions


class TemplateAccess(AuthorizationHandler):
    def can_list_facility_template(self, user, facility):
        """
        Check if the user has permission to view templates in the facility
        """
        return self.check_permission_in_facility_organization(
            [TemplatePermissions.can_read_template.name],
            user,
            facility=facility,
        )

    def can_write_facility_template(self, user, facility):
        """
        Check if the user has permission to write templates in the facility
        """
        return self.check_permission_in_facility_organization(
            [TemplatePermissions.can_write_template.name],
            user,
            facility=facility,
            root=True,
        )

    def can_preview_template(self, user, facility):
        """
        Authorize user to preview templates - allows superuser, admin and facility admin
        """
        if user.is_superuser:
            return True

        if self.check_permission_in_facility_organization(
            [TemplatePermissions.can_preview_template.name],
            user,
        ):
            return True

        raise PermissionDenied("You do not have permission to preview templates")

    def can_view_template_schema(self, user, facility):
        """
        Authorize user to view template schema - allows superuser, admin and facility admin
        """
        if user.is_superuser:
            return True

        if self.check_permission_in_facility_organization(
            [TemplatePermissions.can_view_template_schema.name],
            user,
        ):
            return True

        raise PermissionDenied("You do not have permission to access template schema")


AuthorizationController.register_internal_controller(TemplateAccess)
