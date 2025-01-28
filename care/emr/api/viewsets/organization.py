from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.settings import api_settings

from care.emr.api.viewsets.base import EMRModelReadOnlyViewSet, EMRModelViewSet
from care.emr.models.organization import Organization, OrganizationUser
from care.emr.resources.organization.organization_user_spec import (
    OrganizationUserReadSpec,
    OrganizationUserUpdateSpec,
    OrganizationUserWriteSpec,
)
from care.emr.resources.organization.spec import (
    OrganizationReadSpec,
    OrganizationRetrieveSpec,
    OrganizationTypeChoices,
    OrganizationUpdateSpec,
    OrganizationWriteSpec,
)
from care.security.authorization import AuthorizationController
from care.security.models import PermissionModel, RoleModel, RolePermission
from care.utils.pagination.care_pagination import CareLimitOffsetPagination
from config.patient_otp_authentication import JWTTokenPatientAuthentication


class OrganizationFilter(filters.FilterSet):
    parent = filters.UUIDFilter(field_name="parent__external_id")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    org_type = filters.CharFilter(field_name="org_type", lookup_expr="iexact")
    level_cache = filters.NumberFilter(field_name="level_cache")


class OrganizationPublicViewSet(EMRModelReadOnlyViewSet):
    database_model = Organization
    pydantic_read_model = OrganizationReadSpec
    filterset_class = OrganizationFilter
    filter_backends = [filters.DjangoFilterBackend]
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        queryset = super().get_queryset().order_by("created_date")
        if "parent" in self.request.GET and not self.request.GET.get("parent"):
            queryset = queryset.filter(parent__isnull=True)
        return queryset


class OrganizationViewSet(EMRModelViewSet):
    database_model = Organization
    pydantic_model = OrganizationWriteSpec
    pydantic_read_model = OrganizationReadSpec
    pydantic_update_model = OrganizationUpdateSpec
    pydantic_retrieve_model = OrganizationRetrieveSpec
    filterset_class = OrganizationFilter
    filter_backends = [filters.DjangoFilterBackend]
    authentication_classes = [
        JWTTokenPatientAuthentication,
        *api_settings.DEFAULT_AUTHENTICATION_CLASSES,
    ]
    pagination_class = CareLimitOffsetPagination

    def permissions_controller(self, request):
        if self.action in ["list"]:
            # All users including otp users can view the list of organizations
            return True
        # Deny all other permissions in OTP mode
        return not getattr(request.user, "is_alternative_login", False)

    def validate_data(self, instance, model_obj=None):
        """
        Validating uniqueness on a given level
        """
        if Organization.validate_uniqueness(
            Organization.objects.all(), instance, model_obj
        ):
            raise ValidationError("Organization already exists with same name")

    def authorize_destroy(self, instance):
        if Organization.objects.filter(parent=instance).exists():
            raise PermissionDenied("Cannot delete organization with children")

        if self.request.user.is_superuser:
            return

        if instance.org_type in [
            OrganizationTypeChoices.govt.value,
            OrganizationTypeChoices.role.value,
        ]:
            raise PermissionDenied("Organization Type cannot be deleted")

        if not AuthorizationController.call(
            "can_manage_organization_obj", self.request.user, instance
        ):
            raise PermissionDenied(
                "User does not have the required permissions to update organizations"
            )
        # TODO delete should not be allowed if there are any children left

    def authorize_update(self, request_obj, model_instance):
        if self.request.user.is_superuser:
            return

        if model_instance.org_type in [
            OrganizationTypeChoices.govt.value,
            OrganizationTypeChoices.role.value,
        ]:
            raise PermissionDenied("Organization Type cannot be updated")

        if not AuthorizationController.call(
            "can_manage_organization_obj", self.request.user, model_instance
        ):
            raise PermissionDenied(
                "User does not have the required permissions to update organizations"
            )

    def authorize_create(self, instance):
        if self.request.user.is_superuser:
            return True
        # Root Organizations can only be created by the superadmin
        if not instance.parent:
            raise PermissionDenied(
                "Root Organizations can only be created by the superadmin"
            )
        # Some types of organization cannot be created by regular users
        if instance.org_type in [
            OrganizationTypeChoices.govt.value,
            OrganizationTypeChoices.role.value,
        ]:
            raise PermissionDenied("Organization Type cannot be created")
        # Organizations can only be created if the parent is accessible by the user
        # Organization creates require the Organization Create Permission

        parent = get_object_or_404(Organization, external_id=instance.parent)

        if not AuthorizationController.call(
            "can_create_organization_obj", self.request.user, parent
        ):
            raise PermissionDenied(
                "User does not have the required permissions to create organizations"
            )
        return True

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("parent", "created_by", "updated_by")
            .order_by("created_date")
        )
        if "parent" in self.request.GET and not self.request.GET.get("parent"):
            # Filter for root organizations, For some reason its not working as intended in Django Filters
            queryset = queryset.filter(parent__isnull=True)
        if getattr(self.request.user, "is_alternative_login", False):
            # OTP Mode can only access organizations of the type govt and role
            # OTP Users do not have any more permissions
            return queryset.filter(
                org_type__in=[
                    OrganizationTypeChoices.govt.value,
                ]
            )
        if "permission" in self.request.GET and (
            not self.request.user.is_superuser
            or not getattr(self.request.user, "is_alternative_login", False)
        ):
            # Filter by a permission, this is used to list organizations that the user has a permission over
            permission = get_object_or_404(
                PermissionModel, slug=self.request.GET.get("permission")
            )
            roles = RolePermission.objects.filter(permission=permission).values_list(
                "role_id", flat=True
            )
            queryset = queryset.filter(
                id__in=OrganizationUser.objects.filter(
                    user=self.request.user, role_id__in=roles
                ).values_list("organization_id", flat=True)
            )

        # Filter organizations based on the user's permissions
        return AuthorizationController.call(
            "get_accessible_organizations", queryset, self.request.user
        )

    @action(detail=False, methods=["GET"])
    def mine(self, request, *args, **kwargs):
        """
        Get organizations that are directly attached to the given user
        """
        orgusers = OrganizationUser.objects.filter(user=request.user).select_related(
            "organization"
        )
        data = [
            self.get_read_pydantic_model().serialize(orguser.organization).to_json()
            for orguser in orgusers
        ]
        return Response({"count": len(data), "results": data})


