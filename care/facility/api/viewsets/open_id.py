from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response


class PublicJWKsView(GenericAPIView):
    """
    Retrieve the OpenID Connect configuration
    """

    authentication_classes = ()
    permission_classes = ()

    @method_decorator(cache_page(60 * 60 * 24))
    def get(self, *args, **kwargs):
        return Response(settings.JWKS.as_dict())
