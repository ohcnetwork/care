from django.conf import settings
from django.db.models.query_utils import Q
from django_filters import rest_framework as filters
from djqscsv import render_to_csv_response
from dry_rest_permissions.generics import DRYPermissionFiltersBase, DRYPermissions
from rest_framework import filters as rest_framework_filters
from rest_framework import mixins
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.resources import ResourceRequestCommentSerializer, ResourceRequestSerializer
from care.facility.models import (
    RESOURCE_CATEGORY_CHOICES,
    RESOURCE_STATUS_CHOICES,
    ResourceRequest,
    ResourceRequestComment,
    User,
)
from care.facility.models.resources import RESOURCE_SUB_CATEGORY_CHOICES
from care.utils.cache.cache_allowed_facilities import get_accessible_facilities
from care.utils.filters import CareChoiceFilter


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


inverse_resource_status = inverse_choices(RESOURCE_STATUS_CHOICES)
inverse_category = inverse_choices(RESOURCE_CATEGORY_CHOICES)
inverse_sub_category = inverse_choices(RESOURCE_SUB_CATEGORY_CHOICES)


def get_request_queryset(request, queryset):
    if request.user.is_superuser:
        pass
    else:
        if request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            q_objects = Q(orgin_facility__state=request.user.state)
            q_objects |= Q(approving_facility__state=request.user.state)
            q_objects |= Q(assigned_facility__state=request.user.state)
            return queryset.filter(q_objects)
        elif request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            q_objects = Q(orgin_facility__district=request.user.district)
            q_objects |= Q(approving_facility__district=request.user.district)
            q_objects |= Q(assigned_facility__district=request.user.district)
            return queryset.filter(q_objects)
        facility_ids = get_accessible_facilities(request.user)
        q_objects = Q(orgin_facility__id__in=facility_ids)
        q_objects |= Q(approving_facility__id__in=facility_ids)
        q_objects |= Q(assigned_facility__id__in=facility_ids)
        queryset = queryset.filter(q_objects)
    return queryset


class ResourceFilterSet(filters.FilterSet):

    status = CareChoiceFilter(choice_dict=inverse_resource_status)
    category = CareChoiceFilter(choice_dict=inverse_category)
    sub_category = CareChoiceFilter(choice_dict=inverse_sub_category)

    facility = filters.UUIDFilter(field_name="facility__external_id")
    orgin_facility = filters.UUIDFilter(field_name="orgin_facility__external_id")
    approving_facility = filters.UUIDFilter(field_name="approving_facility__external_id")
    assigned_facility = filters.UUIDFilter(field_name="assigned_facility__external_id")
    created_date = filters.DateFromToRangeFilter(field_name="created_date")
    modified_date = filters.DateFromToRangeFilter(field_name="modified_date")
    assigned_to = filters.NumberFilter(field_name="assigned_to__id")
    created_by = filters.NumberFilter(field_name="created_by__id")
    last_edited_by = filters.NumberFilter(field_name="last_edited_by__id")
    priority = filters.NumberFilter(field_name="priority")
    emergency = filters.BooleanFilter(field_name="emergency")


class ResourceRequestViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    serializer_class = ResourceRequestSerializer
    lookup_field = "external_id"
    queryset = ResourceRequest.objects.all().select_related(
        "orgin_facility",
        "orgin_facility__ward",
        "orgin_facility__local_body",
        "orgin_facility__district",
        "orgin_facility__state",
        "approving_facility",
        "approving_facility__ward",
        "approving_facility__local_body",
        "approving_facility__district",
        "approving_facility__state",
        "assigned_facility",
        "assigned_facility__ward",
        "assigned_facility__local_body",
        "assigned_facility__district",
        "assigned_facility__state",
        "assigned_to",
        "created_by",
        "last_edited_by",
    )
    ordering_fields = ["id", "created_date", "modified_date", "emergency", "priority"]

    permission_classes = (IsAuthenticated, DRYPermissions)
    filter_backends = (filters.DjangoFilterBackend, rest_framework_filters.OrderingFilter)
    filterset_class = ResourceFilterSet

    def get_queryset(self):
        return get_request_queryset(self.request, self.queryset)

    def list(self, request, *args, **kwargs):
        if settings.CSV_REQUEST_PARAMETER in request.GET:
            queryset = self.filter_queryset(self.get_queryset()).values(*ResourceRequest.CSV_MAPPING.keys())
            return render_to_csv_response(
                queryset,
                field_header_map=ResourceRequest.CSV_MAPPING,
                field_serializer_map=ResourceRequest.CSV_MAKE_PRETTY,
            )
        return super().list(request, *args, **kwargs)


class ResourceRequestCommentViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    serializer_class = ResourceRequestCommentSerializer
    lookup_field = "external_id"
    queryset = ResourceRequestComment.objects.all()
    ordering_fields = ["created_date", "modified_date"]

    permission_classes = (IsAuthenticated,)
    filter_backends = (rest_framework_filters.OrderingFilter,)

    def get_queryset(self):
        queryset = self.queryset.filter(request__external_id=self.kwargs.get("resource_external_id"))
        if self.request.user.is_superuser:
            pass
        else:
            if self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
                q_objects = Q(request__orgin_facility__state=self.request.user.state)
                q_objects |= Q(request__approving_facility__state=self.request.user.state)
                q_objects |= Q(request__assigned_facility__state=self.request.user.state)
                return queryset.filter(q_objects)
            elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
                q_objects = Q(request__orgin_facility__district=self.request.user.district)
                q_objects |= Q(request__approving_facility__district=self.request.user.district)
                q_objects |= Q(request__assigned_facility__district=self.request.user.district)
                return queryset.filter(q_objects)
            facility_ids = get_accessible_facilities(self.request.user)
            q_objects = Q(request__orgin_facility__id__in=facility_ids)
            q_objects |= Q(request__approving_facility__id__in=facility_ids)
            q_objects |= Q(request__assigned_facility__id__in=facility_ids)
            queryset = queryset.filter(q_objects)
        return queryset

    def get_request(self):
        queryset = get_request_queryset(self.request, ResourceRequest.objects.all())
        queryset = queryset.filter(external_id=self.kwargs.get("resource_external_id"))
        return get_object_or_404(queryset)

    def perform_create(self, serializer):
        serializer.save(request=self.get_request())

