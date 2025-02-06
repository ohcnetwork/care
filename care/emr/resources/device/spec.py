from datetime import datetime
from enum import Enum

from pydantic import UUID4

from care.emr.models import Device
from care.emr.resources.base import EMRResource
from care.emr.resources.common.contact_point import ContactPoint


class DeviceStatusChoices(str, Enum):
    active = "active"
    inactive = "inactive"
    entered_in_error = "entered_in_error"


class DeviceAvailabilityStatusChoices(str, Enum):
    lost = "lost"
    damaged = "damaged"
    destroyed = "destroyed"
    available = "available"


class DeviceSpecBase(EMRResource):
    __model__ = Device
    __exclude__ = [
        "facility",
        "managing_organization",
        "current_location",
        "current_encounter",
    ]

    id: UUID4 = None

    identifier: str | None = None
    status: DeviceStatusChoices
    availability_status: DeviceAvailabilityStatusChoices
    manufacturer: str | None = None
    manufacture_date: datetime | None = None
    expiration_date: datetime | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    registered_name: str
    user_friendly_name: str | None = None
    model_number: str | None = None
    part_number: str | None = None
    contact: list[ContactPoint] = []
    care_type: str | None = None


class DeviceCreateSpec(DeviceSpecBase):
    pass


class DeviceUpdateSpec(DeviceSpecBase):
    pass


class DeviceListSpec(DeviceCreateSpec):
    pass


class DeviceRetrieveSpec(DeviceListSpec):
    pass
