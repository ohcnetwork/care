from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers, status
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response

User = get_user_model()


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


@extend_schema_view(
    put=extend_schema(tags=["users"]),
    patch=extend_schema(tags=["users"]),
)
class ChangePasswordView(UpdateAPIView):
    """
    An endpoint for changing password.
    """

    serializer_class = ChangePasswordSerializer
    model = User

    def update(self, request, *args, **kwargs):
        self.object = self.request.user
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            check = self.object.check_password(request.data.get("old_password"))
            if not check:
                return Response(
                    {
                        "old_password": [
                            "Wrong password entered. Please check your password."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            return Response({"message": "Password updated successfully"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
