from django.test import TransactionTestCase
from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from care.facility.models.patient_base import DiseaseStatusEnum
from care.utils.tests.test_base import TestBase
from care.users.models import District, State


class BasePatientRegistrationMigrationTest(TransactionTestCase):
    """
    Test specific migrations
        Make sure that `self.migrate_from` and `self.migrate_to` are defined.
    """
    migrate_from = None
    migrate_to = None

    @property
    def app(self):
        return apps.get_containing_app_config(type(self).__module__).label

    def setUp(self):
        super().setUp()
        assert self.migrate_to and self.migrate_from, \
            f'TestCase {type(self).__name__} must define migrate_to and migrate_from properties'

        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        self.executor = MigrationExecutor(connection)
        self.old_apps = self.executor.loader.project_state(self.migrate_from).apps

        # revert to the original migration
        self.executor.migrate(self.migrate_from)
        # ensure return to the latest migration, even if the test fails
        self.addCleanup(self.force_migrate)

        self.setUpBeforeMigration(self.old_apps)
        self.executor.loader.build_graph()
        self.executor.migrate(self.migrate_to)
        self.new_apps = self.executor.loader.project_state(self.migrate_to).apps

    def setUpBeforeMigration(self, apps):
        """
        This method may be used to create stuff before the migrations.
        Something like creating an instance of an old model.
        """
        pass

    @property
    def new_model(self):
        return self.new_apps.get_model(self.app, 'PatientRegistration')

    @property
    def old_model(self):
        return self.old_apps.get_model(self.app, 'PatientRegistration')

    def force_migrate(self, migrate_to=None):
        self.executor.loader.build_graph()  # reload.
        if migrate_to is None:
            # get latest migration of current app
            migrate_to = [key for key in self.executor.loader.graph.leaf_nodes() if key[0] == self.app]
        self.executor.migrate(migrate_to)


class DiseaseStatusMigrationTest(BasePatientRegistrationMigrationTest):
    migrate_from = '0223_merge_20210427_1419'
    migrate_to = '0224_change_disease_status_from_recover_to_recovered'

    def create_patient(self):
        data = self.data.copy()
        data.pop('medical_history', [])
        data.pop('state', '')
        data.pop('district', '')
        return self.old_model.objects.create(**data)


    def setUpBeforeMigration(self, apps):
        _state = State.objects.create(name='bihar')
        _district = District.objects.create(state=_state, name='dharbhanga')
        self.data = TestBase.get_patient_data(state=_state, district=_district)
        self.data.update({
            'disease_status': DiseaseStatusEnum.RECOVERY.value,
            'state_id': _state.id,
            'district_id': _district.id,
        })
        self.patient = self.create_patient()

    def test_recover_changed_to_recovered(self):
        patient = self.new_model.objects.get(id=self.patient.id)

        self.assertEqual(patient.disease_status, DiseaseStatusEnum.RECOVERED.value)
