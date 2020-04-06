from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from care.users.api.serializers.lsg import DistrictSerializer, LocalBodySerializer, StateSerializer
from care.users.models import GENDER_CHOICES
from config.serializers import ChoiceField

User = get_user_model()


class SignUpSerializer(serializers.ModelSerializer):
    user_type = ChoiceField(choices=User.TYPE_CHOICES)
    gender = ChoiceField(choices=GENDER_CHOICES)
    password = serializers.CharField(write_only=True)
    # until we start supporting other states
    state = serializers.PrimaryKeyRelatedField(read_only=True)

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
            "local_body",
            "district",
            "state",
            "phone_number",
            "gender",
            "age",
        )

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data.get("password"))
        return super().create(validated_data)


class UserSerializer(SignUpSerializer):
    user_type = ChoiceField(choices=User.TYPE_CHOICES, read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "user_type",
            "local_body",
            "district",
            "state",
            "phone_number",
            "gender",
            "age",
            "is_superuser",
            "local_body_object",
            "district_object",
            "state_object",
        )

    extra_kwargs = {"url": {"lookup_field": "username"}}


class UserListSerializer(serializers.ModelSerializer):
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "local_body_object", "district_object", "state_object")
