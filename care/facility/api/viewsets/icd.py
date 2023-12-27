from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from care.facility.static_data.icd11 import ICD11


class ICDViewSet(ViewSet):
    permission_classes = (IsAuthenticated,)

    def serialize_data(self, objects: list[ICD11]):
        return [diagnosis.get_representation() for diagnosis in objects]

    def list(self, request):
        queryset = ICD11
        if query := request.query_params.get("query"):
            queryset = queryset.find(ICD11.label % query.lower()).page(0, 100)
            # todo: add partial word search
        else:
            queryset = queryset.find().sort_by("label").page(0, 100)

        return Response(self.serialize_data(list(queryset)))
