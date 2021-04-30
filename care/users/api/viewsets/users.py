from django.contrib.auth import get_user_model
from django.core.cache import cache
from django_filters import rest_framework as filters
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import filters as rest_framework_filters
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.facility import FacilityBasicInfoSerializer
from care.facility.models.facility import Facility, FacilityUser
from care.users.api.serializers.user import UserCreateSerializer, UserListSerializer, UserSerializer

User = get_user_model()


def remove_facility_user_cache(user_id):
    key = "user_facilities:" + str(user_id)
    cache.delete(key)
    return True


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


INVERSE_USER_TYPE = inverse_choices(User.TYPE_CHOICES)


class UserFilterSet(filters.FilterSet):
    first_name = filters.CharFilter(field_name="first_name", lookup_expr="icontains")
    last_name = filters.CharFilter(field_name="last_name", lookup_expr="icontains")
    username = filters.CharFilter(field_name="username", lookup_expr="icontains")
    phone_number = filters.CharFilter(field_name="phone_number", lookup_expr="icontains")
    last_login = filters.DateFromToRangeFilter(field_name="last_login")
    district_id = filters.NumberFilter(field_name="district_id", lookup_expr="exact")

    def get_user_type(
        self,
        queryset,
        field_name,
        value,
    ):
        if value:
            if value in INVERSE_USER_TYPE:
                return queryset.filter(user_type=INVERSE_USER_TYPE[value])
        return queryset

    user_type = filters.CharFilter(method="get_user_type", field_name="user_type")


class UserViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    A viewset for viewing and manipulating user instances.
    """

    queryset = User.objects.filter(is_superuser=False).select_related("local_body", "district", "state")
    lookup_field = "username"

    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    filter_backends = (
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
    )
    filterset_class = UserFilterSet
    ordering_fields = ["id", "date_joined", "last_login"]
    # last_login
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
            status=status.HTTP_200_OK,
            data=UserSerializer(request.user, context={"request": request}).data,
        )

    @action(detail=False, methods=["POST"])
    def add_user(self, request, *args, **kwargs):
        password = request.data.pop("password", User.objects.make_random_password(length=8))
        serializer = UserCreateSerializer(
            data={**request.data, "password": password},
            context={"created_by": request.user},
        )
        serializer.is_valid(raise_exception=True)
        username = request.data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError({"username": "User with Given Username Already Exists"})
        user = serializer.create(serializer.validated_data)

        response_data = UserCreateSerializer(user).data
        # response_data["password"] = password
        return Response(data=response_data, status=status.HTTP_201_CREATED)

    def has_facility_permission(self, user, facility):
        return (
            user.is_superuser
            or (facility and user in facility.users.all())
            or (
                user.user_type >= User.TYPE_VALUE_MAP["LocalBodyAdmin"]
                and (facility and user.local_body == facility.local_body)
            )
            or (
                user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
                and (facility and user.district == facility.district)
            )
            or (user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"] and (facility and user.state == facility.state))
        )

    def has_user_type_permission_elevation(self, init_user, dest_user):
        return init_user.user_type >= dest_user.user_type

    def check_facility_user_exists(self, user, facility):
        return FacilityUser.objects.filter(facility=facility, user=user).exists()

    @action(detail=True, methods=["GET"], permission_classes=[IsAuthenticated])
    def get_facilities(self, request, *args, **kwargs):
        user = self.get_object()
        facilities = Facility.objects.filter(users=user).select_related("local_body", "district", "state", "ward")
        facilities = FacilityBasicInfoSerializer(facilities, many=True)
        return Response(facilities.data)

    @action(detail=True, methods=["PUT"], permission_classes=[IsAuthenticated])
    def add_facility(self, request, *args, **kwargs):
        # Remove User Facility Cache
        user = self.get_object()
        remove_facility_user_cache(user.id)
        # Cache Deleted
        requesting_user = request.user
        if "facility" not in request.data:
            raise ValidationError({"facility": "required"})
        facility = Facility.objects.filter(external_id=request.data["facility"]).first()
        if not facility:
            raise ValidationError({"facility": "Does not Exist"})
        if not self.has_user_type_permission_elevation(requesting_user, user):
            raise ValidationError({"facility": "cannot Access Higher Level User"})
        if not self.has_facility_permission(requesting_user, facility):
            raise ValidationError({"facility": "Facility Access not Present"})
        if self.check_facility_user_exists(user, facility):
            raise ValidationError({"facility": "User Already has permission to this facility"})
        FacilityUser(facility=facility, user=user, created_by=requesting_user).save()
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["DELETE"], permission_classes=[IsAuthenticated])
    def delete_facility(self, request, *args, **kwargs):
        # Remove User Facility Cache
        user = self.get_object()
        remove_facility_user_cache(user.id)
        # Cache Deleted
        requesting_user = request.user
        if "facility" not in request.data:
            raise ValidationError({"facility": "required"})
        facility = Facility.objects.filter(external_id=request.data["facility"]).first()
        if not facility:
            raise ValidationError({"facility": "Does not Exist"})
        if not self.has_user_type_permission_elevation(requesting_user, user):
            raise ValidationError({"facility": "cannot Access Higher Level User"})
        if not self.has_facility_permission(requesting_user, facility):
            raise ValidationError({"facility": "Facility Access not Present"})
        if not self.has_facility_permission(user, facility):
            raise ValidationError({"facility": "Intended User Does not have permission to this facility"})
        FacilityUser.objects.filter(facility=facility, user=user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["PATCH"], permission_classes=[IsAuthenticated])
    def pnconfig(self, request, *args, **kwargs):
        user = request.user
        acceptable_fields = ["pf_endpoint", "pf_p256dh", "pf_auth"]
        for field in acceptable_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response(stauts=status.HTTP_200_OK)
