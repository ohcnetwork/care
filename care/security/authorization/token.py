from care.emr.models.organization import FacilityOrganizationUser
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions
from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.token import TokenPermissions


class TokenCategoryAccess(AuthorizationHandler):
    def can_list_facility_token_category(self, user, facility):
        """
        Check if the user has permission to view token category in the facility
        """
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_list_token_category.name],
            user,
            facility=facility,
        )

    def can_write_facility_token_category(self, user, facility):
        """
        Check if the user has permission to view token category in the facility
        """
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_write_token_category.name],
            user,
            facility=facility,
            root=True,
        )


AuthorizationController.register_internal_controller(TokenCategoryAccess)


class TokenAccess(AuthorizationHandler):
    def can_write_token(self, resource_obj, user):
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.practitioner.value
        ):
            return self.can_write_practitioner_token(
                resource_obj.user, user, resource_obj.facility
            )
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.healthcare_service.value
        ):
            return self.can_write_healthcare_service_token(
                resource_obj.healthcare_service, user
            )
        if resource_obj.resource_type == SchedulableResourceTypeOptions.location.value:
            return self.can_write_location_token(resource_obj.location, user)
        raise ValueError("Invalid resource type")

    def can_update_token(self, resource_obj, user):
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.practitioner.value
        ):
            return self.can_write_practitioner_token(
                resource_obj.user, user, resource_obj.facility
            )
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.healthcare_service.value
        ):
            return self.can_write_healthcare_service_token(
                resource_obj.healthcare_service,
                user,
            )
        if resource_obj.resource_type == SchedulableResourceTypeOptions.location.value:
            return self.can_write_location_token(resource_obj.location, user)
        raise ValueError("Invalid resource type")

    def can_list_token_on_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_list_token.name], user, facility=facility
        )

    def can_list_token(self, resource_obj, user):
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.practitioner.value
        ):
            return self.can_read_practitioner_token(
                resource_obj.user, user, resource_obj.facility
            )
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.healthcare_service.value
        ):
            return self.can_read_healthcare_service_token(
                resource_obj.healthcare_service, user
            )
        if resource_obj.resource_type == SchedulableResourceTypeOptions.location.value:
            return self.can_read_location_token(resource_obj.location, user)
        raise ValueError("Invalid resource type")

    def can_write_practitioner_token(self, obj, user, facility):
        facility_orgs = FacilityOrganizationUser.objects.filter(
            user=obj, organization__facility=facility
        ).values("organization__parent_cache", "organization_id")
        cache = [facility.default_internal_organization_id]
        for facility_org in facility_orgs:
            cache.extend(facility_org["organization__parent_cache"])
            cache.append(facility_org["organization_id"])
        cache = list(set(cache))
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_write_token.name], user, orgs=cache
        )

    def can_write_healthcare_service_token(self, obj, user):
        """
        Anyone in the managing organization of the healthcare service can write the schedule
        """
        if obj.managing_organization:
            orgs = [
                obj.managing_organization.parent_cache,
                obj.managing_organization.id,
            ]
            return self.check_permission_in_facility_organization(
                [TokenPermissions.can_write_token.name], user, orgs=orgs
            )
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_write_token.name],
            user,
            facility=obj.facility,
            root=True,
        )

    def can_write_location_token(self, obj, user):
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_write_token.name],
            user,
            orgs=obj.facility_organization_cache,
        )

    def can_read_practitioner_token(self, obj, user, facility):
        facility_orgs = FacilityOrganizationUser.objects.filter(
            user=obj, organization__facility=facility
        ).values("organization__parent_cache", "organization_id")
        cache = [facility.default_internal_organization_id]
        for facility_org in facility_orgs:
            cache.extend(facility_org["organization__parent_cache"])
            cache.append(facility_org["organization_id"])
        cache = list(set(cache))
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_list_token.name], user, orgs=cache
        )

    def can_read_healthcare_service_token(self, obj, user):
        """
        Anyone in the managing organization of the healthcare service can write the schedule
        """
        if obj.managing_organization:
            orgs = [
                obj.managing_organization.parent_cache,
                obj.managing_organization.id,
            ]
            return self.check_permission_in_facility_organization(
                [TokenPermissions.can_list_token.name], user, orgs=orgs
            )
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_list_token.name],
            user,
            facility=obj.facility,
            root=True,
        )

    def can_read_location_token(self, obj, user):
        return self.check_permission_in_facility_organization(
            [TokenPermissions.can_list_token.name],
            user,
            orgs=obj.facility_organization_cache,
        )


AuthorizationController.register_internal_controller(TokenAccess)
