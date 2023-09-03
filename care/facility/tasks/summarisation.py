from logging import Logger

from celery import shared_task
from celery.utils.log import get_task_logger

from care.facility.utils.summarisation.district.patient_summary import (
    district_patient_summary,
)
from care.facility.utils.summarisation.facility_capacity import (
    facility_capacity_summary,
)
from care.facility.utils.summarisation.patient_summary import patient_summary
from care.facility.utils.summarisation.tests_summary import tests_summary
from care.facility.utils.summarisation.triage_summary import triage_summary

logger: Logger = get_task_logger(__name__)


@shared_task
def summarise_triage():
    triage_summary()
    logger.info("Summarised Triages")


@shared_task
def summarise_tests():
    tests_summary()
    logger.info("Summarised Tests")


@shared_task
def summarise_facility_capacity():
    facility_capacity_summary()
    logger.info("Summarised Facility Capacities")


@shared_task
def summarise_patient():
    patient_summary()
    logger.info("Summarised Patients")


@shared_task
def summarise_district_patient():
    district_patient_summary()
    logger.info("Summarised District Patients")
