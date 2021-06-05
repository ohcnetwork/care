from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
from django.db.models import Count, Sum
from django.utils.decorators import method_decorator
from django.utils.timezone import localtime, now
from django.views.decorators.cache import cache_page
from django_filters import rest_framework as filters
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import GenericViewSet

from care.facility.models import Facility, FacilityPatientStatsHistory, FacilityRelatedSummary
from care.facility.summarisation.facility_capacity import FacilitySummaryFilter, FacilitySummarySerializer


class TriageSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="TriageSummary").order_by("-created_date")
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = FacilitySummarySerializer

    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FacilitySummaryFilter

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

    cache_limit = settings.API_CACHE_DURATION_IN_SECONDS

    @method_decorator(cache_page(cache_limit))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


def TriageSummary():
    facilities = Facility.objects.all()
    current_date = localtime(now()).replace(hour=0, minute=0, second=0, microsecond=0)
    for facility in facilities:
        facility_patient_data = FacilityPatientStatsHistory.objects.filter(facility=facility).aggregate(
            total_patients_visited=Sum("num_patients_visited"),
            total_patients_home_quarantine=Sum("num_patients_home_quarantine"),
            total_patients_isolation=Sum("num_patients_isolation"),
            total_patients_referred=Sum("num_patient_referred"),
            total_patients_confirmed_positive=Sum("num_patient_confirmed_positive"),
            total_count=Count("id"),
        )
        total_count = facility_patient_data.get("total_count", 0)
        total_patients_home_quarantine = facility_patient_data.get("total_patients_home_quarantine", 0)
        total_patients_referred = facility_patient_data.get("total_patients_referred", 0)
        total_patients_isolation = facility_patient_data.get("total_patients_visited", 0)
        total_patients_visited = facility_patient_data.get("total_patients_isolation", 0)
        total_patients_confirmed_positive = facility_patient_data.get("num_patient_confirmed_positive", 0)
        if total_count:
            avg_patients_home_quarantine = int(total_patients_home_quarantine / total_count)
            avg_patients_referred = int(total_patients_referred / total_count)
            avg_patients_isolation = int(total_patients_isolation / total_count)
            avg_patients_visited = int(total_patients_visited / total_count)
            avg_patients_confirmed_positive = int(total_patients_confirmed_positive / total_count)
        else:
            avg_patients_home_quarantine = 0
            avg_patients_referred = 0
            avg_patients_isolation = 0
            avg_patients_visited = 0
            avg_patients_confirmed_positive = 0

        facility_triage_summarised_data = {
            "facility_name": facility.name,
            "district": facility.district.name,
            "total_patients_home_quarantine": total_patients_home_quarantine,
            "total_patients_referred": total_patients_referred,
            "total_patients_isolation": total_patients_isolation,
            "total_patients_visited": total_patients_visited,
            "total_patients_confirmed_positive": total_patients_confirmed_positive,
            "avg_patients_home_quarantine": avg_patients_home_quarantine,
            "avg_patients_referred": avg_patients_referred,
            "avg_patients_isolation": avg_patients_isolation,
            "avg_patients_visited": avg_patients_visited,
            "avg_patients_confirmed_positive": avg_patients_confirmed_positive,
        }

        facility_triage_summary = FacilityRelatedSummary.objects.filter(
            s_type="TriageSummary", facility=facility, created_date__gte=current_date
        ).first()

        if facility_triage_summary:
            facility_triage_summary.data = facility_triage_summarised_data
        else:
            facility_triage_summary = FacilityRelatedSummary(
                s_type="TriageSummary", facility=facility, data=facility_triage_summarised_data
            )
        facility_triage_summary.save()


@periodic_task(run_every=crontab(hour="*/4", minute=59))
def run_midnight():
    TriageSummary()
