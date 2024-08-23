from celery import shared_task

from care.facility.models.asset import Asset, AssetLocation
from care.facility.models.facility import Facility


@shared_task
def soft_delete_assets_schedule():
    Asset.objects.filter(
        current_location__id__in=AssetLocation._base_manager.filter(
            facility__id__in=Facility._base_manager.filter(deleted=True).values_list(
                "id", flat=True
            )
        ).values_list("id", flat=True)
    ).update(deleted=True)
