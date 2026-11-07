from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler


class FacilityFlagAccess(AuthorizationHandler):
    def can_read_facility_flag(self, user):
        """
        Check if the user has permission to read facility flags
        Only superusers can read facility flags
        """
        return user.is_superuser

    def can_write_facility_flag(self, user):
        """
        Check if the user has permission to write facility flags
        Only superusers can write facility flags
        """
        return user.is_superuser


AuthorizationController.register_internal_controller(FacilityFlagAccess)
