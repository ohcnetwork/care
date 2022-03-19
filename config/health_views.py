from rest_framework.response import Response
from rest_framework.views import APIView

from config.authentication import MiddlewareAuthentication


class MiddlewareAuthenticationVerifyView(APIView):

    authentication_classes = [MiddlewareAuthentication]

    def get(self, request):
        return Response({})
