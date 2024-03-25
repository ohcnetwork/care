import os

from celery import Celery

from care.facility.models.asset import Asset
from care.facility.models.facility import Facility

broker_url = os.environ.get("CELERY_BROKER_URL")
app = Celery("soft_delete_assets", broker=broker_url)


@app.task
def soft_delete_assets_schedule():
    facilities = Facility.objects.all().values_list("name", flat=True)
    Asset.objects.exclude(current_location__facility__name__in=facilities).update(
        deleted=True
    )
