from celery import current_app
from celery.schedules import crontab

from care.facility.tasks.asset_monitor import check_asset_status
from care.facility.tasks.cleanup import delete_old_notifications
from care.facility.tasks.plausible_stats import capture_goals
from care.facility.tasks.summarisation import (
    summarise_district_patient,
    summarise_facility_capacity,
    summarise_patient,
    summarise_tests,
    summarise_triage,
)


@current_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour="0", minute="0"),
        delete_old_notifications.s(),
        name="delete_old_notifications",
    )
    sender.add_periodic_task(
        crontab(hour="*/4", minute="59"),
        summarise_triage.s(),
        name="summarise_triage",
    )
    sender.add_periodic_task(
        crontab(hour="23", minute="59"),
        summarise_tests.s(),
        name="summarise_tests",
    )
    sender.add_periodic_task(
        crontab(minute="*/5"),
        summarise_facility_capacity.s(),
        name="summarise_facility_capacity",
    )
    sender.add_periodic_task(
        crontab(hour="*/1", minute="59"),
        summarise_patient.s(),
        name="summarise_patient",
    )
    sender.add_periodic_task(
        crontab(hour="*/1", minute="59"),
        summarise_district_patient.s(),
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
