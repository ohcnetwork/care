from dry_rest_permissions.generics import DRYPermissions


class IsAssetUser:
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.asset
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class DRYAssetPermissions(DRYPermissions):
    """
    Adds additional prefix for asset users to the permission names.
    """

    global_permissions = False

    def _get_action(self, action):
        return f"asset_{super()._get_action(action)}"
