from care.emr.models import FacilityOrganization
from care.security.authorization import AuthorizationHandler
from care.security.permissions.template import TemplatePermissions


class TemplateAccess(AuthorizationHandler):
    def can_write_template_in_facility(self, user, facility):
        if user.is_superuser:
            return True
        root_organization = FacilityOrganization.objects.get(
            facility=facility, org_type="root"
        )
        return self.check_permission_in_organization(
            permissions=[TemplatePermissions.can_manage_template.name],
            user=user,
            orgs=[root_organization],
        )

    def can_list_template_in_facility(self, user, facility):
        if user.is_superuser:
            return True
        root_organization = FacilityOrganization.objects.get(
            facility=facility, org_type="root"
        )
        return self.check_permission_in_organization(
            permissions=[TemplatePermissions.can_list_template.name],
            user=user,
            orgs=[root_organization],
        )

    def can_write_template_in_instance(self, user):
        return user.is_superuser

    def can_list_template_in_instance(self, user):
        return user.is_superuser
