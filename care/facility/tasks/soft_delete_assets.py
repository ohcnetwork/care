from celery import shared_task

from care.facility.models.asset import Asset
from care.facility.models.facility import Facility


@shared_task
def soft_delete_assets_schedule():
    facilities = Facility.objects.all().values_list("id", flat=True)
    Asset.objects.exclude(current_location__facility__id__in=facilities).update(
        deleted=True
    )
