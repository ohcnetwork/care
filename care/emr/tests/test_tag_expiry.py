from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase
from model_bakery import baker
from pydantic import ValidationError as PydanticValidationError
from rest_framework.exceptions import ValidationError

from care.emr.models.tag_config import TagConfig, TagDeleteRequest
from care.emr.resources.tag.config_spec import (
    ExpiryOffset,
    TagConfigExpiryMetadata,
    TagResource,
    TagSetRequest,
)
from care.emr.tagging.base import (
    PatientFacilityTagManager,
    PatientInstanceTagManager,
    SingleFacilityTagManager,
    autohandle_expired_tasks,
    handle_expired_tag,
)
from care.utils.evaluators.evaluation_metric.encounter_tag import (
    EncounterTagsMetric,
    active_tags,
)
from care.utils.evaluators.evaluation_metric.patient_tag import PatientTagsMetric
from care.utils.tests.base import CareAPITestBase

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


class TestTagExpirySpecAndEvaluation(SimpleTestCase):
    def test_automatic_expiry_requires_an_offset(self):
        with self.assertRaisesRegex(
            PydanticValidationError, "Expiry offset is required"
        ):
            TagConfigExpiryMetadata(autoset_expiry=True)

    def test_optional_expiry_fields_are_omitted_from_serialized_request(self):
        metadata = TagConfigExpiryMetadata()
        self.assertEqual(metadata.model_dump(mode="json"), {})
        self.assertEqual(ExpiryOffset(hours=2).model_dump(mode="json"), {"hours": 2})

    @patch(
        "care.utils.evaluators.evaluation_metric.encounter_tag.care_now",
        return_value=NOW,
    )
    def test_active_tags_excludes_expired_tags_and_keeps_boundary(self, _now):
        tags_data = {
            "1": {"expiry": str(NOW - timedelta(seconds=1))},
            "2": {"expiry": str(NOW)},
            "3": {"expiry": str(NOW + timedelta(seconds=1))},
        }
        self.assertEqual(active_tags([1, 2, 3, 4], tags_data), [2, 3, 4])
        self.assertEqual(active_tags(None, None), [])
        self.assertEqual(active_tags([1], None), [1])

    @patch(
        "care.utils.evaluators.evaluation_metric.encounter_tag.care_now",
        return_value=NOW,
    )
    def test_patient_metric_filters_expiry_in_instance_and_current_facility(self, _now):
        patient = SimpleNamespace(
            instance_tags=[1, 2],
            facility_tags={"10": [3, 4], "11": [5]},
            tags_data={
                "1": {"expiry": str(NOW - timedelta(seconds=1))},
                "3": {"expiry": str(NOW - timedelta(seconds=1))},
            },
        )
        metric = PatientTagsMetric(patient, {"facility": SimpleNamespace(id=10)})
        self.assertEqual(metric.get_value(), [4, 2])
        self.assertEqual(PatientTagsMetric(patient).get_value(), [])

    @patch(
        "care.utils.evaluators.evaluation_metric.encounter_tag.care_now",
        return_value=NOW,
    )
    def test_encounter_metric_filters_expiry_in_encounter_and_patient(self, _now):
        encounter = SimpleNamespace(
            tags=[1, 2],
            tags_data={"1": {"expiry": str(NOW - timedelta(seconds=1))}},
            facility=SimpleNamespace(id=10),
            patient=SimpleNamespace(
                instance_tags=[3],
                facility_tags={"10": [4], "11": [5]},
                tags_data={"4": {"expiry": str(NOW - timedelta(seconds=1))}},
            ),
        )
        metric = EncounterTagsMetric(encounter)
        metric._value_type = "encounter"  # noqa: SLF001
        self.assertEqual(metric.get_value(), [2])
        metric._value_type = "patient"  # noqa: SLF001
        self.assertEqual(metric.get_value(), [3])


