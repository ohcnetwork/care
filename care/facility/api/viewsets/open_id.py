from django.conf import settings
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response


class OpenIdConfigView(GenericAPIView):
    def get(self, *args, **kwargs):
        return Response(settings.JWKS.as_dict())
