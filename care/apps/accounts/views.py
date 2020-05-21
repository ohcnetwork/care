from rest_framework.viewsets import ModelViewSet

from apps.accounts import (
    models as accounts_models,
    serializers as accounts_serializers
)


class UserViewSet(ModelViewSet):

    queryset = accounts_models.User.objects.all()
    serializer_class = accounts_serializers.UserSerializer

