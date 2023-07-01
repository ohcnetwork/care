from celery import shared_task

from care.facility.utils.summarisation.district.patient_summary import (
    district_patient_summary,
)
from care.facility.utils.summarisation.facility_capacity import (
    facility_capacity_summary,
)
from care.facility.utils.summarisation.patient_summary import patient_summary
from care.facility.utils.summarisation.tests_summary import tests_summary
from care.facility.utils.summarisation.triage_summary import triage_summary


@shared_task
def summarise_triage():
    triage_summary()
    print("Summarised Triages")


@shared_task
def summarise_tests():
    tests_summary()
    print("Summarised Tests")


@shared_task
def summarise_facility_capacity():
    facility_capacity_summary()
    print("Summarised Facility Capacities")


@shared_task
def summarise_patient():
    patient_summary()
    print("Summarised Patients")


@shared_task
def summarise_district_patient():
    district_patient_summary()
    print("Summarised District Patients")
