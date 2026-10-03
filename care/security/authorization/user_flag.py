from care.security.authorization import AuthorizationController
from care.security.authorization.base import AuthorizationHandler


class UserFlagAccess(AuthorizationHandler):
    def can_read_user_flag(self, user):
        """
        Check if the user has permission to read user flags
        Only superusers can read user flags
        """
        return user.is_superuser

    def can_write_user_flag(self, user):
        """
        Check if the user has permission to write user flags
        Only superusers can write user flags
        """
        return user.is_superuser


AuthorizationController.register_internal_controller(UserFlagAccess)
