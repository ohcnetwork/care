from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from rest_framework import exceptions, serializers

from care.facility.api.serializers.facility import FacilityBareMinimumSerializer
from care.facility.models import READ_ONLY_USER_TYPES, Facility, FacilityUser
from care.users.api.serializers.lsg import (
    DistrictSerializer,
    LocalBodySerializer,
    StateSerializer,
)
from care.users.api.serializers.skill import SkillSerializer
from care.users.models import GENDER_CHOICES
from care.utils.queryset.facility import get_home_facility_queryset
from care.utils.serializer.external_id_field import ExternalIdSerializerField
from config.serializers import ChoiceField

User = get_user_model()


class SignUpSerializer(serializers.ModelSerializer):
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
            "doctor_qualification",
            "doctor_experience_commenced_on",
            "doctor_medical_council_registration",
            "ward",
            "local_body",
            "district",
            "state",
            "phone_number",
            "alt_phone_number",
            "gender",
            "age",
        )

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data.get("password"))
        return super().create(validated_data)

    def validate(self, attrs):
        validated = super().validate(attrs)
        if "user_type" in attrs and attrs["user_type"] == "Doctor":
            if not attrs.get("doctor_qualification"):
                raise serializers.ValidationError(
                    {
                        "doctor_qualification": "Field required for Doctor User Type",
                    }
                )

            if not attrs.get("doctor_experience_commenced_on"):
                raise serializers.ValidationError(
                    {
                        "doctor_experience_commenced_on": "Field required for Doctor User Type",
                    }
                )

            if attrs["doctor_experience_commenced_on"] > date.today():
                raise serializers.ValidationError(
                    {
                        "doctor_experience_commenced_on": "Experience cannot be in the future",
                    }
                )

            if not attrs.get("doctor_medical_council_registration"):
                raise serializers.ValidationError(
                    {
                        "doctor_medical_council_registration": "Field required for Doctor User Type",
                    }
                )

        return validated


class UserCreateSerializer(SignUpSerializer):
    password = serializers.CharField(required=False)
    facilities = serializers.ListSerializer(
        child=serializers.UUIDField(), required=False, allow_empty=True, write_only=True
    )
    home_facility = ExternalIdSerializerField(
        queryset=Facility.objects.all(), required=False
    )

    class Meta:
        model = User
        include = ("facilities",)
        exclude = (
            "is_superuser",
            "is_staff",
            "is_active",
            "last_login",
            "date_joined",
            "verified",
            "deleted",
            "groups",
            "user_permissions",
            "created_by",
        )

    def validate_facilities(self, facility_ids):
        if facility_ids:
            if (
                len(facility_ids)
                != Facility.objects.filter(external_id__in=facility_ids).count()
            ):
                available_facility_ids = Facility.objects.filter(
                    external_id__in=facility_ids
                ).values_list("external_id", flat=True)
                not_found_ids = list(set(facility_ids) - set(available_facility_ids))
                raise serializers.ValidationError(
                    f"Some facilities are not available - {', '.join([str(_id) for _id in not_found_ids])}"
                )
        return facility_ids

    def validate_ward(self, value):
        if (
            value is not None
            and value != self.context["created_by"].ward
            and not self.context["created_by"].is_superuser
            and not self.context["created_by"].user_type
            >= User.TYPE_VALUE_MAP["LocalBodyAdmin"]
        ):
            raise serializers.ValidationError("Cannot create for a different Ward")
        return value

    def validate_local_body(self, value):
        if (
            value is not None
            and value != self.context["created_by"].local_body
            and not self.context["created_by"].is_superuser
            and not self.context["created_by"].user_type
            >= User.TYPE_VALUE_MAP["DistrictAdmin"]
        ):
            raise serializers.ValidationError(
                "Cannot create for a different local body"
            )
        return value

    def validate_district(self, value):
        if (
            value is not None
            and value != self.context["created_by"].district
            and not self.context["created_by"].is_superuser
            and not self.context["created_by"].user_type
            >= User.TYPE_VALUE_MAP["StateAdmin"]
        ):
            raise serializers.ValidationError("Cannot create for a different district")
        return value

    def validate_state(self, value):
        if (
            value is not None
            and value != self.context["created_by"].state
            and not self.context["created_by"].is_superuser
        ):
            raise serializers.ValidationError("Cannot create for a different state")
        return value

    def validate(self, attrs):
        validated = super(UserCreateSerializer, self).validate(attrs)
        if "home_facility" in validated:
            allowed_facilities = get_home_facility_queryset(self.context["created_by"])
            if not allowed_facilities.filter(id=validated["home_facility"].id).exists():
                raise exceptions.ValidationError(
                    {
                        "home_facility": "Cannot create users with different Home Facility"
                    }
                )

        if self.context["created_by"].user_type in READ_ONLY_USER_TYPES:
            if validated["user_type"] not in READ_ONLY_USER_TYPES:
                raise exceptions.ValidationError(
                    {
                        "user_type": [
                            "Read only users can create other read only users only"
                        ]
                    }
                )

        if (
            self.context["created_by"].user_type == User.TYPE_VALUE_MAP["Staff"]
            and validated["user_type"] == User.TYPE_VALUE_MAP["Doctor"]
        ):
            pass
        elif (
            validated["user_type"] > self.context["created_by"].user_type
            and not self.context["created_by"].is_superuser
        ):
            raise exceptions.ValidationError(
                {
                    "user_type": [
                        "User cannot create another user with higher permissions"
                    ]
                }
            )

        if (
            not validated.get("ward")
            and not validated.get("local_body")
            and not validated.get("district")
            and not validated.get("state")
        ):
            raise exceptions.ValidationError(
                {"__all__": ["One of ward, local body, district or state is required"]}
            )

        return validated

    def facility_query(self, user):
        queryset = Facility.objects.all()
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(district=user.district)
        elif user.user_type >= User.TYPE_VALUE_MAP["LocalBodyAdmin"]:
            queryset = queryset.filter(local_body=user.local_body)
        else:
            queryset = queryset.filter(users__id__exact=user.id)
        return queryset

    def create(self, validated_data):
        with transaction.atomic():
            facilities = validated_data.pop("facilities", [])
            user = User.objects.create_user(
                created_by=self.context["created_by"], verified=True, **validated_data
            )
            facility_query = self.facility_query(self.context["created_by"])
            if facilities:
                facility_objs = facility_query.filter(external_id__in=facilities)
                facility_user_objs = [
                    FacilityUser(
                        facility=facility,
                        user=user,
                        created_by=self.context["created_by"],
                    )
                    for facility in facility_objs
                ]
                FacilityUser.objects.bulk_create(facility_user_objs)
            return user


