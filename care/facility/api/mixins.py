from care.facility.models import User


class UserAccessMixin:
    def get_queryset(self):
        queryset = self.queryset
        model = self.queryset.__dict__["model"]
        if self.request.user.is_superuser:
            pass
        elif self.request.user.user_type == User.TYPE_VALUE_MAP["DistrictAdmin"]:
            if hasattr(model(), "district"):
                queryset = queryset.filter(district=self.request.user.district)
        else:
            if hasattr(model(), "created_by"):
                queryset = queryset.filter(created_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        model = self.queryset.__dict__["model"]
        kwargs = {}
        if hasattr(model(), "created_by"):
            kwargs["created_by"] = self.request.user
        serializer.save(**kwargs)
