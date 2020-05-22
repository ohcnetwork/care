from rest_framework import permissions as rest_permissions


class AnonymousPermission(rest_permissions.BasePermission):
    """
    Don't Allows access to authenticated users.
    """
    def has_permission(self, request, view):
        return not(request.user and request.user.is_authenticated)
