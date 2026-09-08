from django.db.models import Q

from care.emr.models.organization import FacilityOrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.valueset import ValueSetPermissions


class ValueSetAccess(AuthorizationHandler):
    def can_access_facility_valueset(self, user, facility, valueset, read_only):
        """
        Permission to access a value set for a specific facility
        """
        if read_only:
            permission = [ValueSetPermissions.can_read_valueset.name]
            return self.check_permission_in_facility_organization(
                permission,
                user,
                facility=facility,
                orgs=valueset.internal_organization_cache,
            )
        permission = [ValueSetPermissions.can_write_valueset.name]
        return self.check_permission_in_facility_organization(
            permission, user, facility, root=True
        )

    def can_access_facility_organization_valueset(
        self, user, facility_organization, read_only
    ):
        """
        Permission to access a questionnaire for a specific facility
        """
        if read_only:
            permission = [ValueSetPermissions.can_read_valueset.name]
        else:
            permission = [ValueSetPermissions.can_write_valueset.name]
        return self.check_permission_in_facility_organization(
            permission,
            user,
            facility=facility_organization.facility,
            orgs=[*facility_organization.parent_cache, facility_organization.id],
        )

    def can_access_user_valueset_in_faciltiy(self, user, facility, read_only):
        """
        Permission to write a value set for a specific facility as a user
        """
        if read_only:
            permission = [ValueSetPermissions.can_read_valueset.name]
        else:
            permission = [ValueSetPermissions.can_write_valueset.name]
        return self.check_permission_in_facility_organization(
            permission,
            user,
            facility=facility,
        )

    def get_filtered_valuesets(self, qs, user):
        if user.is_superuser:
            return qs
        roles = self.get_role_from_permissions(
            [ValueSetPermissions.can_read_valueset.name]
        )
        facility_organization_ids = list(
            FacilityOrganizationUser.objects.filter(
                user=user, role_id__in=roles
            ).values_list("organization_id", flat=True)
        )
        return qs.filter(
            Q(auth_context="instance")
            | Q(internal_organization_cache__overlap=facility_organization_ids)
            | Q(auth_context="user", created_by=user)
        )


AuthorizationController.register_internal_controller(ValueSetAccess)
