from care.users.models import User


class UserAccessMixin:
    def get_queryset(self):
        queryset = self.queryset
        model = self.queryset.__dict__["model"]

        if not self.request.user.is_superuser:
            instance = model()
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
                if hasattr(instance, "district"):
                    queryset = queryset.filter(district=self.request.user.district)
                if hasattr(instance, "facility"):
                    queryset = queryset.filter(facility__district=self.request.user.district)
            else:
                if hasattr(instance, "created_by"):
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
                    queryset = queryset.filter(facility__district=self.request.user.district)
            else:
                if hasattr(instance, "created_by"):
                    queryset = queryset.filter(created_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        model = self.queryset.__dict__["model"]
        kwargs = {}
        if hasattr(model(), "created_by"):
            kwargs["created_by"] = self.request.user
        serializer.save(**kwargs)
