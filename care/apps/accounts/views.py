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


class UserViewSet(rest_viewsets.ModelViewSet):

    queryset = accounts_models.User.objects.all()
    serializer_class = accounts_serializers.UserSerializer


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
        return Response(self.login_response_serializer(serializer.validated_data['user']).data)


class LogoutView(APIView):
    """
    Logout Api for User
    """
    permission_classes = (rest_permissions.IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        request.user.auth_token.delete()
        return Response({}, rest_status.HTTP_204_NO_CONTENT)
