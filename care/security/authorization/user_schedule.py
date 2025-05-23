from care.emr.models.organization import FacilityOrganizationUser
from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler
from care.security.permissions.user_schedule import UserSchedulePermissions


class UserScheduleAccess(AuthorizationHandler):
    def can_list_user_schedule(self, user, facility):
        """
        Check if the user has permission to list schedules in a facility
        """
        return self.check_permission_in_facility_organization(
            [UserSchedulePermissions.can_list_user_schedule.name],
            user,
            facility=facility,
        )

    def can_create_appointment(self, user, facility):
        """
        Check if the user has permission to create schedules in a facility
        """
        return self.check_permission_in_facility_organization(
            [UserSchedulePermissions.can_create_appointment.name],
            user,
            facility=facility,
        )

    def can_reschedule_appointment(self, user, facility):
        """
        Check if the user has permission to re-schedule in a facility
        """
        return self.check_permission_in_facility_organization(
            [UserSchedulePermissions.can_reschedule_appointment.name],
            user,
            facility=facility,
        )

    def can_list_facility_user_booking(self, user, facility):
        """
        Check if the user has permission to list schedules in a facility
        """
        return self.check_permission_in_facility_organization(
            [UserSchedulePermissions.can_list_user_booking.name],
            user,
            facility=facility,
        )

    def can_write_user_schedule(self, user, facility, schedule_user):
        """
        Check if the user has permission to write schedules in the facility
        """
        facility_orgs = FacilityOrganizationUser.objects.filter(
            user=schedule_user, organization__facility=facility
        ).values("organization__parent_cache", "organization_id")
        cache = []
        for facility_org in facility_orgs:
            cache.extend(facility_org["organization__parent_cache"])
            cache.append(facility_org["organization_id"])
        cache = list(set(cache))
        return self.check_permission_in_facility_organization(
            [UserSchedulePermissions.can_write_user_schedule.name], user, orgs=cache
        )

    def can_write_user_booking(self, user, facility, schedule_user):
        """
        Check if the user has permission to write schedules in the facility
        """
        facility_orgs = FacilityOrganizationUser.objects.filter(
            user=schedule_user, organization__facility=facility
        ).values("organization__parent_cache", "organization_id")
        cache = []
        for facility_org in facility_orgs:
            cache.extend(facility_org["organization__parent_cache"])
            cache.append(facility_org["organization_id"])
        cache = list(set(cache))
        return self.check_permission_in_facility_organization(
            [UserSchedulePermissions.can_write_user_booking.name], user, orgs=cache
        )


AuthorizationController.register_internal_controller(UserScheduleAccess)
