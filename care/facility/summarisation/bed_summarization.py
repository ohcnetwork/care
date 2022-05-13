from celery.decorators import periodic_task
from celery.schedules import crontab
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime, now
from django.views.decorators.cache import cache_page
from django_filters import rest_framework as filters
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import GenericViewSet

from care.facility.models import Facility, FacilityRelatedSummary
from care.facility.models.bed import Bed, ConsultationBed
from care.facility.summarisation.facility_capacity import FacilitySummaryFilter, FacilitySummarySerializer


class FaclityBedSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="FacilityBedsSummary").order_by(
        "-created_date"
    )
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = FacilitySummarySerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

    @method_decorator(cache_page(60 * 10))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


def FacilityBedSummary():
    facility_bed_summary = {}
    current_date = localtime(now()).replace(hour=0, minute=0, second=0, microsecond=0)

    for facility_obj in Facility.objects.all():
        bed_count = Bed.objects.filter(facility=facility_obj).count()
        occupied_bed_count = ConsultationBed.objects.filter(
            bed__facility=facility_obj, end_date__isnull=True
        ).count()

        facility_bed_summary[facility_obj.id] = {
            "facility_name": facility_obj.name,
            "beds_count": bed_count,
            "occupied_beds_count": occupied_bed_count,
            "utilization_percent": occupied_bed_count / bed_count * 100,
        }

    for i in list(facility_bed_summary.keys()):
        try:
            summary_obj = FacilityRelatedSummary.objects.get(
                s_type="FacilityBedsSummary", facility_id=i, created_date__gte=current_date)
        except:
            summary_obj = FacilityRelatedSummary(s_type="FacilityBedsSummary", facility_id=i)
        summary_obj.data = facility_bed_summary[i]
        summary_obj.save()


@periodic_task(run_every=crontab(minute="*/5"))
def run_every_five_minute():
    FacilityBedSummary()
    print("Summarised Beds under Facility")
