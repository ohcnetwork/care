from rest_framework import serializers

from care.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "user_type",
            "district",
            "phone_number",
            "gender",
            "age",
            "skill",
            "verified",
        ]
