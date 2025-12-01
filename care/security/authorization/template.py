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

    def can_preview_template(self, user):
        """
        Authorize user to preview templates - allows superuser, admin and facility admin
        """
        return self.check_permission_in_facility_organization(
            [TemplatePermissions.can_preview_template.name],
            user,
        )

    def can_view_template_schema(self, user):
        """
        Authorize user to view template schema - allows superuser, admin and facility admin
        """
        return self.check_permission_in_facility_organization(
            [TemplatePermissions.can_view_template_schema.name],
            user,
        )

    def can_generate_report_from_template(self, user, facility):
        """
        Check if the user has permission to generate reports from templates
        """
        return self.check_permission_in_facility_organization(
            [TemplatePermissions.can_generate_report_from_template.name],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(TemplateAccess)
