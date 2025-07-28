from django.urls import reverse
from model_bakery import baker

from care.emr.resources.patient_identifier.spec import (
    PatientIdentifierStatus,
    PatientIdentifierUse,
)
from care.security.permissions.patient_identifier_config import (
    PatientIdentifierConfigPermissions,
)
from care.utils.tests.base import CareAPITestBase


class TestPatientIdentifierConfigAPI(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="testsuperuser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, name="Test Facility Org", org_type="root"
        )
        self.base_url = reverse("patient-identifier-config-list")
        self.role = self.create_role_with_permissions(
            permissions=[
                PatientIdentifierConfigPermissions.can_read_patient_identifier_config.name,
                PatientIdentifierConfigPermissions.can_write_patient_identifier_config.name,
            ]
        )

    def generate_config(self):
        return {
            "use": PatientIdentifierUse.usual,
            "description": "Test Identifier Config",
            "system": "http://example.com/identifier",
            "required": True,
            "unique": True,
            "regex": r"^\d{3}-\d{2}-\d{4}$",
            "display": "Test Identifier Display",
            "retrieve_config": {
                "retrieve_with_dob": False,
                "retrieve_with_year_of_birth": False,
                "retrieve_with_otp": False,
            },
            "default_value": None,
        }

    def generate_patient_identifier_config_data(self, status=None, facility=None):
        return {
            "status": status or PatientIdentifierStatus.active,
            "facility": facility or self.facility.external_id,
            "config": self.generate_config(),
        }

    def get_detail_url(self, external_id):
        return reverse(
            "patient_identifier_config-detail", kwargs={"external_id": external_id}
        )

    def create_patient_identifier_config(self, status=None, facility=None, config=None):
        patient_identifier_config_data = self.generate_patient_identifier_config_data(
            status=status, facility=facility, config=config
        )
        return baker.make(
            "emr.PatientIdentifierConfig", **patient_identifier_config_data
        )
