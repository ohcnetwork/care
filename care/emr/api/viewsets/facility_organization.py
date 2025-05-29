from django.conf import settings
from django.db.models import Q
from django.db.models.expressions import Subquery
from django_filters import rest_framework as filters
from rest_framework import filters as drf_filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models.device import Device
from care.emr.models.encounter import EncounterOrganization
from care.emr.models.location import FacilityLocationOrganization
from care.emr.models.organization import FacilityOrganization, FacilityOrganizationUser
from care.emr.resources.facility_organization.facility_orgnization_user_spec import (
    FacilityOrganizationUserReadSpec,
    FacilityOrganizationUserUpdateSpec,
    FacilityOrganizationUserWriteSpec,
)
from care.emr.resources.facility_organization.spec import (
    FacilityOrganizationReadSpec,
    FacilityOrganizationRetrieveSpec,
    FacilityOrganizationWriteSpec,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.security.models import RoleModel
from care.security.roles.role import FACILITY_ADMIN_ROLE
from care.users.models import User


class FacilityOrganizationFilter(filters.FilterSet):
    parent = filters.UUIDFilter(field_name="parent__external_id")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    org_type = filters.CharFilter(field_name="org_type", lookup_expr="iexact")


class FacilityOrganizationViewSet(EMRModelViewSet):
    database_model = FacilityOrganization
    pydantic_model = FacilityOrganizationWriteSpec
    pydantic_read_model = FacilityOrganizationReadSpec
    pydantic_retrieve_model = FacilityOrganizationRetrieveSpec
    filterset_class = FacilityOrganizationFilter
    filter_backends = [filters.DjangoFilterBackend]

    def get_organization_obj(self):
        return get_object_or_404(
            FacilityOrganization, external_id=self.kwargs["external_id"]
        )

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def validate_data(self, instance, model_obj=None):
        if instance.org_type == "root":
            raise PermissionDenied("Cannot create root organization")
        if instance.parent:
            parent = get_object_or_404(
                FacilityOrganization, external_id=instance.parent
            )
            if parent.org_type == "root":
                raise PermissionDenied(
                    "Cannot create organizations under root organization"
                )
            if parent.org_type == "role":
                raise PermissionDenied(
                    "Cannot create nested facility organizations under 'role' type facility organization"
                )
            if (
                model_obj is None
                and parent.level_cache >= settings.FACILITY_ORGANIZATION_MAX_DEPTH
            ):
                error = (
                    f"Max depth reached ({settings.FACILITY_ORGANIZATION_MAX_DEPTH})"
                )
                raise ValidationError(error)

        if model_obj is None:
            # validate max number in facility
            facility_external_id = self.kwargs["facility_external_id"]
            if (
                FacilityOrganization.objects.filter(
                    facility__external_id=facility_external_id
                ).count()
                >= settings.MAX_ORGANIZATION_IN_FACILITY
            ):
                error = f"Max location reached for facility ({settings.MAX_ORGANIZATION_IN_FACILITY})"
                raise ValidationError(error)

        # Validate Uniqueness
        if FacilityOrganization.validate_uniqueness(
            FacilityOrganization.objects.filter(facility=self.get_facility_obj()),
            instance,
            model_obj,
        ):
            raise ValidationError("Organization already exists with same name")

    def authorize_destroy(self, instance):
        if instance.org_type == "root":
            raise ValidationError("Cannot delete root organization")

        if FacilityOrganization.objects.filter(parent=instance).exists():
            raise ValidationError("Cannot delete organization with children")

        if (
            FacilityOrganizationUser.objects.filter(organization=instance)
            .exclude(user=self.request.user)
            .exists()
        ):
            raise ValidationError("Cannot delete organization with users")

        if EncounterOrganization.objects.filter(organization=instance).exists():
            raise ValidationError("Cannot delete organization with encounters")

        if FacilityLocationOrganization.objects.filter(organization=instance).exists():
            raise ValidationError("Cannot delete organization with locations")

        if Device.objects.filter(managing_organization=instance).exists():
            raise ValidationError("Cannot delete organization with devices")

        if self.request.user.is_superuser:
            return

        if not AuthorizationController.call(
            "can_delete_facility_organization", self.request.user, instance
        ):
            raise PermissionDenied(
                "User does not have the required permissions to delete this organization"
            )

    def authorize_update(self, request_obj, model_instance):
        if self.request.user.is_superuser:
            return

        if not AuthorizationController.call(
            "can_manage_facility_organization_obj", self.request.user, model_instance
        ):
            raise PermissionDenied(
                "User does not have the required permissions to update organization"
            )

    def authorize_create(self, instance):
        if self.request.user.is_superuser:
            return True
        # Organization creates require the Organization Create Permission

        if instance.parent:
            parent = get_object_or_404(
                FacilityOrganization, external_id=instance.parent
            )
        else:
            parent = None
        facility = self.get_facility_obj()
        if not AuthorizationController.call(
            "can_create_facility_organization_obj", self.request.user, parent, facility
        ):
            raise PermissionDenied(
                "User does not have the required permissions to create organizations"
            )
        return True

    def clean_create_data(self, request_data):
        request_data["facility"] = self.kwargs["facility_external_id"]
        return request_data

    def get_queryset(self):
        facility = self.get_facility_obj()
        queryset = (
            super()
            .get_queryset()
            .filter(facility=facility)
            .select_related("facility", "parent", "created_by", "updated_by")
        )
        if "parent" in self.request.GET and not self.request.GET.get("parent"):
            # Filter for root organizations, For some reason its not working as intended in Django Filters
            queryset = queryset.filter(parent__isnull=True)
        return AuthorizationController.call(
            "get_accessible_facility_organizations",
            queryset,
            self.request.user,
            facility,
        )

    def perform_destroy(self, instance):
        FacilityOrganizationUser.objects.filter(organization=instance).delete()
        instance.deleted = True
        instance.save(update_fields=["deleted"])

    @action(detail=False, methods=["GET"])
    def mine(self, request, *args, **kwargs):
        """
        Get organizations that are directly attached to the given user
        """
        orgusers = FacilityOrganizationUser.objects.filter(
            user=request.user, organization__facility=self.get_facility_obj()
        ).select_related("organization")
        data = [
            self.get_read_pydantic_model().serialize(orguser.organization).to_json()
            for orguser in orgusers
        ]
        return Response({"count": len(data), "results": data})


class FacilityOrganizationUsersViewSet(EMRModelViewSet):
    database_model = FacilityOrganizationUser
    pydantic_model = FacilityOrganizationUserWriteSpec
    pydantic_read_model = FacilityOrganizationUserReadSpec
    pydantic_update_model = FacilityOrganizationUserUpdateSpec
    filter_backends = [drf_filters.SearchFilter]
    search_fields = ["user__first_name", "user__last_name", "user__username"]

    def get_organization_obj(self):
        return get_object_or_404(
            FacilityOrganization,
            external_id=self.kwargs["facility_organizations_external_id"],
        )

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def perform_create(self, instance):
        instance.organization = self.get_organization_obj()
        instance.facility = self.get_facility_obj()
        super().perform_create(instance)

    def validate_data(self, instance, model_obj=None):
        organization = self.get_organization_obj()
        if model_obj:
            # Deny update if user is the last facility admin
            role_obj = model_obj.role
            if (
                organization.org_type == "root"
                and role_obj.name == FACILITY_ADMIN_ROLE.name
                and not FacilityOrganizationUser.objects.filter(
                    organization=organization,
                    role=role_obj,
                )
                .exclude(
                    id=model_obj.id,
                )
                .exists()
            ):
                raise ValidationError(
                    "Cannot change the role of the last admin user in the root organization"
                )
            return

        queryset = FacilityOrganizationUser.objects.filter(
            user__in=Subquery(
                User.objects.filter(external_id=instance.user).values_list("id")
            )
        )
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

    def validate_destroy(self, instance):
        if (
            instance.organization.org_type == "root"
            and FacilityOrganizationUser.objects.filter(
                organization=self.get_organization_obj()
            ).count()
            <= 1
        ):
            raise ValidationError(
                "Cannot delete the last user from the root organization"
            )

    def authorize_destroy(self, instance):
        organization = self.get_organization_obj()
        if not AuthorizationController.call(
            "can_manage_facility_organization_users_obj",
            self.request.user,
            organization,
            instance.role,
        ):
            raise PermissionDenied("User does not have permission for this action")

    def authorize_update(self, request_obj, model_instance):
        organization = self.get_organization_obj()
        requested_role = get_object_or_404(RoleModel, external_id=request_obj.role)
        if not AuthorizationController.call(
            "can_manage_facility_organization_users_obj",
            self.request.user,
            organization,
            model_instance.role,
        ):
            raise PermissionDenied("User does not have permission for this action")
        if not AuthorizationController.call(
            "can_manage_facility_organization_users_obj",
            self.request.user,
            organization,
            requested_role,
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
            "can_manage_facility_organization_users_obj",
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
            "can_list_facility_organization_users_obj", self.request.user, organization
        ):
            raise PermissionDenied(
                "User does not have the required permissions to list users"
            )
        return FacilityOrganizationUser.objects.filter(
            organization=organization
        ).select_related("organization", "user", "role")
