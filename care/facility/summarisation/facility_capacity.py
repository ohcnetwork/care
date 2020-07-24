from datetime import timedelta, datetime
from django.utils.timezone import localtime, now

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
    facility = filters.UUIDFilter(field_name="facility__external_id")
    district = filters.NumberFilter(field_name="facility__district__id")
    local_body = filters.NumberFilter(field_name="facility__local_body__id")
    state = filters.NumberFilter(field_name="facility__state__id")


class FacilityCapacitySummaryViewSet(
    ListModelMixin, GenericViewSet,
):
    lookup_field = "external_id"
    queryset = (
        FacilityRelatedSummary.objects.filter(s_type="FacilityCapacity")
        .order_by("-created_date")
        .select_related("facility", "facility__state", "facility__district", "facility__local_body")
    )
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


def FacilityCapacitySummary():
    capacity_objects = FacilityCapacity.objects.all().select_related(
        "facility", "facility__state", "facility__district", "facility__local_body"
    )
    capacity_summary = {}
    current_date = localtime(now()).replace(hour=0, minute=0, second=0, microsecond=0)
    for capacity_object in capacity_objects:
        facility_id = capacity_object.facility.id
        if facility_id not in capacity_summary:
            capacity_summary[facility_id] = FacilitySerializer(capacity_object.facility).data
            capacity_summary[facility_id]["availability"] = []
        capacity_summary[facility_id]["availability"].append(FacilityCapacitySerializer(capacity_object).data)

    for i in list(capacity_summary.keys()):
        facility_summary_obj = None
        if FacilityRelatedSummary.objects.filter(
            s_type="FacilityCapacity", facility_id=i, created_date__gte=current_date
        ).exists():
            facility_summary_obj = FacilityRelatedSummary.objects.get(
                s_type="FacilityCapacity", facility_id=i, created_date__gte=current_date
            )
        else:
            facility_summary_obj = FacilityRelatedSummary(s_type="FacilityCapacity", facility_id=i)
        facility_summary_obj.data = capacity_summary[i]
        facility_summary_obj.save()

    return True


@periodic_task(run_every=crontab(minute="*/5"))
def run_midnight():
    FacilityCapacitySummary()
    print("Summarised Capacities")