class TestTagExpiry(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.manager = SingleFacilityTagManager()
        self.clock = patch("care.emr.tagging.base.care_now", return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def make_tag(self, **kwargs):
        return baker.make(
            TagConfig,
            **{
                "display": "Temporary tag",
                "status": "active",
                "category": "clinical",
                "resource": TagResource.encounter.value,
                "facility": self.facility,
                "expiry_metadata": {
                    "autoset_expiry": True,
                    "expiry_offset": {"hours": 2},
                },
                **kwargs,
            },
        )

    def set_tag(self, tag, **kwargs):
        request = TagSetRequest(tag=tag.external_id, **kwargs)
        self.manager.lock_set_tag(
            TagResource.encounter,
            self.encounter,
            request,
            self.user,
            self.facility,
        )
        self.encounter.refresh_from_db()

    def test_automatic_expiry_persists_metadata_and_scheduled_deletion(self):
        tag = self.make_tag()
        self.set_tag(tag)
        expiry = NOW + timedelta(hours=2)
        self.assertEqual(self.encounter.tags, [tag.id])
        self.assertEqual(
            self.encounter.tags_data, {str(tag.id): {"expiry": str(expiry)}}
        )
        request = TagDeleteRequest.objects.get()
        self.assertEqual(request.resource_type, TagResource.encounter.value)
        self.assertEqual(request.resource_id, self.encounter.id)
        self.assertEqual(request.tag_config, tag)
        self.assertEqual(request.trigger_at, expiry)

    def test_requested_expiry_overrides_default_when_modification_is_allowed(self):
        tag = self.make_tag(
            expiry_metadata={
                "autoset_expiry": True,
                "modification_allowed": True,
                "expiry_offset": {"hours": 2},
            }
        )
        self.set_tag(tag, expiry_offset=ExpiryOffset(days=1, minutes=30))
        self.assertEqual(
            TagDeleteRequest.objects.get().trigger_at,
            NOW + timedelta(days=1, minutes=30),
        )

    def test_requested_expiry_is_ignored_when_modification_is_disabled(self):
        tag = self.make_tag()
        self.set_tag(tag, expiry_offset=ExpiryOffset(days=1))
        self.assertEqual(
            TagDeleteRequest.objects.get().trigger_at, NOW + timedelta(hours=2)
        )

    def test_optional_manual_expiry_without_automatic_default(self):
        tag = self.make_tag(expiry_metadata={"modification_allowed": True})
        self.set_tag(tag, expiry_offset=ExpiryOffset(minutes=30))
        self.assertEqual(
            TagDeleteRequest.objects.get().trigger_at, NOW + timedelta(minutes=30)
        )

    def test_nonexpiring_tag_does_not_schedule_deletion(self):
        tag = self.make_tag(expiry_metadata={})
        self.set_tag(tag)
        self.assertEqual(self.encounter.tags, [tag.id])
        self.assertEqual(self.encounter.tags_data, {})
        self.assertFalse(TagDeleteRequest.objects.exists())

    def test_unsetting_expiring_tag_removes_expiry_metadata(self):
        tag = self.make_tag()
        self.set_tag(tag)
        self.manager.unset_tags(
            TagResource.encounter,
            self.encounter,
            [TagSetRequest(tag=tag.external_id)],
            self.user,
        )
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.tags, [])
        self.assertEqual(self.encounter.tags_data, {})

    def test_reapplying_tag_reschedules_existing_deletion_request(self):
        tag = self.make_tag()
        self.set_tag(tag)
        original = TagDeleteRequest.objects.get()
        self.manager.unset_tags(
            TagResource.encounter,
            self.encounter,
            [TagSetRequest(tag=tag.external_id)],
            self.user,
        )
        later = NOW + timedelta(hours=1)
        with patch("care.emr.tagging.base.care_now", return_value=later):
            self.set_tag(tag)
        request = TagDeleteRequest.objects.get()
        self.assertEqual(request.pk, original.pk)
        self.assertEqual(request.trigger_at, later + timedelta(hours=2))

    def test_failed_batch_rolls_back_tags_and_expiry_requests(self):
        first = self.make_tag()
        wrong_resource = self.make_tag(resource=TagResource.patient.value)
        with self.assertRaisesRegex(ValidationError, "Tag resource does not match"):
            self.manager.set_tags(
                TagResource.encounter,
                self.encounter,
                [
                    TagSetRequest(tag=first.external_id),
                    TagSetRequest(tag=wrong_resource.external_id),
                ],
                self.user,
                self.facility,
            )
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.tags, [])
        self.assertEqual(self.encounter.tags_data, {})
        self.assertFalse(TagDeleteRequest.objects.exists())

    def test_cleanup_task_removes_only_expired_encounter_tags(self):
        expired = self.make_tag()
        active = self.make_tag()
        permanent = self.make_tag(expiry_metadata={})
        self.encounter.tags = [expired.id, active.id, permanent.id]
        self.encounter.tags_data = {
            str(expired.id): {"expiry": str(NOW - timedelta(seconds=1))},
            str(active.id): {"expiry": str(NOW + timedelta(seconds=1))},
        }
        self.encounter.save(update_fields=["tags", "tags_data"])
        handle_expired_tag.run(TagResource.encounter.value, self.encounter.id)
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.tags, [active.id, permanent.id])
        self.assertEqual(
            self.encounter.tags_data,
            {str(active.id): {"expiry": str(NOW + timedelta(seconds=1))}},
        )

    def test_patient_cleanup_handles_instance_and_multiple_facility_tags(self):
        other_facility = self.create_facility(user=self.user)
        expired_instance = self.make_tag(
            resource=TagResource.patient.value, facility=None
        )
        active_instance = self.make_tag(
            resource=TagResource.patient.value, facility=None
        )
        expired_facility = self.make_tag(resource=TagResource.patient.value)
        active_facility = self.make_tag(
            resource=TagResource.patient.value, facility=other_facility
        )
        self.patient.instance_tags = [expired_instance.id, active_instance.id]
        self.patient.facility_tags = {
            str(self.facility.id): [expired_facility.id],
            str(other_facility.id): [active_facility.id],
        }
        self.patient.tags_data = {
            str(tag.id): {"expiry": str(NOW - timedelta(seconds=1))}
            for tag in [expired_instance, expired_facility]
        }
        self.patient.save(update_fields=["instance_tags", "facility_tags", "tags_data"])
        handle_expired_tag.run(TagResource.patient.value, self.patient.id)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.instance_tags, [active_instance.id])
        self.assertEqual(
            self.patient.facility_tags,
            {str(self.facility.id): [], str(other_facility.id): [active_facility.id]},
        )
        self.assertEqual(self.patient.tags_data, {})

    def test_patient_managers_persist_expiry_in_both_tag_scopes(self):
        for manager, facility in (
            (PatientInstanceTagManager(), None),
            (PatientFacilityTagManager(self.facility), self.facility),
        ):
            with self.subTest(facility=facility):
                tag = self.make_tag(
                    resource=TagResource.patient.value, facility=facility
                )
                manager.lock_set_tag(
                    TagResource.patient,
                    self.patient,
                    TagSetRequest(tag=tag.external_id),
                    self.user,
                )
                self.patient.refresh_from_db()
                self.assertIn(tag.id, manager.get_resource_tag(self.patient))
                self.assertEqual(
                    self.patient.tags_data[str(tag.id)]["expiry"],
                    str(NOW + timedelta(hours=2)),
                )
                self.assertTrue(
                    TagDeleteRequest.objects.filter(
                        resource_type=TagResource.patient.value,
                        resource_id=self.patient.id,
                        tag_config=tag,
                    ).exists()
                )

    def test_patient_tag_rules_match_active_tags_in_current_facility(self):
        instance_tag = self.make_tag(resource=TagResource.patient.value, facility=None)
        active_tag = self.make_tag(resource=TagResource.patient.value)
        expired_tag = self.make_tag(resource=TagResource.patient.value)
        other_facility = self.create_facility(user=self.user)
        other_tag = self.make_tag(
            resource=TagResource.patient.value, facility=other_facility
        )
        self.patient.instance_tags = [instance_tag.id]
        self.patient.facility_tags = {
            str(self.facility.id): [active_tag.id, expired_tag.id],
            str(other_facility.id): [other_tag.id],
        }
        self.patient.tags_data = {
            str(expired_tag.id): {"expiry": str(NOW - timedelta(seconds=1))}
        }
        metric = PatientTagsMetric(self.patient, {"facility": self.facility})
        with patch(
            "care.utils.evaluators.evaluation_metric.encounter_tag.care_now",
            return_value=NOW,
        ):
            for value, expected in (
                (str(instance_tag.external_id), True),
                (str(active_tag.external_id), True),
                (str(expired_tag.external_id), False),
                (str(other_tag.external_id), False),
                (str(uuid4()), False),
                (f"{expired_tag.external_id},{active_tag.external_id}", True),
            ):
                with self.subTest(value=value):
                    self.assertEqual(
                        metric.apply_rule("has_tag", {"value": value}), expected
                    )

    def test_patient_tag_rules_require_facility_context(self):
        tag = self.make_tag(resource=TagResource.patient.value, facility=None)
        self.patient.instance_tags = [tag.id]
        metric = PatientTagsMetric(self.patient)
        self.assertFalse(metric.apply_rule("has_tag", {"value": str(tag.external_id)}))

    @patch("care.emr.tagging.base.handle_expired_tag.delay")
    def test_scheduler_dispatches_only_due_requests_and_removes_them(self, dispatch):
        due = self.make_tag()
        future = self.make_tag()
        TagDeleteRequest.create_delete_request(
            TagResource.encounter, self.encounter.id, due, NOW
        )
        future_request, _ = TagDeleteRequest.create_delete_request(
            TagResource.encounter,
            self.encounter.id,
            future,
            NOW + timedelta(seconds=1),
        )
        autohandle_expired_tasks.run()
        dispatch.assert_called_once_with(TagResource.encounter.value, self.encounter.id)
        self.assertEqual(list(TagDeleteRequest.objects.all()), [future_request])

    @patch("care.emr.tagging.base.handle_expired_tag.delay")
    def test_rendering_expired_tag_marks_it_and_requests_cleanup(self, dispatch):
        expired = self.make_tag()
        active = self.make_tag()
        self.encounter.tags = [expired.id, active.id]
        self.encounter.tags_data = {
            str(expired.id): {"expiry": str(NOW - timedelta(seconds=1))},
            str(active.id): {"expiry": str(NOW + timedelta(seconds=1))},
        }
        rendered = self.manager.render_tags(self.encounter)
        self.assertEqual(rendered[0]["expiry"], str(NOW - timedelta(seconds=1)))
        self.assertTrue(rendered[0]["expired"])
        self.assertNotIn("expired", rendered[1])
        dispatch.assert_called_once_with(TagResource.encounter.value, self.encounter.id)
