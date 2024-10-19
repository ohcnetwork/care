from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from care.facility.models import Facility, FacilityRelatedSummary, PatientSample


def tests_summary():
    facilities = Facility.objects.all()
    for facility in facilities:
        facility_total_patients_count = (
            facility.consultations.all().distinct("patient_id").count()
        )
        facility_patients_samples = PatientSample.objects.filter(
            consultation__facility_id=facility.id
        )
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
                s_type="TestSummary",
                created_date__startswith=timezone.now().date(),
                facility=facility,
            )
            facility_test_summary.created_date = timezone.now()
            facility_test_summary.data.pop("modified_date")
            if facility_test_summary.data != facility_tests_summarised_data:
                facility_test_summary.data = facility_tests_summarised_data
                latest_modification_date = timezone.now()
                facility_test_summary.data["modified_date"] = (
                    latest_modification_date.strftime("%d-%m-%Y %H:%M")
                )
                facility_test_summary.save()
        except ObjectDoesNotExist:
            modified_date = timezone.now()
            facility_tests_summarised_data["modified_date"] = modified_date.strftime(
                "%d-%m-%Y %H:%M"
            )
            FacilityRelatedSummary.objects.create(
                s_type="TestSummary",
                facility=facility,
                data=facility_tests_summarised_data,
            )
