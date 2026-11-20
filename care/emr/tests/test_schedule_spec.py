from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
from pydantic import ValidationError

from care.emr.resources.scheduling.schedule.spec import ScheduleCreateSpec


@override_settings(TIME_ZONE="Asia/Kolkata", USE_TZ=True)
class ScheduleCreateSpecDateTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        now_patch = patch(
            "care.emr.resources.scheduling.schedule.spec.care_now",
            return_value=datetime(2026, 10, 25, 10, tzinfo=UTC),
        )
        self.mock_now = now_patch.start()
        self.addCleanup(now_patch.stop)
        self.data = {
            "facility": str(uuid4()),
            "name": "Test Schedule",
            "valid_from": "2026-10-25",
            "valid_to": "2026-10-26",
            "availabilities": [],
            "resource_type": "practitioner",
            "resource_id": str(uuid4()),
            "is_public": False,
        }

    def test_accepts_today_at_midnight_and_earlier_today(self):
        for valid_from in [
            "2026-10-25",
            "2026-10-25T00:00:00",
            "2026-10-25T09:00:00",
        ]:
            with self.subTest(valid_from=valid_from):
                spec = ScheduleCreateSpec.model_validate(
                    {**self.data, "valid_from": valid_from}
                )
                self.assertEqual(spec.valid_from.date().isoformat(), "2026-10-25")

    def test_accepts_validity_ending_today(self):
        for valid_to in ["2026-10-25", "2026-10-25T01:00:00"]:
            with self.subTest(valid_to=valid_to):
                spec = ScheduleCreateSpec.model_validate(
                    {**self.data, "valid_to": valid_to}
                )
                self.assertEqual(spec.valid_to.date(), spec.valid_from.date())

    def test_rejects_yesterday_for_either_validity_date(self):
        for field in ["valid_from", "valid_to"]:
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(
                    ValidationError, "Date cannot be before the current date"
                ),
            ):
                ScheduleCreateSpec.model_validate({**self.data, field: "2026-10-24"})

    def test_accepts_future_validity(self):
        spec = ScheduleCreateSpec.model_validate(
            {
                **self.data,
                "valid_from": "2026-10-26",
                "valid_to": "2026-10-27",
            }
        )
        self.assertEqual(spec.valid_from.date().isoformat(), "2026-10-26")

    def test_uses_local_date_when_utc_is_still_yesterday(self):
        self.mock_now.return_value = datetime(2026, 10, 24, 19, tzinfo=UTC)
        spec = ScheduleCreateSpec.model_validate(self.data)
        self.assertEqual(spec.valid_from.date().isoformat(), "2026-10-25")

        for field in ["valid_from", "valid_to"]:
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(
                    ValidationError, "Date cannot be before the current date"
                ),
            ):
                ScheduleCreateSpec.model_validate({**self.data, field: "2026-10-24"})

    def test_accepts_aware_timestamps_on_current_local_date(self):
        for valid_from in [
            "2026-10-24T18:30:00Z",
            "2026-10-25T00:00:00+05:30",
        ]:
            with self.subTest(valid_from=valid_from):
                spec = ScheduleCreateSpec.model_validate(
                    {
                        **self.data,
                        "valid_from": valid_from,
                        "valid_to": "2026-10-26T00:00:00+05:30",
                    }
                )
                self.assertIsNotNone(spec.valid_from.tzinfo)

    def test_rejects_aware_timestamps_on_previous_local_date(self):
        for field in ["valid_from", "valid_to"]:
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(
                    ValidationError, "Date cannot be before the current date"
                ),
            ):
                ScheduleCreateSpec.model_validate(
                    {**self.data, field: "2026-10-25T00:00:00+14:00"}
                )

    def test_rejects_valid_to_before_valid_from(self):
        with self.assertRaisesRegex(
            ValidationError, "Valid from cannot be greater than valid to"
        ):
            ScheduleCreateSpec.model_validate(
                {
                    **self.data,
                    "valid_from": "2026-10-26",
                    "valid_to": "2026-10-25",
                }
            )
