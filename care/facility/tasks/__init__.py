from celery import current_app
from celery.schedules import crontab
from django.conf import settings

from care.facility.tasks.asset_monitor import check_asset_status
from care.facility.tasks.cleanup import delete_old_notifications
from care.facility.tasks.location_monitor import check_location_status
from care.facility.tasks.plausible_stats import capture_goals
from care.facility.tasks.redis_index import load_redis_index
from care.facility.tasks.summarisation import (
    summarize_district_patient,
    summarize_facility_capacity,
    summarize_patient,
    summarize_tests,
    summarize_triage,
)


@current_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour="0", minute="0"),
        delete_old_notifications.s(),
        name="delete_old_notifications",
    )
    if settings.TASK_SUMMARIZE_TRIAGE:
        sender.add_periodic_task(
            crontab(hour="*/4", minute="59"),
            summarize_triage.s(),
            name="summarise_triage",
        )
    if settings.TASK_SUMMARIZE_TESTS:
        sender.add_periodic_task(
            crontab(hour="23", minute="59"),
            summarize_tests.s(),
            name="summarise_tests",
        )
    if settings.TASK_SUMMARIZE_FACILITY_CAPACITY:
        sender.add_periodic_task(
            crontab(minute="*/5"),
            summarize_facility_capacity.s(),
            name="summarise_facility_capacity",
        )
    if settings.TASK_SUMMARIZE_PATIENT:
        sender.add_periodic_task(
            crontab(hour="*/1", minute="59"),
            summarize_patient.s(),
            name="summarise_patient",
        )
    if settings.TASK_SUMMARIZE_DISTRICT_PATIENT:
        sender.add_periodic_task(
            crontab(hour="*/1", minute="59"),
            summarize_district_patient.s(),
            name="summarise_district_patient",
        )

    sender.add_periodic_task(
        crontab(minute="*/30"),
        check_asset_status.s(),
        name="check_asset_status",
    )
    sender.add_periodic_task(
        crontab(hour="0", minute="0"),
        capture_goals.s(),
        name="capture_goals",
    )
    sender.add_periodic_task(
        crontab(hour="*", minute="0"),
        load_redis_index.s(),
        name="load_redis_index",
    )
    sender.add_periodic_task(
        crontab(minute="*/30"),
        check_location_status.s(),
        name="check_location_status",
    )
