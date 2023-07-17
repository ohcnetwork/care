from datetime import datetime
from typing import Any

from celery import shared_task

from care.facility.models.asset import (
    Asset,
    AssetAvailabilityRecord,
    AvailabilityStatus,
)
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.assetintegration.base import BaseAssetIntegration


@shared_task
def check_asset_status():
    print("Checking Asset Status", datetime.now())
    assets = Asset.objects.all()
    middleware_status_cache = {}

    for asset in assets:
        if not asset.asset_class or not asset.meta.get("local_ip_address", None):
            continue
        try:
            hostname = asset.meta.get(
                "middleware_hostname",
                asset.current_location.facility.middleware_address,
            )
            result: Any = {}

            if hostname in middleware_status_cache:
                result = middleware_status_cache[hostname]
            else:
                try:
                    asset_class: BaseAssetIntegration = AssetClasses[
                        asset.asset_class
                    ].value(
                        {
                            **asset.meta,
                            "middleware_hostname": hostname,
                        }
                    )
                    result = asset_class.api_get(asset_class.get_url("devices/status"))
                    middleware_status_cache[hostname] = result
                except Exception as e:
                    print("Error in Asset Status Check", e)
                    middleware_status_cache[hostname] = None
                    continue

            if not result:
                continue

            new_status = None
            for status_record in result:
                if asset.meta.get("local_ip_address") in status_record.get(
                    "status", {}
                ):
                    new_status = status_record["status"][
                        asset.meta.get("local_ip_address")
                    ]
                else:
                    new_status = "not_monitored"

                last_record = (
                    AssetAvailabilityRecord.objects.filter(asset=asset)
                    .order_by("-timestamp")
                    .first()
                )

                if new_status == "up":
                    new_status = AvailabilityStatus.OPERATIONAL
                elif new_status == "down":
                    new_status = AvailabilityStatus.DOWN
                elif new_status == "maintenance":
                    new_status = AvailabilityStatus.UNDER_MAINTENANCE
                else:
                    new_status = AvailabilityStatus.NOT_MONITORED

                if not last_record or (
                    datetime.fromisoformat(status_record.get("time"))
                    > last_record.timestamp
                    and last_record.status != new_status.value
                ):
                    AssetAvailabilityRecord.objects.create(
                        asset=asset,
                        status=new_status.value,
                        timestamp=status_record.get("time", datetime.now()),
                    )

        except Exception as e:
            print("Error in Asset Status Check", e)
