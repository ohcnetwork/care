from care.facility.models import FacilityUser
from care.security.controllers.controller import AuthorizationHandler, PermissionDenied


class FacilityAccess(AuthorizationHandler):

    actions = ["can_read_facility"]

    def can_read_facility(self , user, facility_id):
        self.check_permission(user, facility_id)
        # Since the old method relied on a facility-user relationship, check that
        # This can be removed when the migrations have been completed
        if not FacilityUser.objects.filter(facility_id = facility_id , user=user).exists():
            raise PermissionDenied("Access to this facility is denied")
        return True, True
