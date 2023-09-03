from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenVerifyView, TokenViewBase

from care.users.api.serializers.auth import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

User = get_user_model()


class TokenObtainPairView(TokenViewBase):
    """
    Generate access and refresh tokens for a user.

    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """

    serializer_class = TokenObtainPairSerializer

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TokenRefreshView(TokenViewBase):
    """
    Refresh access token.

    Takes a refresh type JSON web token and returns an access type JSON web
    token if the refresh token is valid.
    """

    serializer_class = TokenRefreshSerializer

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AnnotatedTokenVerifyView(TokenVerifyView):
    """
    Verify tokens are valid.

    Takes a token and returns a boolean of whether it is a valid JSON web token
    for this project.
    """

    @extend_schema(tags=["auth"])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
