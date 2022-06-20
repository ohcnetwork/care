from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from care.facility.api.serializers.icd import ICDSerializer
from care.facility.models.icd import ICDDisease
from care.utils.icd.search_diseases import get_diseases


class ICDView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        manual_parameters=[openapi.Parameter(
            'search_text', openapi.IN_QUERY, description="search term", type=openapi.TYPE_STRING)]
    )
    def get(self, request):
        search_text = request.GET.get('search_text') or ''
        diseases = {i: ICDDisease(id=disease['id'], name=disease['name'], reference_url=disease['reference_url']) for (
            i, disease) in enumerate(get_diseases(search_text))}
        serializer = ICDSerializer(
            instance=diseases.values(), many=True)
        return Response(serializer.data)
