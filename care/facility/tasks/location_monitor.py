import logging
from typing import Any

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from care.facility.models.asset import (
    AssetLocation,
    AvailabilityRecord,
    AvailabilityStatus,
)
from care.utils.assetintegration.base import BaseAssetIntegration

logger = logging.getLogger(__name__)


@shared_task
def check_location_status():
    location_content_type = ContentType.objects.get_for_model(AssetLocation)
    logger.info("Checking Location Status: %s", timezone.now())
    locations = AssetLocation.objects.all()

    for location in locations:
        try:
            # Resolving the middleware hostname from location or facility configuration [ in that order ]
            resolved_middleware = (
                location.middleware_address or location.facility.middleware_address
            )

            if not resolved_middleware:
                logger.warning(
                    "No middleware hostname resolved for location %s",
                    location.external_id,
                )
                continue

            result: Any = None

            # Setting new status as down by default
            new_status = AvailabilityStatus.DOWN

            try:
                # To check for uptime of just the middleware, we do not require a specific asset class
                location_class = BaseAssetIntegration(
                    {"middleware_hostname": resolved_middleware, "local_ip_address": ""}
                )
                # Fetching this endpoint to check if the middleware is up
                result = location_class.api_get(
                    location_class.get_url("devices/status")
                )

                # Setting new status as operational if the middleware is up
                if result:
                    new_status = AvailabilityStatus.OPERATIONAL

            except Exception as e:
                logger.warning("Middleware %s is down: %s", resolved_middleware, e)

            # Fetching the last record of the location
            last_record = (
                AvailabilityRecord.objects.filter(
                    content_type=location_content_type,
                    object_external_id=location.external_id,
                )
                .order_by("-timestamp")
                .first()
            )

            # Creating a new record if the status has changed
            if not last_record or last_record.status != new_status.value:
                AvailabilityRecord.objects.create(
                    content_type=location_content_type,
                    object_external_id=location.external_id,
                    status=new_status.value,
                    timestamp=timezone.now(),
                )
            logger.info(
                "Location %s status: %s", location.external_id, new_status.value
            )
        except Exception as e:
            logger.error("Error in Location Status Check: %s", e)
