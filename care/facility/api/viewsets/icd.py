from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


def serailize_data(icd11_object):
    result = []
    for object in icd11_object:
        if type(object) == tuple:
            object = object[0]
        result.append({"id": object.ID, "label": object.label})
    return result


class ICDViewSet(ViewSet):
    permission_classes = (IsAuthenticated,)

    def list(self, request):
        from care.facility.static_data.icd11 import ICDDiseases

        queryset = ICDDiseases
        if request.GET.get("query", False):
            queryset = queryset.search.label(request.GET["query"], limit=100)
        return Response(serailize_data(queryset[0:100]))
