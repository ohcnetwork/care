# from celery import current_app
# from celery.schedules import crontab

# from care.facility.tasks.asset_monitor import check_asset_status
# from care.facility.tasks.cleanup import delete_old_notifications
# from care.facility.tasks.location_monitor import check_location_status

# @current_app.on_after_finalize.connect
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_periodic_task(
#         crontab(hour="0", minute="0"),
#         delete_old_notifications.s(),
#         name="delete_old_notifications",
#     )

#     sender.add_periodic_task(
#         crontab(minute="*/30"),
#         check_asset_status.s(),
#         name="check_asset_status",
#     )
#     sender.add_periodic_task(
#         crontab(minute="*/30"),
#         check_location_status.s(),
#         name="check_location_status",
#     )
