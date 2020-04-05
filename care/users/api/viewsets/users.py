from django.contrib.auth import get_user_model
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.users.api.serializers.user import SignUpSerializer, UserListSerializer, UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and manipulating user instances.
    """

    queryset = User.objects.all().select_related("local_body", "district", "state")
    lookup_field = "username"

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                DRYPermissions(),
            ]
        else:
            return [
                IsAuthenticated(),
                DRYPermissions(),
            ]

    def get_serializer_class(self):
        if self.action == "list" and not self.request.user.is_superuser:
            return UserListSerializer
        elif self.action == "create":
            return SignUpSerializer
        else:
            return UserSerializer

    @action(detail=False, methods=["GET"])
    def getcurrentuser(self, request):
        return Response(
            status=status.HTTP_200_OK, data=UserSerializer(request.user, context={"request": request}).data,
        )
