from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client.parser import text_string_to_metric_families

from care.emr.models.encounter import Encounter
from care.emr.models.patient import Patient
from care.emr.resources.encounter.constants import ClassChoices


@override_settings(
    MAINTAIN_FACILITY_PATIENT_NAME_IDENTIFIER=False,
    PROMETHEUS_METRICS_CACHE_TTL=0,
)
class MetricsTest(TestCase):
    def assert_metrics(self, **expected):
        response = self.client.get(reverse("metrics"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], CONTENT_TYPE_LATEST)
        self.assertIn("no-store", response["Cache-Control"])
        metrics = {
            metric.name: metric
            for metric in text_string_to_metric_families(response.content.decode())
        }
        for name, value in expected.items():
            with self.subTest(metric=name):
                self.assertIn(name, metrics)
                metric = metrics[name]
                self.assertEqual(metric.type, "gauge")
                self.assertEqual(len(metric.samples), 1)
                self.assertEqual(metric.samples[0].labels, {})
                self.assertEqual(metric.samples[0].value, value)
        return metrics

    def assert_encounter_types(self, metrics, **expected):
        metric = metrics["care_encounters_by_type"]
        self.assertEqual(metric.type, "gauge")
        counts = {encounter_type.value: 0 for encounter_type in ClassChoices}
        counts["unknown"] = 0
        counts.update(expected)
        self.assertEqual(len(metric.samples), len(counts))
        for sample in metric.samples:
            self.assertEqual(set(sample.labels), {"type"})
        self.assertEqual(
            {sample.labels["type"]: sample.value for sample in metric.samples}, counts
        )

    def test_empty_patient_count(self):
        self.assert_metrics(care_patients_registered=0)

    def test_counts_registered_patients_excluding_deleted_records(self):
        baker.make(Patient)
        baker.make(Patient, deceased_datetime=timezone.now())
        baker.make(Patient, deleted=True)

        self.assert_metrics(care_patients_registered=2)

    def test_each_scrape_reflects_current_patient_count(self):
        self.assert_metrics(care_patients_registered=0)

        patient = baker.make(Patient)
        self.assert_metrics(care_patients_registered=1)

        patient.delete()
        self.assert_metrics(care_patients_registered=0)

    def test_empty_encounter_count(self):
        metrics = self.assert_metrics(care_encounters=0)
        self.assert_encounter_types(metrics)

    def test_counts_encounters_across_statuses_excluding_deleted_records(self):
        user = baker.make("users.User")
        facility = baker.make("facility.Facility", created_by=user)
        patient = baker.make(Patient)
        for status, encounter_class in [
            ("in_progress", "imp"),
            ("completed", "imp"),
            ("cancelled", "amb"),
            ("entered_in_error", "emer"),
        ]:
            baker.make(
                Encounter,
                patient=patient,
                facility=facility,
                status=status,
                encounter_class=encounter_class,
            )
        baker.make(
            Encounter,
            patient=patient,
            facility=facility,
            encounter_class="obsenc",
            deleted=True,
        )

        metrics = self.assert_metrics(care_patients_registered=1, care_encounters=4)
        self.assert_encounter_types(metrics, imp=2, amb=1, emer=1)

    def test_unrecognized_encounter_types_share_unknown_bucket(self):
        user = baker.make("users.User")
        facility = baker.make("facility.Facility", created_by=user)
        patient = baker.make(Patient)
        for encounter_class in [None, "", "legacy-type"]:
            baker.make(
                Encounter,
                patient=patient,
                facility=facility,
                encounter_class=encounter_class,
            )
        baker.make(
            Encounter,
            patient=patient,
            facility=facility,
            encounter_class="another-legacy-type",
            deleted=True,
        )

        metrics = self.assert_metrics(care_encounters=3)
        self.assert_encounter_types(metrics, unknown=3)

    def test_each_scrape_reflects_current_encounter_count(self):
        self.assert_metrics(care_patients_registered=0, care_encounters=0)

        user = baker.make("users.User")
        facility = baker.make("facility.Facility", created_by=user)
        patient = baker.make(Patient)
        encounter = baker.make(
            Encounter, patient=patient, facility=facility, encounter_class="amb"
        )
        metrics = self.assert_metrics(care_patients_registered=1, care_encounters=1)
        self.assert_encounter_types(metrics, amb=1)

        encounter.encounter_class = "imp"
        encounter.save(update_fields=["encounter_class"])
        metrics = self.assert_metrics(care_encounters=1)
        self.assert_encounter_types(metrics, imp=1)

        encounter.delete()
        metrics = self.assert_metrics(care_patients_registered=1, care_encounters=0)
        self.assert_encounter_types(metrics)

    def test_post_is_not_allowed(self):
        response = self.client.post(reverse("metrics"))

        self.assertEqual(response.status_code, 405)
