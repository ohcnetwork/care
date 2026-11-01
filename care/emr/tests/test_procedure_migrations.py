from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from model_bakery import baker


class ProcedureOutcomeMigrationTests(TransactionTestCase):
    migrate_from = [("emr", "0103_procedure")]
    migrate_to = [("emr", "0104_procedure_outcome")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.latest_migrations = executor.loader.graph.leaf_nodes()
        self.addCleanup(self.restore_schema)
        executor.migrate(self.migrate_from)
        self.old_procedure = executor.loader.project_state(
            self.migrate_from
        ).apps.get_model("emr", "Procedure")
        user = baker.make("users.User")
        facility = baker.make("facility.Facility", created_by=user)
        self.patient = baker.make("emr.Patient")
        self.encounter = baker.make(
            "emr.Encounter", patient=self.patient, facility=facility
        )

    def restore_schema(self):
        MigrationExecutor(connection).migrate(self.latest_migrations)

    def create_legacy_procedure(self, outcome, **kwargs):
        return self.old_procedure.objects.create(
            patient_id=self.patient.pk,
            encounter_id=self.encounter.pk,
            status="completed",
            code={},
            outcome=outcome,
            **kwargs,
        )

    def migrated_procedure_model(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate(target)
        return executor.loader.project_state(target).apps.get_model("emr", "Procedure")

    def test_coded_outcomes_convert_to_enums_and_reverse_to_snomed(self):
        cases = [
            ("385669000", "successful"),
            ("385671000", "unsuccessful"),
            ("385670004", "partially_successful"),
        ]
        expected = {}
        for code, outcome in cases:
            procedure = self.create_legacy_procedure(
                {"system": "http://snomed.info/sct", "code": code}
            )
            expected[procedure.pk] = outcome
        without_system = self.create_legacy_procedure({"code": "385669000"})
        expected[without_system.pk] = "successful"
        enum_string = self.create_legacy_procedure("partially_successful")
        expected[enum_string.pk] = "partially_successful"
        unknown = self.create_legacy_procedure(None)
        expected[unknown.pk] = None
        deleted = self.create_legacy_procedure({"code": "385671000"}, deleted=True)
        expected[deleted.pk] = "unsuccessful"

        procedure_model = self.migrated_procedure_model(self.migrate_to)
        self.assertEqual(
            dict(procedure_model.objects.values_list("pk", "outcome")), expected
        )

        procedure_model = self.migrated_procedure_model(self.migrate_from)
        outcome_codes = {outcome: code for code, outcome in cases}
        for procedure in procedure_model.objects.all():
            outcome = expected[procedure.pk]
            if outcome is None:
                self.assertIsNone(procedure.outcome)
            else:
                self.assertEqual(procedure.outcome["system"], "http://snomed.info/sct")
                self.assertEqual(procedure.outcome["code"], outcome_codes[outcome])

    def test_unrecognized_outcome_aborts_without_losing_existing_data(self):
        valid = self.create_legacy_procedure({"code": "385669000"})
        original = {"system": "http://snomed.info/sct", "code": "unknown-outcome"}
        invalid = self.create_legacy_procedure(original)
        try:
            with self.assertRaises(ValueError):
                self.migrated_procedure_model(self.migrate_to)
            self.assertEqual(
                self.old_procedure.objects.get(pk=valid.pk).outcome,
                {"code": "385669000"},
            )
            self.assertEqual(
                self.old_procedure.objects.get(pk=invalid.pk).outcome, original
            )
        finally:
            self.old_procedure.objects.filter(pk=invalid.pk).delete()
