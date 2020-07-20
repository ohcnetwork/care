from datetime import timedelta

from celery.decorators import periodic_task
from celery.schedules import crontab
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django_filters import rest_framework as filters
from rest_framework import serializers, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.facility import FacilitySerializer
from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import FacilityCapacity, FacilityRelatedSummary
from care.users.models import User


class FacilitySummarySerializer(serializers.ModelSerializer):

    facility = FacilitySerializer()

    class Meta:
        model = FacilityRelatedSummary
        exclude = (
            "id",
            "s_type",
        )


class FacilitySummaryFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name="created_date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="created_date", lookup_expr="lte")


class FacilityCapacitySummaryViewSet(
    RetrieveModelMixin, ListModelMixin, GenericViewSet,
):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="FacilityCapacity").order_by("-created_date")
    permission_classes = (IsAuthenticated,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            return queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictAdmin"]:
            return queryset.filter(facility__district=user.district)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return queryset.filter(facility__state=user.state)
        return queryset.filter(facility__users__id__exact=user.id)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), facility__external_id=self.kwargs.get("external_id"))


def FacilityCapacitySummary():
    capacity_objects = FacilityCapacity.objects.all().select_related(
        "facility", "facility__state", "facility__district", "facility__local_body"
    )
    capacity_summary = {}
    for capacity_object in capacity_objects:
        facility_id = capacity_object.facility.id
        if facility_id not in capacity_summary:
            capacity_summary[facility_id] = FacilitySerializer(capacity_object.facility).data
            capacity_summary[facility_id]["availability"] = []
        capacity_summary[facility_id]["availability"].append(FacilityCapacitySerializer(capacity_object).data)

    for i in list(capacity_summary.keys()):
        FacilityRelatedSummary(s_type="FacilityCapacity", facility_id=i, data=capacity_summary[i]).save()

    return True


@periodic_task(run_every=crontab(hour=23, minute=59))
def run_midnight():
    FacilityCapacitySummary()
    print("Summarised Capacities")
