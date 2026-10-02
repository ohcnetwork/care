from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models.organization import FacilityOrganization
from care.emr.models.workspace import (
    Workspace,
    WorkspaceFacilityOrganization,
    WorkSpaceUserDefault,
)
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.workspace.spec import (
    WorkspaceAuthContext,
    WorkspaceCreateSpec,
    WorkspaceMinimalReadSpec,
    WorkspaceReadSpec,
    WorkspaceUpdateSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class WorkspaceFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    auth_context = filters.CharFilter(field_name="auth_context", lookup_expr="iexact")
    facility = filters.UUIDFilter(field_name="facility__external_id")


class WorkspaceViewSet(EMRModelViewSet):
    database_model = Workspace
    pydantic_model = WorkspaceCreateSpec
    pydantic_update_model = WorkspaceUpdateSpec
    pydantic_read_model = WorkspaceReadSpec
    filterset_class = WorkspaceFilter
    filter_backends = [DjangoFilterBackend]

    def authorize_create(self, instance):
        if (
            instance.auth_context == WorkspaceAuthContext.instance
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied("You are not authorized to create a workspace")
        if instance.auth_context == WorkspaceAuthContext.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_access_facility_workspace",
                self.request.user,
                facility,
                None,
                read_only=False,
            ):
                raise PermissionDenied("You are not authorized to create a workspace")
        if instance.auth_context == WorkspaceAuthContext.facility_organization:
            facility_organization = get_object_or_404(
                FacilityOrganization, external_id=instance.facility_organization
            )
            if not AuthorizationController.call(
                "can_access_facility_organization_workspace",
                self.request.user,
                facility_organization,
                read_only=False,
            ):
                raise PermissionDenied("You are not authorized to create a workspace")
        if instance.auth_context == WorkspaceAuthContext.user:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_access_user_workspace_in_facility",
                self.request.user,
                facility,
                read_only=False,
            ):
                raise PermissionDenied("You are not authorized to create a workspace")

        return super().authorize_create(instance)

    def authorize_update(self, request_obj, model_instance):
        if (
            model_instance.auth_context == WorkspaceAuthContext.instance
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied("You are not authorized to create a workspace")
        if (
            model_instance.auth_context == WorkspaceAuthContext.facility
            and not AuthorizationController.call(
                "can_access_facility_workspace",
                self.request.user,
                model_instance.facility,
                None,
                read_only=False,
            )
        ):
            raise PermissionDenied("You are not authorized to create a workspace")
        if (
            model_instance.auth_context == WorkspaceAuthContext.facility_organization
            and not AuthorizationController.call(
                "can_access_facility_organization_workspace",
                self.request.user,
                model_instance.facility_organization,
                read_only=False,
            )
        ):
            raise PermissionDenied("You are not authorized to create a workspace")
        if (
            model_instance.auth_context == WorkspaceAuthContext.user
            and not AuthorizationController.call(
                "can_access_user_workspace_in_facility",
                self.request.user,
                model_instance.facility,
                read_only=False,
            )
        ):
            raise PermissionDenied("You are not authorized to create a workspace")
        if (
            model_instance.auth_context == WorkspaceAuthContext.user
            and model_instance.created_by != self.request.user
        ):
            raise PermissionDenied("Only the creator of the workspace can update it")

    def authorize_destroy(self, instance):
        self.authorize_update(self.request, instance)

    def perform_create(self, instance):
        super().perform_create(instance)
        instance.sync_facility_org_cache()

    def get_queryset(self):
        queryset = super().get_queryset()
        return AuthorizationController.call(
            "get_filtered_workspaces", queryset, self.request.user
        )

    @action(detail=True, methods=["GET"])
    def get_facility_organizations(self, request, *args, **kwargs):
        workspace = self.get_object()
        if not workspace.auth_context == WorkspaceAuthContext.facility:
            raise PermissionDenied(
                "Facility organizations can only be set for facility level workspaces"
            )
        self.authorize_update(None, workspace)
        workspace_organizations = WorkspaceFacilityOrganization.objects.filter(
            workspace=workspace
        ).select_related("organization")
        organizations = [
            FacilityOrganizationReadSpec.serialize(obj.organization).to_json()
            for obj in workspace_organizations
        ]
        return Response(
            {
                "count": len(organizations),
                "results": organizations,
            }
        )

    class WorkspaceFacilityOrganizationUpdateSchema(BaseModel):
        facility_organizations: list[UUID4]

    @extend_schema(request=WorkspaceFacilityOrganizationUpdateSchema)
    @action(detail=True, methods=["POST"])
    def set_facility_organizations(self, request, *args, **kwargs):
        workspace = self.get_object()
        if not workspace.auth_context == WorkspaceAuthContext.facility:
            raise PermissionDenied(
                "Facility organizations can only be set for facility level workspaces"
            )
        self.authorize_update(None, workspace)
        request_params = self.WorkspaceFacilityOrganizationUpdateSchema(**request.data)
        with transaction.atomic():
            WorkspaceFacilityOrganization.objects.filter(workspace=workspace).delete()
            for org in request_params.facility_organizations:
                organization = get_object_or_404(
                    FacilityOrganization.objects.only("id"),
                    external_id=org,
                    facility=workspace.facility,
                )
                WorkspaceFacilityOrganization.objects.create(
                    workspace=workspace, organization=organization
                )
            workspace.sync_facility_org_cache()
        return Response({})

    class WorkspaceDefaultSetSchema(BaseModel):
        attribute: str | None = None
        value: str

    @extend_schema(request=WorkspaceDefaultSetSchema)
    @action(detail=True, methods=["POST"])
    def set_default_attributes(self, request, *args, **kwargs):
        workspace = self.get_object()
        request_params = self.WorkspaceDefaultSetSchema(**request.data)
        with transaction.atomic():
            workspace_qs = WorkSpaceUserDefault.objects.filter(
                workspace=workspace, user=self.request.user
            )
            if request_params.attribute:
                workspace_qs = workspace_qs.filter(attribute=request_params.attribute)
            else:
                workspace_qs = workspace_qs.filter(attribute__isnull=True)
            workspace_qs.delete()
            WorkSpaceUserDefault.objects.create(
                workspace=workspace,
                attribute=request_params.attribute,
                value=request_params.value,
                user=self.request.user,
            )
        return Response({})

    @action(detail=False, methods=["GET"])
    def get_user_default_attributes(self, request, *args, **kwargs):
        cache_key = WorkSpaceUserDefault.get_cache_key(self.request.user.id)
        results = cache.get(cache_key)
        if results is None:
            user_default_attributes = WorkSpaceUserDefault.objects.filter(
                user=self.request.user
            ).select_related("workspace")
            results = [
                {
                    "attribute": obj.attribute,
                    "value": obj.value,
                    "workspace": WorkspaceMinimalReadSpec.serialize(
                        obj.workspace
                    ).to_json(),
                }
                for obj in user_default_attributes
            ]
            cache.set(cache_key, results)
        return Response({"count": len(results), "results": results})
