from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.users.api.serializers.user import UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and manipulating user instances.
    """

    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "username"

    def get_permissions(self):
        if self.request.method == "POST":
            self.permission_classes = ()  # allows signup
        else:
            self.permission_classes = (IsAuthenticated,)
        return super().get_permissions()

    def get_queryset(self):
        if self.request.method == "DELETE" or self.request.method == "PUT":
            return self.queryset.filter(id=self.request.user.id)
        else:
            return self.queryset

    @action(detail=False, methods=["GET"])
    def getcurrentuser(self, request):
        return Response(
            status=status.HTTP_200_OK, data=self.serializer_class(request.user, context={"request": request}).data,
        )
