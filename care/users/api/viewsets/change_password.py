from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers, status
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response

User = get_user_model()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        user = self.context["request"].user
        try:
            validate_password(value, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


@extend_schema_view(
    put=extend_schema(tags=["users"]),
    patch=extend_schema(tags=["users"]),
)
class ChangePasswordView(UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    model = User

    def update(self, request, *args, **kwargs):
        self.object = self.request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not self.object.check_password(
            serializer.validated_data.get("old_password")
        ):
            return Response(
                {
                    "old_password": [
                        "Wrong password entered. Please check your password."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        self.object.set_password(serializer.validated_data.get("new_password"))
        self.object.save()
        return Response({"message": "Password updated successfully"})