class UserSerializer(SignUpSerializer):
    user_type = ChoiceField(choices=User.TYPE_CHOICES, read_only=True)
    created_by = serializers.CharField(source="created_by_user", read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)
    home_facility_object = FacilityBareMinimumSerializer(
        source="home_facility", read_only=True
    )

    home_facility = ExternalIdSerializerField(queryset=Facility.objects.all())

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "user_type",
            "doctor_qualification",
            "doctor_experience_commenced_on",
            "doctor_medical_council_registration",
            "created_by",
            "home_facility",
            "local_body",
            "district",
            "state",
            "phone_number",
            "alt_phone_number",
            "gender",
            "age",
            "is_superuser",
            "verified",
            "home_facility_object",
            "local_body_object",
            "district_object",
            "state_object",
            "pf_endpoint",
            "pf_p256dh",
            "pf_auth",
        )
        read_only_fields = (
            "is_superuser",
            "verified",
            "user_type",
            "ward",
            "local_body",
            "district",
            "state",
            "pf_endpoint",
            "pf_p256dh",
            "pf_auth",
        )

    extra_kwargs = {"url": {"lookup_field": "username"}}

    def validate(self, attrs):
        validated = super(UserSerializer, self).validate(attrs)
        if "home_facility" in validated:
            allowed_facilities = get_home_facility_queryset(
                self.context["request"].user
            )
            if not allowed_facilities.filter(id=validated["home_facility"].id).exists():
                raise exceptions.ValidationError(
                    {
                        "home_facility": "Cannot create users with different Home Facility"
                    }
                )
        return validated


class UserBaseMinimumSerializer(serializers.ModelSerializer):
    user_type = ChoiceField(choices=User.TYPE_CHOICES, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "username",
            "email",
            "last_name",
            "user_type",
            "last_login",
        )


class UserAssignedSerializer(serializers.ModelSerializer):
    user_type = ChoiceField(choices=User.TYPE_CHOICES, read_only=True)
    home_facility_object = FacilityBareMinimumSerializer(
        source="home_facility", read_only=True
    )
    skills = serializers.SerializerMethodField()

    def get_skills(self, obj):
        qs = obj.skills.filter(userskill__deleted=False)
        return SkillSerializer(qs, many=True).data

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "username",
            "email",
            "last_name",
            "alt_phone_number",
            "user_type",
            "last_login",
            "home_facility_object",
            "doctor_qualification",
            "doctor_experience_commenced_on",
            "doctor_medical_council_registration",
            "skills",
        )


class UserListSerializer(serializers.ModelSerializer):
    local_body_object = LocalBodySerializer(source="local_body", read_only=True)
    district_object = DistrictSerializer(source="district", read_only=True)
    state_object = StateSerializer(source="state", read_only=True)
    user_type = ChoiceField(choices=User.TYPE_CHOICES, read_only=True)
    created_by = serializers.CharField(source="created_by_user", read_only=True)
    home_facility_object = FacilityBareMinimumSerializer(
        source="home_facility", read_only=True
    )
    home_facility = ExternalIdSerializerField(queryset=Facility.objects.all())

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "username",
            "local_body_object",
            "district_object",
            "state_object",
            "user_type",
            "doctor_qualification",
            "doctor_experience_commenced_on",
            "doctor_medical_council_registration",
            "created_by",
            "last_login",
            "home_facility_object",
            "home_facility",
        )
