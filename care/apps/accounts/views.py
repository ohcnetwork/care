import logging
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django_filters import rest_framework as filters
from rest_framework import (
    generics as rest_generics,
    mixins as rest_mixins,
    permissions as rest_permissions,
    status as rest_status,
    viewsets as rest_viewsets,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import (
    models as accounts_models,
    filters as accounts_filters,
    serializers as accounts_serializers,
)
from apps.commons import permissions as commons_permissions

logger = logging.getLogger(__name__)


class UserViewSet(rest_viewsets.ModelViewSet):

    queryset = accounts_models.User.objects.all()
    serializer_class = accounts_serializers.UserSerializer


class UserTypeListViewSet(rest_mixins.ListModelMixin, rest_viewsets.GenericViewSet):
    """
    User Type list view
    """

    queryset = accounts_models.UserType.objects.all()
    serializer_class = accounts_serializers.UserTypeSerializer


class StateListViewSet(rest_mixins.ListModelMixin, rest_viewsets.GenericViewSet):
    """
    State list API view
    """

    queryset = accounts_models.State.objects.all()
    serializer_class = accounts_serializers.StateSerializer


class DistrictListViewSet(rest_mixins.ListModelMixin, rest_viewsets.GenericViewSet):
    """
    District List API view
    """

    queryset = accounts_models.District.objects.all()
    serializer_class = accounts_serializers.DistrictSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = accounts_filters.DistrictFilter


class LoginView(rest_generics.GenericAPIView):
    """
    Login Api for user
    """

    serializer_class = accounts_serializers.LoginSerializer
    permission_classes = (commons_permissions.AnonymousPermission,)
    login_response_serializer = accounts_serializers.LoginResponseSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(self.login_response_serializer(serializer.validated_data["user"]).data)


class LogoutView(APIView):
    """
    Logout Api for User
    """

    permission_classes = (rest_permissions.IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        request.user.auth_token.delete()
        return Response({}, rest_status.HTTP_204_NO_CONTENT)


class ForgotPasswordLinkView(rest_generics.GenericAPIView):
    """
    Sends reset password link to user email
    """

    permission_classes = (commons_permissions.AnonymousPermission,)
    serializer_class = accounts_serializers.ForgotPasswordLinkSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
        else:
            logger.info("Payload: %s, Error: %s", request.data, serializer.errors)
        return Response(status=rest_status.HTTP_200_OK)


class PasswordResetView(rest_generics.GenericAPIView):
    """
    API view for resetting user password
    """

    permission_classes = (commons_permissions.AnonymousPermission,)
    serializer_class = accounts_serializers.ResetPasswordSerializer
    response_serializer_class = accounts_serializers.LoginResponseSerializer
    model = accounts_models.User
    user = None

    def dispatch(self, request, *args, **kwargs):
        queryset = self.model.objects.filter(is_active=True)
        try:
            uid = urlsafe_base64_decode(self.kwargs["uidb64"])
            self.user = queryset.get(pk=uid)
        except self.model.DoesNotExist:
            pass
        else:
            if default_token_generator.check_token(self.user, kwargs["token"]):
                return super().dispatch(request, *args, **kwargs)
        return Response(status=rest_status.HTTP_404_NOT_FOUND)

    def get(self, request, **kwargs):
        """
        Check whether the activation link generated is expired or not for the particular user
        """
        return Response(status=rest_status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        changes the password of the user
        """
        serializer = self.get_serializer(instance=self.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.response_serializer_class(self.user).data, status=rest_status.HTTP_200_OK,)
