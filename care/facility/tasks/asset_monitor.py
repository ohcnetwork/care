from datetime import datetime

from celery import shared_task

from care.facility.models.asset import Asset, AssetAvailabilityRecord
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.assetintegration.base import BaseAssetIntegration


@shared_task
def check_asset_status():
    assets = Asset.objects.filter(is_working=True)

    for asset in assets:
        asset_class: BaseAssetIntegration = AssetClasses[asset.asset_class].value(
            {
                **asset.meta,
                "middleware_hostname": asset.current_location.facility.middleware_address,
            }
        )
        result = asset_class.api_get(asset_class.get_url("status"))

        if result and result.get("status"):
            status = result.get("status", "-1")
            if status == "-1":
                continue

            new_status = AssetAvailabilityRecord.AvailabilityStatus(int(status))
            last_record = (
                AssetAvailabilityRecord.objects.filter(asset=asset)
                .order_by("-timestamp")
                .first()
            )

            if not last_record or last_record.status != new_status.value:
                AssetAvailabilityRecord.objects.create(
                    asset=asset, status=new_status.value, timestamp=datetime.now()
                )
