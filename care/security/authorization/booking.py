from care.emr.models.organization import FacilityOrganizationUser
from care.emr.resources.scheduling.schedule.spec import SchedulableResourceTypeOptions
from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.schedule import SchedulePermissions


class BookingAccess(AuthorizationHandler):
    def can_create_booking(self, resource_obj, user):
        facility = resource_obj.facility
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_write_booking.name], user, facility=facility
        )

    def can_list_booking_organization(self, organization, user):
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_write_schedule.name],
            user,
            orgs=[organization.id, *organization.parent_cache],
        )

    def can_list_booking_on_facility(self, user, facility):
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_list_booking.name], user, facility=facility
        )

    def can_list_booking(self, resource_obj, user):
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.practitioner.value
        ):
            return self.can_list_practitioner_booking(
                resource_obj.user, user, resource_obj.facility
            )
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.healthcare_service.value
        ):
            return self.can_list_healthcare_service_booking(
                resource_obj.healthcare_service, user, resource_obj.facility
            )
        if resource_obj.resource_type == SchedulableResourceTypeOptions.location.value:
            return self.can_list_location_booking(
                resource_obj.location, user, resource_obj.facility
            )
        raise ValueError("Invalid resource type")

    def can_list_practitioner_booking(self, obj, user, facility):
        facility_orgs = FacilityOrganizationUser.objects.filter(
            user=obj, organization__facility=facility
        ).values("organization__parent_cache", "organization_id")
        cache = [facility.default_internal_organization_id]
        for facility_org in facility_orgs:
            cache.extend(facility_org["organization__parent_cache"])
            cache.append(facility_org["organization_id"])
        cache = list(set(cache))
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_list_booking.name], user, orgs=cache
        )

    def can_list_healthcare_service_booking(self, obj, user, facility):
        """
        Anyone in the managing organization of the healthcare service can write the schedule
        """
        if obj.managing_organization:
            orgs = [
                obj.managing_organization.parent_cache,
                obj.managing_organization.id,
            ]
            return self.check_permission_in_facility_organization(
                [SchedulePermissions.can_list_booking.name], user, orgs=orgs
            )
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_list_booking.name],
            user,
            facility=obj.facility,
            root=True,
        )

    def can_list_location_booking(self, obj, user, facility):
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_list_booking.name],
            user,
            orgs=obj.facility_organization_cache,
        )

    def can_write_booking(self, resource_obj, user):
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.practitioner.value
        ):
            return self.can_write_practitioner_booking(
                resource_obj.user, user, resource_obj.facility
            )
        if (
            resource_obj.resource_type
            == SchedulableResourceTypeOptions.healthcare_service.value
        ):
            return self.can_write_healthcare_service_booking(
                resource_obj.healthcare_service, user, resource_obj.facility
            )
        if resource_obj.resource_type == SchedulableResourceTypeOptions.location.value:
            return self.can_write_location_booking(
                resource_obj.location, user, resource_obj.facility
            )
        raise ValueError("Invalid resource type")

    def can_write_practitioner_booking(self, obj, user, facility):
        facility_orgs = FacilityOrganizationUser.objects.filter(
            user=obj, organization__facility=facility
        ).values("organization__parent_cache", "organization_id")
        cache = [facility.default_internal_organization_id]
        for facility_org in facility_orgs:
            cache.extend(facility_org["organization__parent_cache"])
            cache.append(facility_org["organization_id"])
        cache = list(set(cache))
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_write_booking.name], user, orgs=cache
        )

    def can_write_healthcare_service_booking(self, obj, user, facility):
        """
        Anyone in the managing organization of the healthcare service can write the schedule
        """
        if obj.managing_organization:
            orgs = [
                obj.managing_organization.parent_cache,
                obj.managing_organization.id,
            ]
            return self.check_permission_in_facility_organization(
                [SchedulePermissions.can_write_booking.name], user, orgs=orgs
            )
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_write_booking.name],
            user,
            facility=obj.facility,
            root=True,
        )

    def can_write_location_booking(self, obj, user, facility):
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_write_booking.name],
            user,
            orgs=obj.facility_organization_cache,
        )

    def can_reschedule_booking(self, user, facility):
        return self.check_permission_in_facility_organization(
            [SchedulePermissions.can_reschedule_booking.name],
            user,
            facility=facility,
        )


AuthorizationController.register_internal_controller(BookingAccess)
