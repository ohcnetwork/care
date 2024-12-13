from datetime import time

from freezegun import freeze_time

from care.facility.models.schedule import (
    Availability,
    SchedulableResource,
    Schedule,
    ScheduleException,
    SlotType,
)
from care.users.models import User


@freeze_time("2024-11-01")
class ScheduleTestSetup:
    @classmethod
    def setup_schedule(cls):
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)

        cls.user = cls.create_user(
            "staff", district=cls.district, local_body=cls.local_body
        )

        cls.facility = cls.create_facility(cls.user, cls.district, cls.local_body)
        cls.doctor_user = cls.create_user(
            "doctor",
            district=cls.district,
            local_body=cls.local_body,
            user_type=User.TYPE_VALUE_MAP["Doctor"],
            home_facility=cls.facility,
        )

        cls.schedulable_resource = SchedulableResource.objects.create(
            facility=cls.facility, resource=cls.doctor_user
        )
        cls.schedule = Schedule.objects.create(
            resource=cls.schedulable_resource,
            valid_from="2024-11-01",
            valid_to="2024-11-30",
        )

        # for monday to friday, availability for appointment 10-12 and open slots 14-16

        Availability.objects.create(
            schedule=cls.schedule,
            slot_type=SlotType.APPOINTMENT,
            slot_size_in_minutes=30,
            tokens_per_slot=10,
            days_of_week=[0, 1, 2, 3, 4],
            start_time=time(hour=10),
            end_time=time(hour=12),
        )
        Availability.objects.create(
            schedule=cls.schedule,
            slot_type=SlotType.OPEN,
            slot_size_in_minutes=0,
            tokens_per_slot=0,
            days_of_week=[0, 1, 2, 3, 4],
            start_time=time(hour=14),
            end_time=time(hour=16),
        )

        # he is on leave from 2024-11-05 to 2024-11-07
        ScheduleException.objects.create(
            resource=cls.schedulable_resource,
            is_available=False,
            slot_size_in_minutes=0,
            tokens_per_slot=0,
            valid_from="2024-11-05",
            valid_to="2024-11-07",
            start_time=time(hour=0, minute=0),
            end_time=time(hour=23, minute=59),
        )

        # he compensates for appointment on 2024-11-09 Saturday from 10-12
        ScheduleException.objects.create(
            resource=cls.schedulable_resource,
            is_available=True,
            slot_type=SlotType.APPOINTMENT,
            slot_size_in_minutes=30,
            tokens_per_slot=10,
            valid_from="2024-11-09",
            valid_to="2024-11-09",
            start_time=time(hour=10),
            end_time=time(hour=12),
        )
        ScheduleException.objects.create(
            resource=cls.schedulable_resource,
            is_available=True,
            slot_type=SlotType.OPEN,
            slot_size_in_minutes=0,
            tokens_per_slot=0,
            valid_from="2024-11-09",
            valid_to="2024-11-09",
            start_time=time(hour=14),
            end_time=time(hour=16),
        )
