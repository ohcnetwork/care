from care.abdm.utils.api_call import Facility
from care.facility.models import FacilityUser
from care.security.authorization.base import (
    AuthorizationHandler,
    PermissionDeniedError,
)


class FacilityAccess(AuthorizationHandler):
    actions = ["can_read_facility"]
    queries = ["allowed_facilities"]

    def can_read_facility(self, user, facility_id):
        self.check_permission(user, facility_id)
        # Since the old method relied on a facility-user relationship, check that
        # This can be removed when the migrations have been completed
        if not FacilityUser.objects.filter(facility_id=facility_id, user=user).exists():
            raise PermissionDeniedError
        return True, True

    def allowed_facilities(self, user):
        return Facility.objects.filter(users__id__exact=user.id)
