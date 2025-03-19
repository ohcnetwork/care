from django.db.models import Q

from care.emr.models.organization import FacilityOrganizationUser
from care.emr.resources.encounter.constants import COMPLETED_CHOICES
from care.security.authorization.base import (
    AuthorizationController,
    AuthorizationHandler,
)
from care.security.permissions.encounter import EncounterPermissions


class EncounterAccess(AuthorizationHandler):
    def find_roles_on_encounter(self, user, encounter):
        # Through Facility Organization
        org_cache = [*encounter.facility_organization_cache]
        # Through Location
        if encounter.current_location:
            org_cache.extend(encounter.current_location.facility_organization_cache)
        roles = FacilityOrganizationUser.objects.filter(
            organization_id__in=org_cache, user=user
        ).values_list("role_id", flat=True)
        return set(roles)

    def can_create_encounter_obj(self, user, facility):
        """
        Check if the user has permission to create encounter under this facility
        """
        return self.check_permission_in_facility_organization(
            [EncounterPermissions.can_create_encounter.name], user, facility=facility
        )

    def can_view_encounter_obj(self, user, encounter):
        """
        Check if the user has permission to read encounter under this facility
        """
        orgs = [*encounter.facility_organization_cache]
        if encounter.current_location:
            orgs.extend(encounter.current_location.facility_organization_cache)

        return self.check_permission_in_facility_organization(
            [EncounterPermissions.can_read_encounter.name],
            user,
            orgs=orgs,
        )

    def can_submit_encounter_questionnaire_obj(self, user, encounter):
        """
        Check if the user has permission to read encounter under this facility
        """
        if encounter.status in COMPLETED_CHOICES:
            # Cannot write to a closed encounter
            return False

        orgs = [*encounter.facility_organization_cache]
        if encounter.current_location:
            orgs.extend(encounter.current_location.facility_organization_cache)

        return self.check_permission_in_facility_organization(
            [EncounterPermissions.can_submit_encounter_questionnaire.name],
            user,
            orgs=orgs,
        )

    def can_update_encounter_obj(self, user, encounter):
        """
        Check if the user has permission to create encounter under this facility
        """
        if encounter.status in COMPLETED_CHOICES:
            # Cannot write to a closed encounter
            return False
        orgs = [*encounter.facility_organization_cache]
        if encounter.current_location:
            orgs.extend(encounter.current_location.facility_organization_cache)
        return self.check_permission_in_facility_organization(
            [EncounterPermissions.can_write_encounter.name],
            user,
            orgs=orgs,
        )

    def get_filtered_encounters(self, qs, user, facility):
        if user.is_superuser:
            return qs
        roles = self.get_role_from_permissions(
            [EncounterPermissions.can_list_encounter.name]
        )
        organization_ids = list(
            FacilityOrganizationUser.objects.filter(
                user=user, organization__facility=facility, role_id__in=roles
            ).values_list("organization_id", flat=True)
        )
        return qs.filter(
            Q(facility_organization_cache__overlap=organization_ids)
            | Q(current_location__facility_organization_cache__overlap=organization_ids)
        )


AuthorizationController.register_internal_controller(EncounterAccess)
