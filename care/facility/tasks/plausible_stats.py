import logging
from datetime import timedelta
from enum import Enum

import requests
from celery import shared_task
from django.conf import settings
from django.utils.timezone import now

from care.facility.models.stats import Goal, GoalEntry, GoalProperty, GoalPropertyEntry

logger = logging.getLogger(__name__)


class Goals(Enum):
    PATIENT_CONSULTATION_VIEWED = ("facilityId", "consultationId", "userId")
    DOCTOR_CONNECT_CLICKED = ("consultationId", "facilityId", "userId", "page")
    CAMERA_PRESET_CLICKED = ("presetName", "consultationId", "userId", "result")
    CAMERA_FEED_MOVED = ("direction", "consultationId", "userId")
    PATIENT_PROFILE_VIEWED = ("facilityId", "userId")
    DEVICE_VIEWED = ("bedId", "assetId", "userId")
    PAGEVIEW = ("page",)

    @property
    def formatted_name(self):
        if self == Goals.PAGEVIEW:
            return "pageview"  # pageview is a reserved goal in plausible
        return self.name.replace("_", " ").title()


def get_goal_stats(plausible_host, site_id, date, goal_name):
    goal_filter = f"event:name=={goal_name}"
    url = f"https://{plausible_host}/api/v1/stats/aggregate"

    params = {
        "site_id": site_id,
        "filters": goal_filter,
        "period": "day",
        "date": date,
        "metrics": "visitors,events",
    }

    response = requests.get(
        url,
        params=params,
        headers={
            "Authorization": "Bearer " + settings.PLAUSIBLE_AUTH_TOKEN,
        },
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


def get_goal_event_stats(plausible_host, site_id, date, goal_name, event_name):
    goal_filter = f"event:name=={goal_name}"

    # pageview is a reserved goal in plausible which uses event:page
    if goal_name == "pageview" and event_name == "page":
        goal_event = "event:page"
    else:
        goal_event = f"event:props:{event_name}"

    url = f"https://{plausible_host}/api/v1/stats/breakdown"

    params = {
        "site_id": site_id,
        "property": goal_event,
        "filters": goal_filter,
        "period": "day",
        "date": date,
        "metrics": "visitors,events",
    }

    response = requests.get(
        url,
        params=params,
        headers={
            "Authorization": "Bearer " + settings.PLAUSIBLE_AUTH_TOKEN,
        },
        timeout=60,
    )

    response.raise_for_status()

    return response.json()


@shared_task
def capture_goals():
    if (
        not settings.PLAUSIBLE_HOST
        or not settings.PLAUSIBLE_SITE_ID
        or not settings.PLAUSIBLE_AUTH_TOKEN
    ):
        logger.info("Plausible is not configured, skipping")
        return
    today = now().date()
    yesterday = today - timedelta(days=1)
    logger.info("Capturing Goals for %s", yesterday)

    for goal in Goals:
        try:
            goal_name = goal.formatted_name
            goal_data = get_goal_stats(
                settings.PLAUSIBLE_HOST,
                settings.PLAUSIBLE_SITE_ID,
                yesterday,
                goal_name,
            )
            goal_object, _ = Goal.objects.get_or_create(
                name=goal_name,
            )
            goal_entry_object, _ = GoalEntry.objects.get_or_create(
                goal=goal_object,
                date=yesterday,
            )
            goal_entry_object.visitors = goal_data["results"]["visitors"]["value"]
            goal_entry_object.events = goal_data["results"]["events"]["value"]
            goal_entry_object.save()

            logger.info("Saved goal entry for %s on %s", goal_name, yesterday)

            for property_name in goal.value:
                goal_property_stats = get_goal_event_stats(
                    settings.PLAUSIBLE_HOST,
                    settings.PLAUSIBLE_SITE_ID,
                    yesterday,
                    goal_name,
                    property_name,
                )
                for property_statistic in goal_property_stats["results"]:
                    property_object, _ = GoalProperty.objects.get_or_create(
                        goal=goal_object,
                        name=property_name,
                    )
                    property_entry_object, _ = GoalPropertyEntry.objects.get_or_create(
                        goal_property=property_object,
                        goal_entry=goal_entry_object,
                        value=property_statistic[property_name],
                    )
                    property_entry_object.visitors = property_statistic["visitors"]
                    property_entry_object.events = property_statistic["events"]
                    property_entry_object.save()
                logger.info(
                    "Saved goal property entry for %s and property %s on %s",
                    goal_name,
                    property_name,
                    yesterday,
                )

        except Exception as e:
            logger.error("Failed to process goal %s due to error: %s", goal_name, e)
