from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from model_bakery import baker
from prometheus_client.parser import text_string_to_metric_families

from care.emr.models.patient import Patient


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"metrics-cache-tests-{uuid4()}",
        }
    },
    PROMETHEUS_METRICS_CACHE_TTL=600,
)
class MetricsCacheTest(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def assert_patient_count(self, response, expected):
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        metrics = {
            metric.name: metric
            for metric in text_string_to_metric_families(response.content.decode())
        }
        self.assertEqual(metrics["care_patients_registered"].samples[0].value, expected)

    def test_cached_snapshot_is_shared_without_database_queries(self):
        baker.make(Patient)

        with patch.dict(connection.settings_dict, {"ATOMIC_REQUESTS": True}):
            with CaptureQueriesContext(connection) as queries:
                first = self.client.get(reverse("metrics"))
            self.assertGreater(len(queries), 0)
            self.assert_patient_count(first, 1)

            baker.make(Patient)
            with self.assertNumQueries(0):
                second = Client().get(reverse("metrics"))

        self.assert_patient_count(second, 1)
        self.assertEqual(first.content, second.content)

    def assert_snapshot_expires_after(self, seconds):
        with patch(
            "django.core.cache.backends.locmem.time.time", return_value=1000
        ) as clock:
            first = self.client.get(reverse("metrics"))
            self.assert_patient_count(first, 0)
            baker.make(Patient)

            clock.return_value = 1000 + seconds - 1
            with self.assertNumQueries(0):
                cached = self.client.get(reverse("metrics"))
            self.assert_patient_count(cached, 0)

            clock.return_value = 1000 + seconds
            with CaptureQueriesContext(connection) as queries:
                refreshed = self.client.get(reverse("metrics"))
            self.assertGreater(len(queries), 0)
            self.assert_patient_count(refreshed, 1)

    def test_snapshot_refreshes_after_ten_minutes(self):
        self.assert_snapshot_expires_after(600)

    @override_settings(PROMETHEUS_METRICS_CACHE_TTL=30)
    def test_cache_lifetime_is_configurable(self):
        self.assert_snapshot_expires_after(30)

    def test_zero_lifetime_bypasses_existing_snapshot(self):
        first = self.client.get(reverse("metrics"))
        self.assert_patient_count(first, 0)

        with override_settings(PROMETHEUS_METRICS_CACHE_TTL=0):
            for expected in (1, 2):
                baker.make(Patient)
                with CaptureQueriesContext(connection) as queries:
                    response = self.client.get(reverse("metrics"))
                self.assertGreater(len(queries), 0)
                self.assert_patient_count(response, expected)
