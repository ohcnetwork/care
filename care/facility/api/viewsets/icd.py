from re import IGNORECASE

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


def serailize_data(icd11_object):
    result = []
    for _obj in icd11_object:
        obj = _obj[0] if isinstance(_obj, tuple) else _obj
        result.append({"id": obj.id, "label": obj.label})
    return result


class ICDViewSet(ViewSet):
    permission_classes = (IsAuthenticated,)

    def list(self, request):
        from care.facility.static_data.icd11 import ICDDiseases

        queryset = ICDDiseases
        if request.GET.get("query", False):
            query = request.GET.get("query")
            queryset = queryset.where(
                label=queryset.re_match(r".*" + query + r".*", IGNORECASE),
            )  # can accept regex from FE if needed.
        return Response(serailize_data(queryset[0:100]))
