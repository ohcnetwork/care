from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from care.users.api.serializers.user import UserBaseMinimumSerializer
from config.authentication import (
    MiddlewareAssetAuthentication,
    MiddlewareAuthentication,
)


class MiddlewareAuthenticationVerifyView(APIView):
    authentication_classes = [MiddlewareAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserBaseMinimumSerializer(request.user).data)


class MiddlewareAssetAuthenticationVerifyView(APIView):
    authentication_classes = [MiddlewareAssetAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserBaseMinimumSerializer(request.user).data)
