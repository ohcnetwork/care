from redis_om import FindQuery
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from care.facility.static_data.icd11 import ICD11
from care.utils.static_data.helpers import query_builder


class ICDViewSet(ViewSet):
    permission_classes = (IsAuthenticated,)

    def serialize_data(self, objects: list[ICD11]):
        return [diagnosis.get_representation() for diagnosis in objects]

    def list(self, request):
        try:
            limit = min(int(request.query_params.get("limit")), 20)
        except (ValueError, TypeError):
            limit = 20

        query = []
        if q := request.query_params.get("query"):
            query.append(ICD11.label % query_builder(q))

        result = FindQuery(expressions=query, model=ICD11, limit=limit).execute(
            exhaust_results=False
        )
        return Response(self.serialize_data(result))
