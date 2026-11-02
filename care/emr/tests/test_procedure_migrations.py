from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from model_bakery import baker


class ProcedureSchemaMigrationTests(TransactionTestCase):
    migrate_from = [("emr", "0102_schedule_participants")]
    migrate_to = [("emr", "0103_procedure")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.latest_migrations = executor.loader.graph.leaf_nodes()
        self.addCleanup(self.restore_schema)
        executor.migrate(self.migrate_from)
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state(
            [
                node
                for node in executor.loader.applied_migrations
                if node in executor.loader.graph.nodes
            ]
        ).apps
        user = baker.make(apps.get_model("users", "User"))
        facility = baker.make(apps.get_model("facility", "Facility"), created_by=user)
        self.patient = baker.make(apps.get_model("emr", "Patient"))
        self.encounter = baker.make(
            apps.get_model("emr", "Encounter"),
            patient=self.patient,
            facility=facility,
        )

    def restore_schema(self):
        MigrationExecutor(connection).migrate(self.latest_migrations)

    def migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate(target)
        return executor.loader.project_state(target).apps

    def test_creates_procedure_with_nullable_enum_outcome(self):
        self.assertNotIn("emr_procedure", connection.introspection.table_names())
        apps = self.migrate(self.migrate_to)
        procedure_model = apps.get_model("emr", "Procedure")
        outcome_field = procedure_model._meta.get_field("outcome")  # noqa: SLF001
        self.assertIsInstance(outcome_field, models.CharField)
        self.assertEqual(outcome_field.max_length, 32)
        self.assertTrue(outcome_field.null)
        for outcome in ("successful", "unsuccessful", "partially_successful", None):
            with self.subTest(outcome=outcome):
                procedure = procedure_model.objects.create(
                    patient_id=self.patient.pk,
                    encounter_id=self.encounter.pk,
                    status="completed",
                    outcome=outcome,
                )
                procedure.refresh_from_db()
                self.assertEqual(procedure.outcome, outcome)
                self.assertEqual(procedure.patient_id, self.patient.pk)
                self.assertEqual(procedure.encounter_id, self.encounter.pk)
                self.assertEqual(procedure.code, {})
                self.assertEqual(procedure.body_site, [])

    def test_reversing_procedure_creation_preserves_existing_patient_data(self):
        self.migrate(self.migrate_to)
        apps = self.migrate(self.migrate_from)
        self.assertNotIn("emr_procedure", connection.introspection.table_names())
        self.assertTrue(
            apps.get_model("emr", "Patient").objects.filter(pk=self.patient.pk).exists()
        )
        self.assertTrue(
            apps.get_model("emr", "Encounter")
            .objects.filter(pk=self.encounter.pk)
            .exists()
        )
        apps = self.migrate(self.migrate_to)
        self.assertEqual(apps.get_model("emr", "Procedure").objects.count(), 0)
