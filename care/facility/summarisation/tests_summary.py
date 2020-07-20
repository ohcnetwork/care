from celery.decorators import periodic_task
from celery.schedules import crontab
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.models import Facility, FacilityRelatedSummary, PatientSample
from care.facility.summarisation.facility_capacity import FacilitySummaryFilter, FacilitySummarySerializer
from care.users.models import User


class TestsSummaryViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    lookup_field = "external_id"
    queryset = FacilityRelatedSummary.objects.filter(s_type="TestSummary").order_by("-created_date")
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


def tests_summary():
    facilities = Facility.objects.all()
    for facility in facilities:
        facility_total_patients_count = facility.consultations.all().distinct("patient_id").count()
        facility_patients_samples = PatientSample.objects.filter(consultation__facility_id=facility.id)
        total_tests_count = facility_patients_samples.count()
        results_positive_count = facility_patients_samples.filter(
            result=PatientSample.SAMPLE_TEST_RESULT_MAP["POSITIVE"]
        ).count()
        results_awaited_count = facility_patients_samples.filter(
            result=PatientSample.SAMPLE_TEST_RESULT_MAP["AWAITING"]
        ).count()
        results_negative_count = facility_patients_samples.filter(
            result=PatientSample.SAMPLE_TEST_RESULT_MAP["NEGATIVE"]
        ).count()
        test_discarded_count = facility_patients_samples.filter(
            result=PatientSample.SAMPLE_TEST_RESULT_MAP["INVALID"]
        ).count()
        facility_tests_summarised_data = {
            "facility_name": facility.name,
            "district": facility.district.name,
            "total_patients": facility_total_patients_count,
            "total_tests": total_tests_count,
            "result_positive": results_positive_count,
            "result_awaited": results_awaited_count,
            "result_negative": results_negative_count,
            "test_discarded": test_discarded_count,
        }

        try:
            facility_test_summary = FacilityRelatedSummary.objects.get(
                s_type="TestSummary", created_date__startswith=timezone.now().date(), facility=facility
            )
            facility_test_summary.created_date = timezone.now()
            facility_test_summary.data.pop("modified_date")
            if not facility_test_summary.data == facility_tests_summarised_data:
                facility_test_summary.data = facility_tests_summarised_data
                latest_modification_date = timezone.now()
                facility_test_summary.data.update(
                    {"modified_date": latest_modification_date.strftime("%d-%m-%Y %H:%M")}
                )
                facility_test_summary.save()
        except ObjectDoesNotExist:
            modified_date = timezone.now()
            facility_tests_summarised_data.update({"modified_date": modified_date.strftime("%d-%m-%Y %H:%M")})
            FacilityRelatedSummary.objects.create(
                s_type="TestSummary", facility=facility, data=facility_tests_summarised_data
            )


@periodic_task(run_every=crontab(hour=23, minute=59))
def run_midnight():
    tests_summary()
