from rest_framework.decorators import action

from care.facility.models import User
from care.utils.serializer.history_serializer import ModelHistorySerializer


class UserAccessMixin:
    def get_queryset(self):
        queryset = self.queryset
        model = self.queryset.__dict__["model"]
        if self.request.user.is_superuser:
            pass
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            if hasattr(model(), "district"):
                queryset = queryset.filter(district=self.request.user.district)
            if hasattr(model(), "facility"):
                queryset = queryset.filter(facility__district=self.request.user.district)
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


class HistoryMixin:
    @action(detail=True, methods=["get"])
    def history(self, request, *args, **kwargs):
        obj = self.get_object()
        page = self.paginate_queryset(obj.history.all())
        model = obj.history.__dict__["model"]
        serializer = ModelHistorySerializer(model, page, many=True)
        serializer.is_valid()
        return self.get_paginated_response(serializer.data)
