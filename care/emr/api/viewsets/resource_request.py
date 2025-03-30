from django.db.models import Q
from django_filters import rest_framework as filters
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


class ResourceRequestFilters(filters.FilterSet):
    origin_facility = filters.UUIDFilter(field_name="origin_facility__external_id")
    approving_facility = filters.UUIDFilter(
        field_name="approving_facility__external_id"
    )
    assigned_facility = filters.UUIDFilter(field_name="assigned_facility__external_id")
    related_patient = filters.UUIDFilter(field_name="related_patient__external_id")
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")


class ResourceRequestViewSet(EMRModelViewSet):
    database_model = ResourceRequest
    pydantic_model = ResourceRequestCreateSpec
    pydantic_read_model = ResourceRequestListSpec
    pydantic_retrieve_model = ResourceRequestRetrieveSpec
    filterset_class = ResourceRequestFilters
    filter_backends = [filters.DjangoFilterBackend]

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
        queryset = (
            ResourceRequest.objects.all()
            .select_related(
                "origin_facility",
                "approving_facility",
                "assigned_facility",
                "related_patient",
                "assigned_to",
            )
            .order_by("-created_date")
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
        return (
            ResourceRequestComment.objects.filter(request=resource_request_obj)
            .select_related("created_by")
            .order_by("-created_date")
        )
