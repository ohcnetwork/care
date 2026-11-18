from django.test import SimpleTestCase
from prometheus_client import CollectorRegistry, Gauge

from care.emr.metrics import EncounterCollector, PatientCollector
from care.facility.metrics import FacilityCollector
from care.users.metrics import UserCollector
from care.utils.metrics import metrics_registry

COLLECTOR_METRICS = (
    (FacilityCollector, {"care_facilities": {"category": "Private Hospital"}}),
    (PatientCollector, {"care_patients_registered": {}}),
    (
        EncounterCollector,
        {"care_encounters": {}, "care_encounters_by_type": {"type": "imp"}},
    ),
    (UserCollector, {"care_users": {}}),
)


class MetricRegistrationTests(SimpleTestCase):
    def assert_name_reserved(self, registry, name):
        with self.assertRaisesRegex(ValueError, "Duplicated timeseries"):
            metric = Gauge(name, "A conflicting plugin metric.", registry=registry)
            self.addCleanup(registry.unregister, metric)

    def test_shared_registry_reserves_every_builtin_metric_name(self):
        for _, metrics in COLLECTOR_METRICS:
            for name in metrics:
                with self.subTest(metric=name):
                    self.assert_name_reserved(metrics_registry, name)

    def test_collectors_reserve_names_without_database_access(self):
        for collector_type, metrics in COLLECTOR_METRICS:
            registry = CollectorRegistry(auto_describe=False)
            registry.register(collector_type())
            for name in metrics:
                with self.subTest(metric=name):
                    self.assert_name_reserved(registry, name)

    def test_collectors_reject_names_already_registered_by_plugins(self):
        for collector_type, metrics in COLLECTOR_METRICS:
            for name in metrics:
                with self.subTest(metric=name):
                    registry = CollectorRegistry(auto_describe=False)
                    Gauge(name, "An existing plugin metric.", registry=registry)

                    with self.assertRaisesRegex(ValueError, "Duplicated timeseries"):
                        registry.register(collector_type())

    def test_descriptions_provide_fresh_metadata_without_samples(self):
        for collector_type, metrics in COLLECTOR_METRICS:
            with self.subTest(collector=collector_type.__name__):
                collector = collector_type()
                descriptions = list(collector.describe())
                self.assertEqual(len(descriptions), len(metrics))
                self.assertEqual(
                    {description.name for description in descriptions}, set(metrics)
                )
                for description in descriptions:
                    self.assertEqual(description.type, "gauge")
                    self.assertTrue(description.documentation)
                    self.assertEqual(description.samples, [])
                    labels = metrics[description.name]
                    description.add_metric(list(labels.values()), 1)
                    self.assertEqual(description.samples[0].labels, labels)

                for description in collector.describe():
                    self.assertEqual(description.samples, [])

    def test_distinct_plugin_metric_coexists_with_builtin_collectors(self):
        registry = CollectorRegistry(auto_describe=False)
        for collector_type, _ in COLLECTOR_METRICS:
            registry.register(collector_type())
        metric = Gauge(
            "care_plugin_example", "A distinct plugin metric.", registry=registry
        )
        metric.set(7)

        metrics = list(registry.restricted_registry(["care_plugin_example"]).collect())

        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].name, "care_plugin_example")
        self.assertEqual(metrics[0].samples[0].value, 7)
