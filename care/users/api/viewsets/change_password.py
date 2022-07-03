from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

User = get_user_model()

class ChangePasswordSerializer(serializers.Serializer):
    model = User

    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def check_old_password(self, instance, validated_data):
        if instance.check_password(validated_data.get("old_password")):
            return False
        return True

class ChangePasswordView(UpdateAPIView):
        """
        An endpoint for changing password.
        """
        serializer_class = ChangePasswordSerializer
        model = User
        permission_classes = (IsAuthenticated,)

        def get_object(self):
            return self.request.user

        def update(self, request, *args, **kwargs):
            self.object = self.request.user
            serializer = self.get_serializer(data=request.data)

            if serializer.is_valid():
                check = serializer.check_old_password(instance=self.object, validated_data=request.data)
                if not check:
                    return Response({"old_password": ["Wrong password entered. Please check your password."]}, status=status.HTTP_400_BAD_REQUEST)
                self.object.set_password(serializer.data.get("new_password"))
                self.object.save()
                return Response({"message": "Password updated successfully"})

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)