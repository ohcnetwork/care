import logging
from datetime import datetime
from typing import Any

from celery import shared_task
from django.utils import timezone

from care.facility.models.asset import (
    Asset,
    AssetAvailabilityRecord,
    AvailabilityStatus,
)
from care.utils.assetintegration.asset_classes import AssetClasses
from care.utils.assetintegration.base import BaseAssetIntegration

logger = logging.getLogger(__name__)


@shared_task
def check_asset_status():
    logger.info(f"Checking Asset Status: {timezone.now()}")

    assets = Asset.objects.all()
    middleware_status_cache = {}

    for asset in assets:
        # Skipping if asset class or local IP address is not present
        if not asset.asset_class or not asset.meta.get("local_ip_address", None):
            continue
        try:
            # Fetching middleware hostname
            hostname = asset.meta.get(
                "middleware_hostname",
                asset.current_location.facility.middleware_address,
            )
            result: Any = None

            # Checking if middleware status is already cached
            if hostname in middleware_status_cache:
                result = middleware_status_cache[hostname]
            else:
                try:
                    # Creating an instance of the asset class
                    asset_class: BaseAssetIntegration = AssetClasses[
                        asset.asset_class
                    ].value(
                        {
                            **asset.meta,
                            "middleware_hostname": hostname,
                        }
                    )
                    # Fetching the status of the device
                    result = asset_class.api_get(asset_class.get_url("devices/status"))
                except Exception:
                    logger.warn(f"Middleware {hostname} is down", exc_info=True)

            # If no status is returned, setting default status as down
            if not result or len(result) == 0:
                result = [{"time": timezone.now().isoformat(), "status": []}]

            middleware_status_cache[hostname] = result

            # Setting new status as down by default
            new_status = AvailabilityStatus.DOWN
            for status_record in result:
                if asset.meta.get("local_ip_address") in status_record.get(
                    "status", {}
                ):
                    asset_status = status_record["status"][
                        asset.meta.get("local_ip_address")
                    ]
                else:
                    asset_status = "down"

                # Fetching the last record of the asset
                last_record = (
                    AssetAvailabilityRecord.objects.filter(asset=asset)
                    .order_by("-timestamp")
                    .first()
                )

                # Setting new status based on the status returned by the device
                if asset_status == "up":
                    new_status = AvailabilityStatus.OPERATIONAL
                elif asset_status == "maintenance":
                    new_status = AvailabilityStatus.UNDER_MAINTENANCE

                # Creating a new record if the status has changed
                if not last_record or (
                    datetime.fromisoformat(status_record.get("time"))
                    > last_record.timestamp
                    and last_record.status != new_status.value
                ):
                    AssetAvailabilityRecord.objects.create(
                        asset=asset,
                        status=new_status.value,
                        timestamp=status_record.get("time", timezone.now()),
                    )

        except Exception:
            logger.error("Error in Asset Status Check", exc_info=True)
