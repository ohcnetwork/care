"""Build a Beckn catalog from Care facilities, practitioners and availability.

The catalog is published in response to a ``discover`` action. Each Care
``Facility`` with public practitioner schedules becomes a catalog ``provider``;
each schedulable practitioner becomes a ``resource`` carrying its weekly
availability (merged from all its ``Availability`` rows) in the Beckn-native
``resourceAttributes.availabilitySchedule[]`` field; and each practitioner gets
a bookable ``offer``.
"""

from care.beckn.constants import (
    CODED_VALUE_CONTEXT,
    DAY_OF_WEEK_NAMES,
    DEFAULT_HEALTH_SERVICE_TYPE,
    HEALTH_OFFER_CONTEXT,
    HEALTH_RESOURCE_CONTEXT,
    HEALTH_SERVICE_LAB_TEST,
    HEALTH_SERVICE_PHYSICAL_CONSULTATION,
)
from care.emr.models.scheduling.schedule import Availability, Schedule
from care.emr.resources.scheduling.schedule.spec import (
    SchedulableResourceTypeOptions,
    SlotTypeOptions,
)


def _resource_display_name(resource) -> str:
    if (
        resource.resource_type == SchedulableResourceTypeOptions.practitioner.value
        and resource.user
    ):
        return resource.user.get_full_name() or resource.user.username
    if (
        resource.resource_type
        == SchedulableResourceTypeOptions.healthcare_service.value
        and resource.healthcare_service
    ):
        return resource.healthcare_service.name
    if (
        resource.resource_type == SchedulableResourceTypeOptions.location.value
        and resource.location
    ):
        return resource.location.name
    return resource.resource_type


def _health_service_type(resource, schedules) -> str:
    """Resolve the Beckn healthServiceType for a resource.

    Order: an explicit override on any of the resource's schedules
    (``Schedule.meta["beckn"]["healthServiceType"]``), then a type derived from
    the resource kind, then the default.
    """
    for schedule in schedules:
        meta = schedule.meta or {}
        override = (meta.get("beckn", {}) or {}).get("healthServiceType")
        if override:
            return override
    if (
        resource.resource_type
        == SchedulableResourceTypeOptions.healthcare_service.value
    ):
        return HEALTH_SERVICE_LAB_TEST
    if resource.resource_type == SchedulableResourceTypeOptions.location.value:
        return HEALTH_SERVICE_PHYSICAL_CONSULTATION
    return DEFAULT_HEALTH_SERVICE_TYPE


def _availability_schedule(schedules) -> list[dict]:
    """Merge all appointment availabilities of the resource into Beckn slots."""
    slots = []
    availabilities = Availability.objects.filter(
        schedule__in=schedules,
        slot_type=SlotTypeOptions.appointment.value,
    )
    for availability in availabilities:
        for entry in availability.availability or []:
            day_index = entry.get("day_of_week")
            if day_index is None or not 0 <= day_index < len(DAY_OF_WEEK_NAMES):
                continue
            slots.append(
                {
                    "dayOfWeek": DAY_OF_WEEK_NAMES[day_index],
                    "startTime": str(entry.get("start_time", ""))[:5],
                    "endTime": str(entry.get("end_time", ""))[:5],
                }
            )
    return slots


def _is_healthcare_service(resource) -> bool:
    return (
        resource.resource_type
        == SchedulableResourceTypeOptions.healthcare_service.value
    )


def _build_resource(resource, schedules) -> dict:
    health_service_type = _health_service_type(resource, schedules)
    resource_attributes = {
        "@context": HEALTH_RESOURCE_CONTEXT,
        "@type": "hr:HealthResource",
        "healthServiceType": health_service_type,
        "availabilitySchedule": _availability_schedule(schedules),
    }
    # Healthcare services (labs / diagnostics) carry the clinical delivery unit
    # and accepted schemes expected by the network for LAB_TEST resources.
    if _is_healthcare_service(resource):
        resource_attributes["clinicalDeliveryUnit"] = "TEST"
        resource_attributes["acceptedSchemes"] = [
            {
                "@context": CODED_VALUE_CONTEXT,
                "@type": "Scheme",
                "code": "PMJAY",
            }
        ]
    return {
        "id": str(resource.external_id),
        "descriptor": {"name": _resource_display_name(resource)},
        "resourceAttributes": resource_attributes,
    }


def _build_offer(resource, health_service_type: str) -> dict:
    offer_attributes = {
        "@context": HEALTH_OFFER_CONTEXT,
        "@type": "hof:HealthOffer",
        "healthServiceType": health_service_type,
        "offerType": "SINGLE_EVENT",
    }
    # Diagnostic offers commit to producing an outcome (report) within an SLA.
    if _is_healthcare_service(resource):
        offer_attributes["outcomeCommitment"] = {
            "attendanceToOutcomeSlaHours": 24,
            "outcomeNoteFormatStandard": "FHIR/DiagnosticReport",
            "mandatory": True,
        }
    return {
        "id": f"offer-{resource.external_id}",
        "resourceIds": [str(resource.external_id)],
        "descriptor": {"name": f"Appointment - {_resource_display_name(resource)}"},
        "offerAttributes": offer_attributes,
    }


def build_catalogs(public_only: bool = True) -> list[dict]:
    """Return the list of Beckn catalogs for facilities with public schedules."""
    schedules = Schedule.objects.select_related(
        "resource",
        "resource__facility",
        "resource__user",
        "resource__healthcare_service",
        "resource__location",
    )
    if public_only:
        schedules = schedules.filter(is_public=True)

    # facility -> {resource_id -> (resource, [schedules])}
    facilities: dict = {}
    for schedule in schedules:
        resource = schedule.resource
        facility = resource.facility
        facility_bucket = facilities.setdefault(
            facility.id, {"facility": facility, "resources": {}}
        )
        resource_bucket = facility_bucket["resources"].setdefault(
            resource.id, {"resource": resource, "schedules": []}
        )
        resource_bucket["schedules"].append(schedule)

    catalogs = []
    for facility_bucket in facilities.values():
        facility = facility_bucket["facility"]
        resources = []
        offers = []
        for resource_bucket in facility_bucket["resources"].values():
            resource = resource_bucket["resource"]
            resource_schedules = resource_bucket["schedules"]
            resources.append(_build_resource(resource, resource_schedules))
            offers.append(
                _build_offer(
                    resource, _health_service_type(resource, resource_schedules)
                )
            )
        catalogs.append(
            {
                "id": f"catalog-{facility.external_id}",
                "descriptor": {"name": facility.name},
                "provider": {
                    "id": str(facility.external_id),
                    "descriptor": {"name": facility.name},
                },
                "resources": resources,
                "offers": offers,
            }
        )
    return catalogs
