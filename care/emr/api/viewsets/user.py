from django.db import transaction
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from rest_framework import filters as drf_filters
from rest_framework.decorators import action, parser_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models import Organization
from care.emr.models.organization import OrganizationUser
from care.emr.resources.user.spec import (
    UserCreateSpec,
    UserRetrieveSpec,
    UserSpec,
    UserTypeRoleMapping,
    UserUpdateSpec,
)
from care.security.authorization import AuthorizationController
from care.security.models import RoleModel
from care.users.api.serializers.user import UserImageUploadSerializer, UserSerializer
from care.users.models import User
from care.utils.file_uploads.cover_image import delete_cover_image


class UserFilter(filters.FilterSet):
    email = filters.CharFilter(field_name="email", lookup_expr="icontains")
    phone_number = filters.CharFilter(
        field_name="phone_number", lookup_expr="icontains"
    )
    username = filters.CharFilter(field_name="username", lookup_expr="icontains")
    user_type = filters.CharFilter(field_name="username", lookup_expr="iexact")


class UserViewSet(EMRModelViewSet):
    database_model = User
    pydantic_model = UserCreateSpec
    pydantic_update_model = UserUpdateSpec
    pydantic_read_model = UserSpec
    pydantic_retrieve_model = UserRetrieveSpec
    lookup_field = "username"
    filterset_class = UserFilter
    filter_backends = [filters.DjangoFilterBackend, drf_filters.SearchFilter]
    search_fields = ["first_name", "last_name", "username"]

    def perform_create(self, instance):
        with transaction.atomic():
            super().perform_create(instance)
            # Get or create organization with the role
            org_name = instance.user_type.capitalize()
            org = Organization.objects.filter(
                parent__isnull=True,
                name=org_name,
                org_type="role",
                system_generated=True,
            ).first()
            if not org:
                org = Organization.objects.create(
                    name=org_name, org_type="role", system_generated=True
                )
            # Add User to organization with default role
            OrganizationUser.objects.create(
                organization=org,
                user=instance,
                role=RoleModel.objects.get(
                    is_system=True,
                    name=UserTypeRoleMapping[instance.user_type].value.name,
                ),
            )

    def authorize_update(self, request_obj, model_instance):
        if self.request.user.is_superuser:
            return True
        return self.request.user.id == model_instance.id

    def authorize_create(self, instance):
        if not AuthorizationController.call("can_create_user", self.request.user):
            raise PermissionDenied("You do not have permission to create Users")

    def authorize_destroy(self, instance):
        return self.request.user.is_superuser

    @action(detail=False, methods=["GET"])
    def getcurrentuser(self, request):
        return Response(
            data=UserSerializer(request.user, context={"request": request}).data,
        )

    @action(methods=["GET"], detail=True)
    def check_availability(self, request, username):
        """
        Checks availability of username by getting as query, returns 200 if available, and 409 otherwise.
        """
        if User.check_username_exists(username):
            return Response(status=409)
        return Response(status=200)

    @method_decorator(parser_classes([MultiPartParser]))
    @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated])
    def profile_picture(self, request, *args, **kwargs):
        user = self.get_object()
        if not self.authorize_update({}, user):
            raise PermissionDenied("Permission Denied")
        serializer = UserImageUploadSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=200)

    @profile_picture.mapping.delete
    def profile_picture_delete(self, request, *args, **kwargs):
        user = self.get_object()
        if not self.authorize_update({}, user):
            raise PermissionDenied("Permission Denied")
        delete_cover_image(user.profile_picture_url, "avatars")
        user.profile_picture_url = None
        user.save()
        return Response(status=204)

    @action(
        detail=True,
        methods=["PATCH", "GET"],
        permission_classes=[IsAuthenticated],
    )
    def pnconfig(self, request, *args, **kwargs):
        user = request.user
        if request.method == "GET":
            return Response(
                {
                    "pf_endpoint": user.pf_endpoint,
                    "pf_p256dh": user.pf_p256dh,
                    "pf_auth": user.pf_auth,
                }
            )
        acceptable_fields = ["pf_endpoint", "pf_p256dh", "pf_auth"]
        for field in acceptable_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response({})
