from django.contrib.auth import get_user_model
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from care.users.api.serializers.user import SignUpSerializer, UserCreateSerializer, UserListSerializer, UserSerializer

User = get_user_model()


class UserViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, GenericViewSet,
):
    """
    A viewset for viewing and manipulating user instances.
    """

    queryset = User.objects.all().select_related("local_body", "district", "state")
    lookup_field = "username"

    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )

    # def get_permissions(self):
    #     return [
    #         DRYPermissions(),
    #         IsAuthenticated(),
    #     ]
    # if self.request.method == "POST":
    #     return [
    #         DRYPermissions(),
    #     ]
    # else:
    #     return [
    #         IsAuthenticated(),
    #         DRYPermissions(),
    #     ]

    def get_serializer_class(self):
        if self.action == "list" and not self.request.user.is_superuser:
            return UserListSerializer
        elif self.action == "add_user":
            return UserCreateSerializer
        # elif self.action == "create":
        #     return SignUpSerializer
        else:
            return UserSerializer

    @action(detail=False, methods=["GET"])
    def getcurrentuser(self, request):
        return Response(
            status=status.HTTP_200_OK, data=UserSerializer(request.user, context={"request": request}).data,
        )

    @action(detail=False, methods=["POST"])
    def add_user(self, request, *args, **kwargs):
        password = request.data.pop("password", User.objects.make_random_password(length=8))
        serializer = UserCreateSerializer(
            data={**request.data, "password": password}, context={"created_by": request.user}
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.create(serializer.validated_data)

        response_data = UserCreateSerializer(user).data
        response_data["password"] = password
        return Response(data=response_data, status=status.HTTP_201_CREATED)
