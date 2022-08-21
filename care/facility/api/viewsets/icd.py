from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


def serailize_data(icd11_object):
    result = []
    for object in icd11_object:
        result.append({"id": object.ID, "label": object.label})
    return result


class ICDViewSet(ViewSet):
    # permission_classes = (IsAuthenticated,)
    permission_classes = ()

    def list(self, request):
        from care.facility.static_data.icd11 import ICDDiseases
        return Response(serailize_data(ICDDiseases[0:10]))
