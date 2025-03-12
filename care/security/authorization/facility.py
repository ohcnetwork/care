from care.emr.models.organization import FacilityOrganization, FacilityOrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.facility import FacilityPermissions


class FacilityAccess(AuthorizationHandler):
    def find_roles_on_facility_sub_orgs(self, user, facility):
        facility_orgs = FacilityOrganization.objects.filter(
            facility=facility, org_type__in=["team", "dept"]
        ).values_list("id", flat=True)
        roles = FacilityOrganizationUser.objects.filter(
            organization_id__in=facility_orgs, user=user
        ).values_list("role_id", flat=True)
        return set(roles)

    def find_roles_on_facility_root(self, user, facility):
        root_organization = FacilityOrganization.objects.get(
            facility=facility, org_type="root"
        )
        roles = FacilityOrganizationUser.objects.filter(
            organization_id=root_organization, user=user
        ).values_list("role_id", flat=True)
        return set(roles)

    def can_create_facility(self, user):
        return self.check_permission_in_organization(
            [FacilityPermissions.can_create_facility.name], user
        )

    def can_update_facility_obj(self, user, facility):
        return self.check_permission_in_organization(
            [FacilityPermissions.can_update_facility.name],
            user,
            orgs=facility.geo_organization_cache,
        ) or self.check_permission_in_facility_organization(
            [FacilityPermissions.can_update_facility.name], user, facility=facility
        )


AuthorizationController.register_internal_controller(FacilityAccess)