class OrganizationUserFilter(filters.FilterSet):
    username = filters.CharFilter(field_name="user__username", lookup_expr="icontains")


class OrganizationUsersViewSet(EMRModelViewSet):
    database_model = OrganizationUser
    pydantic_model = OrganizationUserWriteSpec
    pydantic_read_model = OrganizationUserReadSpec
    pydantic_update_model = OrganizationUserUpdateSpec
    filterset_class = OrganizationUserFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_organization_obj(self):
        return get_object_or_404(
            Organization, external_id=self.kwargs["organization_external_id"]
        )

    def perform_create(self, instance):
        instance.organization = self.get_organization_obj()
        super().perform_create(instance)

    def validate_data(self, instance, model_obj=None):
        if model_obj:
            return
        organization = self.get_organization_obj()
        queryset = OrganizationUser.objects.filter(user__external_id=instance.user)
        if organization.root_org is None:
            queryset = queryset.filter(organization=organization)
        else:
            queryset = queryset.filter(
                Q(organization=organization)
                | Q(organization__root_org=organization.root_org)
            )
        if queryset.exists():
            raise ValidationError("User association already exists")

    def authorize_update(self, request_obj, model_instance):
        organization = self.get_organization_obj()
        requested_role = get_object_or_404(RoleModel, external_id=request_obj.role)
        if not AuthorizationController.call(
            "can_manage_organization_users_obj",
            self.request.user,
            organization,
            model_instance.role,
        ):
            raise PermissionDenied("User does not have permission for this action")
        if not AuthorizationController.call(
            "can_manage_organization_users_obj",
            self.request.user,
            organization,
            requested_role,
        ):
            raise PermissionDenied("User does not have permission for this action")

    def authorize_destroy(self, instance):
        organization = self.get_organization_obj()
        if not AuthorizationController.call(
            "can_manage_organization_users_obj",
            self.request.user,
            organization,
            instance.role,
        ):
            raise PermissionDenied("User does not have permission for this action")

    def authorize_create(self, instance):
        """
        - Creates are only allowed if the user is part of the organization
        - The role applied to the new user must be equal or lower in privilege to the user created
        - Maintain a permission to add users to an organization
        """
        if self.request.user.is_superuser:
            return
        organization = self.get_organization_obj()
        requested_role = get_object_or_404(RoleModel, external_id=instance.role)
        if not AuthorizationController.call(
            "can_manage_organization_users_obj",
            self.request.user,
            organization,
            requested_role,
        ):
            raise PermissionDenied("User does not have permission for this action")

    def get_queryset(self):
        """
        Only users part of the organization can access its users
        """
        organization = self.get_organization_obj()
        if not AuthorizationController.call(
            "can_list_organization_users_obj", self.request.user, organization
        ):
            raise PermissionDenied(
                "User does not have the required permissions to list users"
            )
        return OrganizationUser.objects.filter(organization=organization)
