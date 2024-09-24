from celery import shared_task
from celery.utils.log import get_task_logger

from care.facility.utils.summarization.district.patient_summary import (
    district_patient_summary,
)
from care.facility.utils.summarization.facility_capacity import (
    facility_capacity_summary,
)
from care.facility.utils.summarization.patient_summary import patient_summary
from care.facility.utils.summarization.tests_summary import tests_summary
from care.facility.utils.summarization.triage_summary import triage_summary

logger = get_task_logger(__name__)


@shared_task
def summarize_triage():
    triage_summary()
    logger.info("Summarized Triages")


@shared_task
def summarize_tests():
    tests_summary()
    logger.info("Summarized Tests")


@shared_task
def summarize_facility_capacity():
    facility_capacity_summary()
    logger.info("Summarized Facility Capacities")


@shared_task
def summarize_patient():
    patient_summary()
    logger.info("Summarized Patients")


@shared_task
def summarize_district_patient():
    district_patient_summary()
    logger.info("Summarized District Patients")
