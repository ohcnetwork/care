from django.contrib.auth import get_user_model
from rest_framework import serializers

from config.serializers import ChoiceField

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    user_type = ChoiceField(choices=User.TYPE_CHOICES)
    district = ChoiceField(choices=User.DISTRICT_CHOICES)
    gender = ChoiceField(choices=User.GENDER_CHOICES)
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
            "skill",
        )

        extra_kwargs = {"url": {"lookup_field": "username"}}


