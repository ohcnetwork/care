from care.facility.models.mixins.permissions.asset import DRYAssetPermissions
from care.users.models import User
from config.authentication import MiddlewareAssetAuthentication


class UserAccessMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        model = self.queryset.__dict__["model"]

        if not self.request.user.is_superuser:
            instance = model()
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
                if hasattr(instance, "district"):
                    queryset = queryset.filter(district=self.request.user.district)
                if hasattr(instance, "facility"):
                    queryset = queryset.filter(
                        facility__district=self.request.user.district
                    )
            elif hasattr(instance, "created_by"):
                queryset = queryset.filter(created_by=self.request.user)
        return queryset

    def filter_by_user_scope(self, queryset):
        model = queryset.__dict__["model"]

        if not self.request.user.is_superuser:
            instance = model()
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
                if hasattr(instance, "district_id"):
                    queryset = queryset.filter(district=self.request.user.district)
                if hasattr(instance, "facility_id"):
                    queryset = queryset.filter(
                        facility__district=self.request.user.district
                    )
            elif hasattr(instance, "created_by"):
                queryset = queryset.filter(created_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        model = self.queryset.__dict__["model"]
        kwargs = {}
        if hasattr(model(), "created_by"):
            kwargs["created_by"] = self.request.user
        serializer.save(**kwargs)


class AssetUserAccessMixin:
    """
    Class to override default permissions for a view if the user has an asset attached to it
    """

    asset_permissions = (DRYAssetPermissions,)

    def get_authenticators(self):
        return [MiddlewareAssetAuthentication(), *super().get_authenticators()]

    def get_permissions(self):
        """
        Skips DRYPermissions check for asset users
        """
        if bool(
            self.request.user
            and self.request.user.is_authenticated
            and self.request.user.asset
        ):
            return tuple(permission() for permission in self.asset_permissions)
        return super().get_permissions()
