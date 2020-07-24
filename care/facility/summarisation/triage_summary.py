from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.models import Facility, FacilityPatientStatsHistory, FacilityRelatedSummary
from care.facility.summarisation.facility_capacity import FacilitySummaryFilter, FacilitySummarySerializer
from care.users.models import User


class TriageSummaryViewSet(ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="TriageSummary").order_by("-created_date")
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


def TriageSummary():
    facilities = Facility.objects.all()
    for facility in facilities:
        facility_patient_data = FacilityPatientStatsHistory.objects.filter(facility=facility).aggregate(
            total_patients_visited=Sum("num_patients_visited"),
            total_patients_home_quarantine=Sum("num_patients_home_quarantine"),
            total_patients_isolation=Sum("num_patients_isolation"),
            total_patients_referred=Sum("num_patient_referred"),
            total_count=Count("id"),
        )
        total_count = facility_patient_data.get("total_count")
        total_patients_home_quarantine = facility_patient_data.get("total_patients_home_quarantine")
        total_patients_referred = facility_patient_data.get("total_patients_referred")
        total_patients_isolation = facility_patient_data.get("total_patients_visited")
        total_patients_visited = facility_patient_data.get("total_patients_isolation")
        try:
            avg_patients_home_quarantine = int(total_patients_home_quarantine / total_count)
            avg_patients_referred = int(total_patients_referred / total_count)
            avg_patients_isolation = int(total_patients_isolation / total_count)
            avg_patients_visited = int(total_patients_visited / total_count)
        except ZeroDivisionError:
            avg_patients_home_quarantine = 0
            avg_patients_referred = 0
            avg_patients_isolation = 0
            avg_patients_visited = 0

        facility_triage_summarised_data = {
            "facility_name": facility.name,
            "district": facility.district.name,
            "total_patients_home_quarantine": total_patients_home_quarantine,
            "total_patients_referred": total_patients_referred,
            "total_patients_isolation": total_patients_isolation,
            "total_patients_visited": total_patients_visited,
            "avg_patients_home_quarantine": avg_patients_home_quarantine,
            "avg_patients_referred": avg_patients_referred,
            "avg_patients_isolation": avg_patients_isolation,
            "avg_patients_visited": avg_patients_visited,
        }

        facility_triage_summary, created = FacilityRelatedSummary.objects.get_or_create(
            s_type="TriageSummary", created_date__date=timezone.now().date(), facility=facility
        )

        if created:
            modified_date = timezone.now()
            facility_triage_summarised_data.update({"modified_date": modified_date.strftime("%d-%m-%Y %H:%M")})
            facility_triage_summary.data = facility_triage_summarised_data
        else:
            facility_triage_summary.created_date = timezone.now()
            facility_triage_summary.data.pop("modified_date")
            if not facility_triage_summary.data == facility_triage_summarised_data:
                facility_triage_summary.data = facility_triage_summarised_data
                modification_date = timezone.now()
                facility_triage_summary.data.update({"modified_date": modification_date.strftime("%d-%m-%Y %H:%M")})
        facility_triage_summary.save()


@periodic_task(run_every=crontab(hour=23, minute=59))
def run_midnight():
    TriageSummary()
