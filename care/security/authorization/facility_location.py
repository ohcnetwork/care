from care.emr.models import FacilityOrganization
from care.emr.models.organization import FacilityOrganizationUser
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.facility_organization import (
    FacilityOrganizationPermissions,
)
from care.security.permissions.location import FacilityLocationPermissions


class FacilityLocationAccess(AuthorizationHandler):
    def can_list_facility_location_obj(self, user, facility, location):
        return self.check_permission_in_facility_organization(
            [FacilityLocationPermissions.can_list_facility_locations.name],
            user,
            facility=facility,
            orgs=location.facility_organization_cache,
        )

    def can_create_facility_location_obj(self, user, location, facility):
        """
        Check if the user has permission to create locations under the given location
        """

        if location:
            # If a parent is present then the user should have permission to create locations under the parent
            return self.check_permission_in_facility_organization(
                [FacilityLocationPermissions.can_write_facility_locations.name],
                user,
                location.facility_organization_cache,
            )
        # If no parent exists, the user must have sufficient permissions in the root organization
        root_organization = FacilityOrganization.objects.get(
            facility=facility, org_type="root"
        )
        return self.check_permission_in_facility_organization(
            [FacilityOrganizationPermissions.can_create_facility_organization.name],
            user,
            [root_organization.id],
        )

    def can_update_facility_location_obj(self, user, location):
        """
        Check if the user has permission to write locations under the given location
        """

        return self.check_permission_in_facility_organization(
            [FacilityLocationPermissions.can_write_facility_locations.name],
            user,
            location.facility_organization_cache,
        )

    def get_accessible_facility_locations(self, qs, user, facility):
        if user.is_superuser:
            return qs

        roles = self.get_role_from_permissions(
            [FacilityLocationPermissions.can_list_facility_locations.name]
        )
        organization_ids = list(
            FacilityOrganizationUser.objects.filter(
                user=user, organization__facility=facility, role_id__in=roles
            ).values_list("organization_id", flat=True)
        )
        return qs.filter(facility_organization_cache__overlap=organization_ids)


AuthorizationController.register_internal_controller(FacilityLocationAccess)
