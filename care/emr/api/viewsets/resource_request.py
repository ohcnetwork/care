from django.db.models import Q
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRDestroyMixin,
    EMRListMixin,
    EMRModelViewSet,
    EMRRetrieveMixin,
)
from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.models.resource_request import ResourceRequest, ResourceRequestComment
from care.emr.resources.resource_request.spec import (
    ResourceRequestCommentCreateSpec,
    ResourceRequestCommentListSpec,
    ResourceRequestCommentRetrieveSpec,
    ResourceRequestCreateSpec,
    ResourceRequestListSpec,
    ResourceRequestRetrieveSpec,
)


class ResourceRequestViewSet(EMRModelViewSet):
    database_model = ResourceRequest
    pydantic_model = ResourceRequestCreateSpec
    pydantic_read_model = ResourceRequestListSpec
    pydantic_retrieve_model = ResourceRequestRetrieveSpec

    @classmethod
    def build_queryset(cls, queryset, user):
        user_accessible_external_organizations = list(
            OrganizationUser.objects.filter(user=user).values_list(
                "organization_id", flat=True
            )
        )
        user_accessible_internal_organizations = list(
            FacilityOrganizationUser.objects.filter(user=user).values_list(
                "organization__facility_id", flat=True
            )
        )
        origin_facility_filters = Q(
            origin_facility_id__in=user_accessible_internal_organizations
        ) | Q(
            origin_facility__geo_organization_cache__overlap=user_accessible_external_organizations
        )
        approving_facility_filters = Q(
            approving_facility_id__in=user_accessible_internal_organizations
        ) | Q(
            approving_facility__geo_organization_cache__overlap=user_accessible_external_organizations
        )
        assigned_facility_filters = Q(
            assigned_facility_id__in=user_accessible_internal_organizations
        ) | Q(
            assigned_facility__geo_organization_cache__overlap=user_accessible_external_organizations
        )
        return queryset.filter(
            origin_facility_filters
            | approving_facility_filters
            | assigned_facility_filters
        )

    def get_queryset(self):
        queryset = ResourceRequest.objects.all().select_related(
            "origin_facility",
            "approving_facility",
            "assigned_facility",
            "related_patient",
            "assigned_to",
        )
        if self.request.user.is_superuser:
            return queryset
        return self.build_queryset(queryset, self.request.user)


class ResourceRequestCommentViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRListMixin, EMRDestroyMixin, EMRBaseViewSet
):
    database_model = ResourceRequestComment
    pydantic_model = ResourceRequestCommentCreateSpec
    pydantic_read_model = ResourceRequestCommentListSpec
    pydantic_retrieve_model = ResourceRequestCommentRetrieveSpec

    def perform_create(self, instance):
        instance.request = self.get_resource_request_obj()
        super().perform_create(instance)

    def get_resource_request_obj(self):
        queryset = ResourceRequest.objects.all()
        queryset = ResourceRequestViewSet.build_queryset(queryset, self.request.user)
        return get_object_or_404(
            queryset, external_id=self.kwargs["resource_external_id"]
        )

    def get_queryset(self):
        resource_request_obj = self.get_resource_request_obj()
        return ResourceRequestComment.objects.filter(
            request=resource_request_obj
        ).select_related("created_by")
