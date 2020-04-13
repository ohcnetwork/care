from rest_framework.decorators import action

from care.utils.serializer.history_serializer import ModelHistorySerializer


class HistoryMixin:
    @action(detail=True, methods=["get"])
    def history(self, request, *args, **kwargs):
        obj = self.get_object()
        page = self.paginate_queryset(obj.history.all())
        model = obj.history.__dict__["model"]
        serializer = ModelHistorySerializer(model, page, many=True)
        serializer.is_valid()
        return self.get_paginated_response(serializer.data)
