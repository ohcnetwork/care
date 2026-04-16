from enum import Enum

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
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
from care.emr.resources.role.spec import RoleReadSpec
from care.security.authorization import AuthorizationController
from care.security.models import PermissionModel, RoleModel, RolePermission
from care.utils.filters.default_filter import DefaultBooleanFilter
from care.utils.pagination.care_pagination import CareLimitOffsetPagination
from care.utils.shortcuts import get_object_or_404
from config.patient_otp_authentication import JWTTokenPatientAuthentication


class ManagingOrganizationFilter(filters.UUIDFilter):
    def filter(self, qs, value):
        queryset = qs
        if not value:
            return queryset
        organization = get_object_or_404(
            Organization.objects.only("id"), external_id=value
        )
        return queryset.filter(managing_organizations__overlap=[organization.id])


class OrganizationFilter(filters.FilterSet):
    parent = filters.UUIDFilter(field_name="parent__external_id")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    org_type = filters.CharFilter(field_name="org_type", lookup_expr="iexact")
    level_cache = filters.NumberFilter(field_name="level_cache")
    get_managed_organizations = ManagingOrganizationFilter()


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


class OrganizationManagingOrganizationAction(str, Enum):
    add = "add"
    remove = "remove"


class OrganizationManagingOrganizationRequest(BaseModel):
    organization: UUID4
    action: OrganizationManagingOrganizationAction


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

        if model_obj is None and instance.parent:
            parent = get_object_or_404(Organization, external_id=instance.parent)

            # Validate Depth
            if parent.level_cache >= settings.ORGANIZATION_MAX_DEPTH:
                error = f"Max depth reached ({settings.ORGANIZATION_MAX_DEPTH})"
                raise ValidationError(error)

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
                "User does not have the required permissions to delete organizations"
            )

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

        if parent.org_type == OrganizationTypeChoices.role.value:
            raise ValidationError(
                "Cannot create organizations under role organizations"
            )

        if not AuthorizationController.call(
            "can_create_organization_obj", self.request.user, parent
        ):
            raise PermissionDenied(
                "User does not have the required permissions to create organizations"
            )
        return True

    def perform_destroy(self, instance):
        with transaction.atomic():
            OrganizationUser.objects.filter(organization=instance).delete()
            instance.deleted = True
            instance.save(update_fields=["deleted"])

            parent = instance.parent
            if parent:
                parent.has_children = Organization.objects.filter(
                    parent=parent
                ).exists()
                parent.save(update_fields=["has_children"])

    def get_queryset(self):
        queryset = (
            super().get_queryset().select_related("parent").order_by("created_date")
        )
        if self.action == "retrieve":
            obj = get_object_or_404(
                Organization.objects.only("org_type"),
                external_id=self.kwargs["external_id"],
            )
            if obj.org_type == OrganizationTypeChoices.role.value:
                return queryset
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

    @action(detail=False, methods=["GET"])
    def accessible_role_organizations(self, request, *args, **kwargs):
        my_organizations = OrganizationUser.objects.filter(
            organization__org_type=OrganizationTypeChoices.role.value, user=request.user
        ).only("organization_id", "role_id")
        org_role_mapping = {}
        for my_organization in my_organizations:
            org_role_mapping[my_organization.organization_id] = my_organization.role_id
        my_organizations_ids = list(org_role_mapping.keys())

        if self.request.user.is_superuser:
            managing_organization = Organization.objects.filter(
                org_type=OrganizationTypeChoices.role.value
            )
        else:
            managing_organization = Organization.objects.filter(
                Q(managing_organizations__overlap=list(my_organizations_ids))
                | Q(id__in=my_organizations_ids)
            )

        rendered_data = []
        for org in managing_organization:
            data = {}
            org_data = OrganizationReadSpec.serialize(org).to_json()
            # TODO : Cache RoleModel
            if org.id in org_role_mapping:
                role_data = RoleReadSpec.serialize(
                    RoleModel.objects.get(id=org_role_mapping[org.id])
                ).to_json()
            else:
                role_data = None
            data["role"] = role_data
            data["organization"] = org_data
            rendered_data.append(data)

        return Response({"count": len(rendered_data), "results": rendered_data})

    @extend_schema(
        request=OrganizationManagingOrganizationRequest,
    )
    @action(detail=True, methods=["POST"])
    def managing_organization(self, request, *args, **kwargs):
        request_data = OrganizationManagingOrganizationRequest(**request.data)
        organization = self.get_object()
        managing_organization = get_object_or_404(
            Organization, external_id=request_data.organization
        )
        if (
            organization.org_type != OrganizationTypeChoices.role.value
            or managing_organization.org_type != OrganizationTypeChoices.role.value
        ):
            raise ValidationError(
                "Managing organization is only supported for role organizations"
            )
        if not AuthorizationController.call(
            "can_manage_organization_obj", self.request.user, managing_organization
        ):
            raise PermissionDenied(
                "User does not have the required permissions to requested organization"
            )
        if not AuthorizationController.call(
            "can_manage_organization_obj", self.request.user, organization
        ):
            raise PermissionDenied(
                "User does not have the required permissions to manage the organization"
            )

        if request_data.action == OrganizationManagingOrganizationAction.add:
            organization.managing_organizations = list(
                {*organization.managing_organizations, managing_organization.id}
            )
        elif request_data.action == OrganizationManagingOrganizationAction.remove:
            if managing_organization.id not in organization.managing_organizations:
                raise ValidationError(
                    "Managing organization is not part of the organization"
                )
            organization.managing_organizations.remove(managing_organization.id)
        organization.updated_by = request.user
        organization.save()
        return Response({})


class OrganizationUserFilter(filters.FilterSet):
    phone_number = filters.CharFilter(
        field_name="user__phone_number", lookup_expr="iexact"
    )
    username = filters.CharFilter(field_name="user__username", lookup_expr="icontains")
    is_service_account = DefaultBooleanFilter(
        field_name="user__is_service_account", default=False
    )


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
        # TODO : Optimise by fetching user first, avoiding the extra join to org
        queryset = OrganizationUser.objects.filter(user__external_id=instance.user)
        # Case 1 - Same organization
        if queryset.filter(Q(organization=organization)).exists():
            raise ValidationError("User association already exists")
        # Case 2 - Adding to a child organization ( parent already linked )
        if organization.parent:
            parent_orgs = organization.parent_cache
            if queryset.filter(Q(organization__in=parent_orgs)).exists():
                raise ValidationError("User is already linked to a parent organization")
        # Case 3 - Adding to a parent organization ( child already linked )
        if queryset.filter(
            organization__parent_cache__overlap=[organization.id]
        ).exists():
            raise ValidationError("User has association to some child organization")

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
