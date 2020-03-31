from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from care.users.models import GENDER_CHOICES
from config.serializers import ChoiceField

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    user_type = ChoiceField(choices=User.TYPE_CHOICES)
    gender = ChoiceField(choices=GENDER_CHOICES)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "user_type",
            "district",
            "phone_number",
            "gender",
            "age",
        )

        extra_kwargs = {"url": {"lookup_field": "username"}}

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data.get("password"))
        return super().create(validated_data)


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name")
