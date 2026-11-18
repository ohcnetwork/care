from django.test import TestCase, override_settings
from django.urls import reverse
from model_bakery import baker
from prometheus_client import Gauge
from prometheus_client.parser import text_string_to_metric_families

from care.facility.models.facility import FACILITY_TYPES, Facility
from care.users.models import User
from care.utils.metrics import metrics_registry


@override_settings(PROMETHEUS_METRICS_CACHE_TTL=0)
class SharedMetricsTest(TestCase):
    def get_metrics(self):
        response = self.client.get(reverse("metrics"))

        self.assertEqual(response.status_code, 200)
        return {
            family.name: family
            for family in text_string_to_metric_families(response.content.decode())
        }

    def assert_facility_counts(self, metrics, expected):
        metric = metrics["care_facilities"]
        self.assertEqual(metric.type, "gauge")
        counts = dict.fromkeys([name for _, name in FACILITY_TYPES], 0)
        counts["unknown"] = 0
        counts.update(expected)
        self.assertEqual(len(metric.samples), len(counts))
        for sample in metric.samples:
            self.assertEqual(set(sample.labels), {"category"})
        self.assertEqual(
            {sample.labels["category"]: sample.value for sample in metric.samples},
            counts,
        )

    def assert_user_count(self, expected):
        metric = self.get_metrics()["care_users"]
        self.assertEqual(metric.type, "gauge")
        self.assertEqual(len(metric.samples), 1)
        self.assertEqual(metric.samples[0].labels, {})
        self.assertEqual(metric.samples[0].value, expected)

    def test_endpoint_exposes_metrics_from_shared_registry(self):
        metric = Gauge(
            "care_test_shared_metric",
            "A metric registered outside EMR.",
            registry=metrics_registry,
        )
        self.addCleanup(metrics_registry.unregister, metric)
        metric.set(7)

        metrics = self.get_metrics()
        for name in [
            "care_patients_registered",
            "care_encounters",
            "care_encounters_by_type",
            "care_facilities",
            "care_users",
        ]:
            with self.subTest(metric=name):
                self.assertIn(name, metrics)
        self.assertEqual(metrics["care_test_shared_metric"].samples[0].value, 7)

    def test_empty_facility_categories_are_zero(self):
        self.assert_facility_counts(self.get_metrics(), {})

    def test_facility_categories_include_inactive_and_exclude_deleted(self):
        user = baker.make(User)
        baker.make(Facility, created_by=user, facility_type=2)
        baker.make(Facility, created_by=user, facility_type=2, is_active=False)
        baker.make(Facility, created_by=user, facility_type=800)
        baker.make(Facility, created_by=user, facility_type=800, deleted=True)
        baker.make(Facility, created_by=user, facility_type=999999)

        self.assert_facility_counts(
            self.get_metrics(),
            {"Private Hospital": 2, "Primary Health Centres": 1, "unknown": 1},
        )

    def test_each_scrape_reflects_facility_category_changes_and_deletion(self):
        user = baker.make(User)
        facility = baker.make(Facility, created_by=user, facility_type=2)
        self.assert_facility_counts(self.get_metrics(), {"Private Hospital": 1})

        facility.facility_type = 800
        facility.save(update_fields=["facility_type"])
        self.assert_facility_counts(self.get_metrics(), {"Primary Health Centres": 1})

        facility.delete()
        self.assert_facility_counts(self.get_metrics(), {})

    def test_empty_user_count(self):
        self.assert_user_count(0)

    def test_user_count_includes_inactive_and_service_users_excluding_deleted(self):
        baker.make(User)
        baker.make(User, is_active=False)
        baker.make(User, is_service_account=True)
        baker.make(User, deleted=True)

        self.assert_user_count(3)

    def test_each_scrape_reflects_current_user_count(self):
        self.assert_user_count(0)

        user = baker.make(User)
        self.assert_user_count(1)

        user.deleted = True
        user.save(update_fields=["deleted"])
        self.assert_user_count(0)
