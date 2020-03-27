class UserAccessMixin:
    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        model = self.queryset.__dict__["model"]
        kwargs = {}
        if hasattr(model(), "created_by"):
            kwargs["created_by"] = self.request.user
        serializer.save(**kwargs)
