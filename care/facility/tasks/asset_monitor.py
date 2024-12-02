import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from care.facility.models.asset import Asset, AvailabilityRecord, AvailabilityStatus
from care.utils.assetintegration.asset_classes import AssetClasses

if TYPE_CHECKING:
    from care.utils.assetintegration.base import BaseAssetIntegration

logger = logging.getLogger(__name__)


@shared_task
def check_asset_status():  # noqa: PLR0912
    logger.info("Checking Asset Status: %s", timezone.now())

    assets = (
        Asset.objects.exclude(Q(asset_class=None) | Q(asset_class=""))
        .select_related(
            "current_location",
            "current_location__facility",
        )
        .only(
            "external_id",
            "meta",
            "asset_class",
            "current_location__middleware_address",
            "current_location__facility__middleware_address",
        )
    )
    asset_content_type = ContentType.objects.get_for_model(Asset)

    for asset in assets:
        # Skipping if local IP address is not present
        if not asset.meta.get("local_ip_address", None):
            continue
        try:
            # Fetching middleware hostname
            resolved_middleware = (
                asset.meta.get(
                    "middleware_hostname",
                )  # From asset configuration
                or asset.current_location.middleware_address  # From location configuration
                or asset.current_location.facility.middleware_address  # From facility configuration
            )

            if not resolved_middleware:
                logger.warning(
                    "Asset %s does not have a middleware hostname", asset.external_id
                )
                continue

            result: Any = None

            try:
                # Creating an instance of the asset class
                asset_class: BaseAssetIntegration = AssetClasses[
                    asset.asset_class
                ].value(
                    {
                        **asset.meta,
                        "id": str(asset.external_id),
                        "middleware_hostname": resolved_middleware,
                    }
                )
                # Fetching the status of the device
                if asset.asset_class == "ONVIF":
                    try:
                        # TODO: Remove this block after all assets are migrated to the new middleware
                        asset_config = asset.meta["camera_access_key"].split(":")
                        assets_config = [
                            {
                                "hostname": asset.meta.get("local_ip_address"),
                                "port": 80,
                                "username": asset_config[0],
                                "password": asset_config[1],
                            }
                        ]

                        result = asset_class.api_post(
                            asset_class.get_url("cameras/status"), data=assets_config
                        )
                    except Exception:
                        result = asset_class.api_get(
                            asset_class.get_url("cameras/status")
                        )
                else:
                    result = asset_class.api_get(asset_class.get_url("devices/status"))
            except Exception as e:
                logger.warning("Middleware %s is down: %s", resolved_middleware, e)

            # If no status is returned, setting default status as down
            if not result or "error" in result:
                result = [{"time": timezone.now().isoformat(), "status": []}]

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
                    AvailabilityRecord.objects.filter(
                        content_type=asset_content_type,
                        object_external_id=asset.external_id,
                    )
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
                    AvailabilityRecord.objects.create(
                        content_type=asset_content_type,
                        object_external_id=asset.external_id,
                        status=new_status.value,
                        timestamp=status_record.get("time", timezone.now()),
                    )
        except Exception as e:
            logger.error("Error in Asset Status Check: %s", e)
