from celery.decorators import periodic_task
from celery.schedules import crontab
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime, now
from django.views.decorators.cache import cache_page
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.facility import FacilitySerializer
from care.facility.api.serializers.facility_capacity import FacilityCapacitySerializer
from care.facility.models import Facility, FacilityCapacity, FacilityRelatedSummary, PatientRegistration
from care.facility.models.inventory import FacilityInventoryBurnRate, FacilityInventoryLog, FacilityInventorySummary
from care.facility.models.patient import PatientRegistration


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
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    @method_decorator(cache_page(60 * 10))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    # def get_queryset(self):
    #     user = self.request.user
    #     queryset = self.queryset
    #     if user.is_superuser:
    #         return queryset
    #     elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]:
    #         return queryset.filter(facility__district=user.district)
    #     elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]:
    #         return queryset.filter(facility__state=user.state)
    #     return queryset.filter(facility__users__id__exact=user.id)


def FacilityCapacitySummary():
    capacity_objects = FacilityCapacity.objects.all().select_related(
        "facility", "facility__state", "facility__district", "facility__local_body"
    )
    capacity_summary = {}
    current_date = localtime(now()).replace(hour=0, minute=0, second=0, microsecond=0)

    for facility_obj in Facility.objects.all():
        # Calculate Actual Patients Discharged and Live in this Facility
        patients_in_facility = PatientRegistration.objects.filter(facility_id=facility_obj.id).select_related(
            "state", "district", "local_body"
        )
        capacity_summary[facility_obj.id] = FacilitySerializer(facility_obj).data
        capacity_summary[facility_obj.id]["features"] = list(capacity_summary[facility_obj.id]["features"])
        capacity_summary[facility_obj.id]["actual_live_patients"] = patients_in_facility.filter(is_active=True).count()
        discharge_patients = patients_in_facility.filter(is_active=False)
        capacity_summary[facility_obj.id]["actual_discharged_patients"] = discharge_patients.count()
        capacity_summary[facility_obj.id]["availability"] = []

        temp_inventory_summary_obj = {}
        summary_objs = FacilityInventorySummary.objects.filter(facility_id=facility_obj.id)
        for summary_obj in summary_objs:
            burn_rate = FacilityInventoryBurnRate.objects.filter(
                facility_id=facility_obj.id, item_id=summary_obj.item.id
            ).first()
            log_query = FacilityInventoryLog.objects.filter(
                facility_id=facility_obj.id,
                item_id=summary_obj.item.id,
                created_date__gte=current_date,
                probable_accident=False,
            )
            # start_log = log_query.order_by("created_date").first()
            end_log = log_query.order_by("-created_date").first()
            # start_stock = summary_obj.quantity_in_default_unit
            # if start_log:
            #     if start_log.is_incoming:  # Add current value to current stock to get correct stock
            #         start_stock = start_log.current_stock + start_log.quantity_in_default_unit
            #     else:
            #         start_stock = start_log.current_stock - start_log.quantity_in_default_unit
            end_stock = summary_obj.quantity
            if end_log:
                end_stock = end_log.current_stock
            total_consumed = 0
            temp1 = log_query.filter(is_incoming=False).aggregate(Sum("quantity_in_default_unit"))
            if temp1:
                total_consumed = temp1.get("quantity_in_default_unit__sum", 0)
                if not total_consumed:
                    total_consumed = 0
            total_added = 0
            temp2 = log_query.filter(is_incoming=True).aggregate(Sum("quantity_in_default_unit"))
            if temp2:
                total_added = temp2.get("quantity_in_default_unit__sum", 0)
                if not total_added:
                    total_added = 0

            # Calculate Start Stock as
            # end_stock = start_stock - consumption + addition
            # start_stock = end_stock - addition + consumption
            # This way the start stock will never veer off course

            start_stock = end_stock - total_added + total_consumed

            if burn_rate:
                burn_rate = burn_rate.burn_rate
            temp_inventory_summary_obj[summary_obj.item.id] = {
                "item_name": summary_obj.item.name,
                "stock": summary_obj.quantity,
                "unit": summary_obj.item.default_unit.name,
                "is_low": summary_obj.is_low,
                "burn_rate": burn_rate,
                "start_stock": start_stock,
                "end_stock": end_stock,
                "total_consumed": total_consumed,
                "total_added": total_added,
                "modified_date": summary_obj.modified_date.astimezone().isoformat(),
            }
        capacity_summary[facility_obj.id]["inventory"] = temp_inventory_summary_obj

    for capacity_object in capacity_objects:
        facility_id = capacity_object.facility.id
        if facility_id not in capacity_summary:
            capacity_summary[facility_id] = FacilitySerializer(capacity_object.facility).data
        if "availability" not in capacity_summary[facility_id]:
            capacity_summary[facility_id]["availability"] = []
        capacity_summary[facility_id]["availability"].append(FacilityCapacitySerializer(capacity_object).data)

    for i in capacity_summary:
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
