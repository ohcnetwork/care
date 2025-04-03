# Deprecated

from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.emr.units.units_client import units_client


class UnitsView(GenericViewSet):
    def list(self, request, *args, **kwargs):
        results = units_client.search(request.query_params.get("search", ""))
        return Response({"count": len(results), "results": results})
