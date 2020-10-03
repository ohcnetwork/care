from django.contrib.auth import get_user_model
from dry_rest_permissions.generics import DRYPermissions
from requests.api import request
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.viewsets import GenericViewSet
from care.facility.models.facility import Facility, FacilityUser
from care.users.api.serializers.user import SignUpSerializer, UserCreateSerializer, UserListSerializer, UserSerializer
from care.facility.api.serializers.facility import FacilityBasicInfoSerializer

User = get_user_model()


class UserViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.ListModelMixin, GenericViewSet,
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

    @action(detail=True, methods=["GET"])
    def get_facilities(self, request, *args, **kwargs):
        user = self.get_object()
        facilities = Facility.objects.filter(users=user).select_related("local_body", "district", "state", "ward")
        facilities = FacilityBasicInfoSerializer(facilities, many=True)
        return Response(facilities.data)

    @action(detail=True, methods=["PUT"])
    def add_facility(self, request, *args, **kwargs):
        user = self.get_object()
        requesting_user = request.user
        if "facility" not in request.data:
            raise ValidationError({"facility": "required"})
        facility = Facility.objects.filter(external_id=request.data["facility"]).first()
        if not facility:
            raise ValidationError({"facility": "Does not Exist"})
        if not self.has_facility_permission(requesting_user, facility):
            raise ValidationError({"facility": "Facility Access not Present"})
        FacilityUser(facility=facility, user=user, created_by=requesting_user).save()
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["DELETE"])
    def delete_facility(self, request, *args, **kwargs):
        user = self.get_object()
        requesting_user = request.user
        if "facility" not in request.data:
            raise ValidationError({"facility": "required"})
        facility = Facility.objects.filter(external_id=request.data["facility"]).first()
        if not facility:
            raise ValidationError({"facility": "Does not Exist"})
        if not self.has_facility_permission(requesting_user, facility):
            raise ValidationError({"facility": "Facility Access not Present"})
        FacilityUser.objects.filter(facility=facility, user=user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
