from django.conf import settings
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class OpenIdConfigView(GenericAPIView):
    """
    Retrieve the OpenID Connect configuration
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, *args, **kwargs):
        return Response(settings.JWKS.as_dict())
