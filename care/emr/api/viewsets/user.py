from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import filters as drf_filters
from rest_framework import serializers
from rest_framework.decorators import action, parser_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRDestroyMixin,
    EMRListMixin,
    EMRModelViewSet,
    EMRRetrieveMixin,
)
from care.emr.models import Organization
from care.emr.models.organization import OrganizationUser
from care.emr.models.user import UserFlag
from care.emr.resources.common.mail_type import MailTypeChoices
from care.emr.resources.user.spec import (
    CurrentUserRetrieveSpec,
    UserCreateSpec,
    UserFlagCreateSpec,
    UserFlagReadSpec,
    UserRetrieveSpec,
    UserSpec,
    UserTypeRoleMapping,
    UserUpdateSpec,
)
from care.emr.utils.reset_password import send_password_reset_email
from care.security.authorization import AuthorizationController
from care.security.models import RoleModel
from care.users.models import User
from care.utils.file_uploads.cover_image import delete_cover_image, upload_cover_image
from care.utils.models.validators import (
    cover_image_validator,
    custom_image_extension_validator,
)
from care.utils.registries.feature_flag import FlagNotFoundError, FlagRegistry, FlagType


class UserImageUploadSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(
        required=True,
        write_only=True,
        validators=[custom_image_extension_validator, cover_image_validator],
    )
    read_profile_picture_url = serializers.URLField(read_only=True)

    class Meta:
        model = User
        fields = ("profile_picture", "read_profile_picture_url")

    def save(self, **kwargs):
        user: User = self.instance
        image = self.validated_data["profile_picture"]
        user.profile_picture_url = upload_cover_image(
            image,
            str(user.external_id),
            "avatars",
            user.profile_picture_url,
        )
        user.save(update_fields=["profile_picture_url"])
        return user


class UserFilter(filters.FilterSet):
    email = filters.CharFilter(field_name="email", lookup_expr="icontains")
    phone_number = filters.CharFilter(
        field_name="phone_number", lookup_expr="icontains"
    )
    username = filters.CharFilter(field_name="username", lookup_expr="icontains")
    user_type = filters.CharFilter(field_name="user_type", lookup_expr="iexact")


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

    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)

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
            if not instance.has_usable_password():
                try:
                    mail_type = MailTypeChoices.create.value
                    send_password_reset_email(instance, mail_type)
                except Exception as e:
                    raise IntegrityError(
                        "User creation failed due to email error."
                    ) from e  # to fail the transaction

    def authorize_update(self, request_obj, model_instance):
        if self.request.user.is_superuser:
            return
        if not self.request.user.id == model_instance.id:
            raise PermissionDenied("You do not have permission to update this user")

    def authorize_create(self, instance):
        if not AuthorizationController.call("can_create_user", self.request.user):
            raise PermissionDenied("You do not have permission to create Users")

    def perform_destroy(self, instance):
        if instance.last_login:
            instance.deleted = True
            instance.save(update_fields=["deleted"])
        else:
            instance.delete()

    def authorize_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise PermissionDenied("You do not have permission to delete this user")

    @extend_schema(responses={200: CurrentUserRetrieveSpec})
    @action(detail=False, methods=["GET"])
    def getcurrentuser(self, request):
        return Response(CurrentUserRetrieveSpec.serialize(request.user).to_json())

    @action(methods=["GET"], detail=True)
    def check_availability(self, request, username):
        """
        Checks availability of username by getting as query, returns 200 if available, and 409 otherwise.
        """
        if User.check_username_exists(username):
            return Response(status=409)
        return Response(status=200)

    @method_decorator(parser_classes([MultiPartParser]))
    @action(
        detail=True, methods=["POST", "DELETE"], permission_classes=[IsAuthenticated]
    )
    def profile_picture(self, request, *args, **kwargs):
        user = self.get_object()
        self.authorize_update({}, user)

        if request.method == "POST":
            serializer = UserImageUploadSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(status=200)
        if request.method == "DELETE":
            if not user.profile_picture_url:
                return Response({"detail": "No cover image to delete"}, status=404)
            delete_cover_image(user.profile_picture_url, "avatars")
            user.profile_picture_url = None
            user.save()
            return Response(status=204)
        return Response({"detail": "Method not allowed"}, status=405)

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


class UserFlagFilter(filters.FilterSet):
    flag = filters.CharFilter(field_name="flag", lookup_expr="exact")
    user = filters.UUIDFilter(field_name="user__external_id")


class UserFlagViewSet(
    EMRDestroyMixin, EMRCreateMixin, EMRRetrieveMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = UserFlag
    pydantic_model = UserFlagCreateSpec
    pydantic_read_model = UserFlagReadSpec
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = UserFlagFilter

    def permissions_controller(self, request):
        return request.user.is_superuser

    def perform_create(self, instance):
        with transaction.atomic():
            FlagRegistry.register(FlagType.USER.value, instance.flag)
            super().perform_create(instance)

    def perform_destroy(self, instance):
        with transaction.atomic():
            super().perform_destroy(instance)
            UserFlag.invalidate_cache(instance.user, instance.flag)
            transaction.on_commit(
                lambda: self._safe_unregister_flag_if_unused(instance.flag, instance.id)
            )

    def _safe_unregister_flag_if_unused(self, flag_name: str, deleted_instance_id: int):
        still_used = (
            UserFlag.objects.filter(flag=flag_name)
            .exclude(id=deleted_instance_id)
            .exists()
        )

        if not still_used:
            FlagRegistry.unregister(FlagType.USER.value, flag_name)

    @action(detail=False, methods=["get"], url_path="available-flags")
    def list_available_flags(self, request):
        try:
            flags = FlagRegistry.get_all_flags(FlagType.USER.value)
            return Response({"available_flags": list(flags)})
        except FlagNotFoundError:
            return Response(
                {"message": "No registered flag type 'user' found."}, status=400
            )
